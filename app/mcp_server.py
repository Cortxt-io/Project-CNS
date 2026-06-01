"""Cortxt MCP Server – exposes Cortxt data as tools over Streamable HTTP.

Remote MCP server built on FastMCP 2.x. Mounted into the Flask app via the
ASGI entrypoint (``app/asgi.py``) and served at ``/mcp`` so it can be added as
a remote Custom Connector in claude.ai (telefon/web/desktop).

Auth: OAuth 2.1. claude.ai's connector UI only supports OAuth — it has no
field for a static Bearer token or custom headers — so ``/mcp`` is gated by an
OAuth flow (GitHub by default), NOT the ``CNS_API_TOKEN`` used by the REST API.
When the OAuth env vars are unset the server starts unauthenticated, which is
intended only for local development / Claude Desktop.

Provides 5 tools:
  - cortxt_list_active_quests
  - cortxt_get_quest
  - cortxt_complete_quest
  - cortxt_list_projects
  - cortxt_get_project
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repo root is on path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware


def _build_auth():
    """Build the OAuth provider for /mcp from environment, or None for dev.

    claude.ai requires OAuth (no static-Bearer option in its connector UI), so
    in production set:
      - MCP_GITHUB_CLIENT_ID / MCP_GITHUB_CLIENT_SECRET  (a GitHub OAuth app)
      - MCP_BASE_URL  (public origin, e.g. https://<app>.up.railway.app)

    FastMCP's GitHubProvider wraps an OAuth proxy that advertises the metadata
    and Dynamic Client Registration that claude.ai's connector relies on.

    Returns None when the vars are missing → unauthenticated server, intended
    only for local development / Claude Desktop over stdio.
    """
    client_id = os.getenv("MCP_GITHUB_CLIENT_ID")
    client_secret = os.getenv("MCP_GITHUB_CLIENT_SECRET")
    base_url = os.getenv("MCP_BASE_URL")
    if not (client_id and client_secret and base_url):
        return None

    from fastmcp.server.auth.providers.github import GitHubProvider

    return GitHubProvider(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        required_scopes=["read:user"],
    )


import logging

logger = logging.getLogger(__name__)


def _allowed_github_users() -> set[str]:
    """GitHub logins allowed to call tools, from MCP_ALLOWED_GITHUB_USERS
    (comma-separated, case-insensitive). Empty set = no restriction."""
    raw = os.getenv("MCP_ALLOWED_GITHUB_USERS", "")
    return {u.strip().lower() for u in raw.split(",") if u.strip()}


class GitHubAllowlistMiddleware(Middleware):
    """Reject tool calls from GitHub users not on the allowlist.

    The authenticated user's GitHub login comes from the OAuth access-token
    claims (GitHubProvider stores it under "login"). Applied to every tool
    call, so reading project data and mutating quests are both gated — without
    this, any GitHub account that completes the OAuth flow could run the tools.
    """

    def __init__(self, allowed_logins: set[str]) -> None:
        self._allowed = allowed_logins

    async def on_call_tool(self, context, call_next):
        token = get_access_token()
        login = token.claims.get("login") if token and token.claims else None
        if not login or login.lower() not in self._allowed:
            raise ToolError(
                "Access denied: your GitHub account is not authorized for this server."
            )
        return await call_next(context)


mcp = FastMCP("cortxt", auth=_build_auth())

# Lock tool access to specific GitHub users when an allowlist is configured.
_allowlist = _allowed_github_users()
if _allowlist:
    mcp.add_middleware(GitHubAllowlistMiddleware(_allowlist))
elif mcp.auth is not None:
    logger.warning(
        "MCP OAuth is configured but MCP_ALLOWED_GITHUB_USERS is empty — "
        "ANY GitHub user who logs in can call the tools. Set it to lock "
        "access to your own account."
    )


@mcp.tool()
def cortxt_list_active_quests() -> list[dict]:
    """List all quests with status 'active' or 'in_progress'."""
    from scripts.quest_manager import list_quests
    active = list_quests(status="active")
    in_progress = list_quests(status="in_progress")
    return active + in_progress


@mcp.tool()
def cortxt_get_quest(quest_id: str) -> dict:
    """Get full quest details including project context."""
    from scripts.quest_manager import get_quest
    from scripts.md_parser import read_project
    quest = get_quest(quest_id)
    if not quest:
        return {"error": f"Quest {quest_id} not found"}
    # Add project context
    try:
        meta, sections, _ = read_project(quest["slug"])
        quest["project_context"] = {
            "meta": meta,
            "summary": meta.get("summary", ""),
            "layer": meta.get("layer", ""),
            "pipeline": meta.get("pipeline", ""),
        }
    except Exception:
        pass
    return quest


@mcp.tool()
def cortxt_complete_quest(quest_id: str, result_summary: str) -> dict:
    """Mark a quest as completed with a result summary."""
    from scripts.quest_manager import transition_quest, update_quest
    from app.git_ops import push_file_immediately
    from scripts.quest_manager import QUESTS_DIR
    quest = transition_quest(quest_id, "completed")
    quest = update_quest(quest_id, result_summary=result_summary)
    # Push to GitHub
    quest_path = QUESTS_DIR / f"{quest_id}.json"
    push_file_immediately(quest_path, f"cns-vault: complete quest {quest_id}")
    return quest


@mcp.tool()
def cortxt_list_projects() -> list[dict]:
    """List all CNS projects with metadata."""
    from scripts.md_parser import read_all_projects
    result = []
    for meta, _ in read_all_projects():
        result.append({
            "slug": meta.get("slug"),
            "title": meta.get("title"),
            "status": meta.get("status"),
            "layer": meta.get("layer"),
            "pipeline": meta.get("pipeline"),
            "summary": meta.get("summary"),
        })
    return result


@mcp.tool()
def cortxt_get_project(slug: str) -> dict:
    """Get full project context including sections and planning files."""
    from scripts.md_parser import read_project, project_dir
    try:
        meta, sections, _ = read_project(slug)
        # Read planning files
        planning = {}
        pdir = project_dir(slug) / "planning"
        if pdir.exists():
            for f in sorted(pdir.glob("*.md")):
                if f.name.lower() != "readme.md":
                    planning[f.name] = f.read_text(encoding="utf-8")
        return {"meta": meta, "sections": sections, "planning": planning}
    except FileNotFoundError:
        return {"error": f"Project {slug} not found"}


if __name__ == "__main__":
    # Local development fallback: stdio transport for Claude Desktop.
    # The production deployment serves Streamable HTTP via app/asgi.py instead.
    mcp.run()
