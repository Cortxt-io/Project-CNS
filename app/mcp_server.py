"""Cortxt MCP Server – exposes Cortxt data as tools over Streamable HTTP.

Remote MCP server built on FastMCP 2.x. Mounted into the Flask app via the
ASGI entrypoint (``app/asgi.py``) and served at ``/mcp`` so it can be added as
a remote Custom Connector in claude.ai (telefon/web/desktop).

Auth: OAuth 2.1. claude.ai's connector UI only supports OAuth — it has no
field for a static Bearer token or custom headers — so ``/mcp`` is gated by an
OAuth flow (GitHub by default), NOT the ``CNS_API_TOKEN`` used by the REST API.
When the OAuth env vars are unset the server starts unauthenticated, which is
intended only for local development / Claude Desktop.

Provides 13 tools:
  - cortxt_list_open_issues
  - cortxt_get_issue
  - cortxt_create_issue
  - cortxt_close_issue
  - cortxt_list_quests        (milestones)
  - cortxt_get_quest          (milestone + its issues)
  - cortxt_create_quest       (milestone)
  - cortxt_close_quest        (milestone)
  - cortxt_capture_idea
  - cortxt_list_ideas
  - cortxt_promote_idea_to_issue
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

    Production requires (in addition to the GitHub OAuth app):
      - MCP_BASE_URL              public origin
      - JWT_SIGNING_KEY           stable signing key (else tokens die on restart)
      - STORAGE_ENCRYPTION_KEY    Fernet key for encrypting stored tokens
      - REDIS_URL                 Redis connection (Railway Redis plugin)

    Without REDIS_URL we fall back to in-memory storage (dev/Claude Desktop),
    which does NOT survive worker restarts — that's the bug this fixes for prod.
    """
    client_id = os.getenv("MCP_GITHUB_CLIENT_ID")
    client_secret = os.getenv("MCP_GITHUB_CLIENT_SECRET")
    base_url = os.getenv("MCP_BASE_URL")
    if not (client_id and client_secret and base_url):
        return None

    from fastmcp.server.auth.providers.github import GitHubProvider

    jwt_signing_key = os.getenv("JWT_SIGNING_KEY")
    redis_url = os.getenv("REDIS_URL")
    storage_key = os.getenv("STORAGE_ENCRYPTION_KEY")

    client_storage = None
    if redis_url and storage_key:
        from key_value.aio.stores.redis import RedisStore
        from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
        from cryptography.fernet import Fernet

        client_storage = FernetEncryptionWrapper(
            key_value=RedisStore(url=redis_url),
            fernet=Fernet(storage_key.encode()),
        )
    elif redis_url or storage_key:
        logger.warning(
            "Partial storage config: REDIS_URL and STORAGE_ENCRYPTION_KEY must "
            "BOTH be set for persistent OAuth storage. Falling back to memory."
        )

    kwargs = dict(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        required_scopes=["read:user"],
    )
    if jwt_signing_key:
        kwargs["jwt_signing_key"] = jwt_signing_key
    else:
        logger.warning(
            "JWT_SIGNING_KEY not set — tokens will be invalidated on every "
            "worker restart. Set it for stable auth."
        )
    if client_storage is not None:
        kwargs["client_storage"] = client_storage

    return GitHubProvider(**kwargs)


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


# --- Work items: GitHub Issues (replaces the quest lifecycle) ---------------
# A node's work items are GitHub Issues tagged with the `node:<slug>` label.
# These call scripts.issues_client with token=None, which uses CNS_GITHUB_TOKEN
# (the server token git_ops already relies on). Decision E (act as the calling
# user via the per-user OAuth token from get_access_token()) is pending
# confirmation that the GitHub access token is retrievable here; until then the
# server token is used. NOTE: these are breaking renames of the old
# cortxt_*_quest tools — the claude.ai connector must be re-authed/refreshed.


@mcp.tool()
def cortxt_list_open_issues(node_slug: str | None = None) -> list[dict]:
    """List open work-item issues, optionally filtered to one node via its node:<slug> label."""
    from scripts.issues_client import list_issues
    return list_issues(node_slug=node_slug, state="open")


@mcp.tool()
def cortxt_get_issue(number: int) -> dict:
    """Get a work-item issue enriched with its node context (kind/stage/summary)."""
    from scripts.issues_client import get_issue
    from scripts.md_parser import read_node
    issue = get_issue(number)
    if not issue:
        return {"error": f"Issue #{number} not found"}
    slug = issue.get("node_slug")
    if slug:
        try:
            meta, _sections, _ = read_node(slug)
            issue["node_context"] = {
                "meta": meta,
                "summary": meta.get("summary", ""),
                "kind": meta.get("kind", ""),
                "stage": meta.get("stage", ""),
            }
        except Exception:
            pass
    return issue


@mcp.tool()
def cortxt_create_issue(
    node_slug: str, title: str, body: str = "", quest_number: int | None = None
) -> dict:
    """Create a work-item issue tied to a node, optionally inside a quest (milestone).

    `quest_number` is a GitHub milestone number (see cortxt_list_quests).
    """
    from scripts.issues_client import create_issue
    return create_issue(node_slug=node_slug, title=title, body=body, milestone=quest_number)


@mcp.tool()
def cortxt_close_issue(number: int, result_summary: str) -> dict:
    """Close a work-item issue, leaving the result summary as a closing comment."""
    from scripts.issues_client import close_issue
    return close_issue(number, comment=result_summary)


# --- Quests: GitHub Milestones grouping N issues (progress computed by GitHub) ---


@mcp.tool()
def cortxt_list_quests() -> list[dict]:
    """List open quests (GitHub milestones) with progress (closed/total issues)."""
    from scripts.issues_client import list_milestones
    return list_milestones(state="open")


@mcp.tool()
def cortxt_get_quest(number: int) -> dict:
    """Get a quest (milestone) with its issues. `number` is the milestone number."""
    from scripts.issues_client import get_milestone, list_issues
    quest = get_milestone(number)
    if not quest:
        return {"error": f"Quest (milestone) #{number} not found"}
    quest["issues"] = list_issues(milestone=number, state="all")
    return quest


@mcp.tool()
def cortxt_create_quest(title: str, description: str = "") -> dict:
    """Create a quest (GitHub milestone) to group several issues under one work package."""
    from scripts.issues_client import create_milestone
    return create_milestone(title=title, description=description)


@mcp.tool()
def cortxt_close_quest(number: int) -> dict:
    """Close a quest (milestone). Its issues keep their own open/closed state."""
    from scripts.issues_client import close_milestone
    return close_milestone(number)


@mcp.tool()
def cortxt_capture_idea(text: str, source: str = "chat", slug: str | None = None) -> dict:
    """Capture a raw idea into the inbox — lighter than a quest.

    Use this for any thought worth keeping that isn't yet an actionable task.
    `source` is "chat" or "code"; `slug` optionally links the idea to a node.
    """
    from scripts.idea_inbox import capture_idea, IDEAS_DIR
    from app.git_ops import push_file_immediately
    idea = capture_idea(text=text, source=source, slug=slug)
    idea_path = IDEAS_DIR / f"{idea['id']}.json"
    push_file_immediately(idea_path, f"cns-vault: capture idea {idea['id']}")
    return idea


@mcp.tool()
def cortxt_list_ideas(status: str = "open", slug: str | None = None) -> list[dict]:
    """List captured ideas, newest first. Pass status='' to include all."""
    from scripts.idea_inbox import list_ideas
    return list_ideas(status=status or None, slug=slug)


@mcp.tool()
def cortxt_promote_idea_to_issue(
    idea_id: str,
    title: str,
    slug: str | None = None,
    body: str | None = None,
) -> dict:
    """Promote an inbox idea into a GitHub Issue (a node work item).

    The issue's node comes from the idea (or the `slug` argument if the idea has
    none); its body defaults to the idea's text. The idea is kept and marked
    'promoted' to the new issue. Returns {"idea": ..., "issue": ...}.
    """
    from scripts.idea_inbox import get_idea, mark_promoted, IDEAS_DIR
    from scripts.issues_client import create_issue
    from app.git_ops import push_file_immediately

    idea = get_idea(idea_id)
    if idea is None:
        raise ToolError(f"Idea {idea_id} not found")
    if idea.get("status") == "promoted":
        raise ToolError(
            f"Idea {idea_id} was already promoted to {idea.get('promoted_to')}"
        )

    node_slug = slug or idea.get("slug")
    if not node_slug:
        raise ToolError(
            "Idea has no linked slug — pass `slug` to say which node the issue is for."
        )

    issue = create_issue(node_slug=node_slug, title=title, body=body or idea["text"])

    idea = mark_promoted(idea_id, f"#{issue['number']}")
    idea_path = IDEAS_DIR / f"{idea_id}.json"
    push_file_immediately(
        idea_path, f"cns-vault: promote idea {idea_id} to issue #{issue['number']}"
    )

    return {"idea": idea, "issue": issue}


@mcp.tool()
def cortxt_list_projects() -> list[dict]:
    """List all CNS projects with metadata."""
    from scripts.md_parser import read_all_nodes
    result = []
    for meta, _ in read_all_nodes():
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
    from scripts.md_parser import read_node, node_dir
    try:
        meta, sections, _ = read_node(slug)
        # Read planning files
        planning = {}
        pdir = node_dir(slug) / "planning"
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
