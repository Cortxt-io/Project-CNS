"""Cortxt MCP Server – exposes Cortxt data as tools over Streamable HTTP.

Remote MCP server built on FastMCP 2.x. Mounted into the Flask app via the
ASGI entrypoint (``app/asgi.py``) and served at ``/mcp`` so it can be added as
a remote Custom Connector in claude.ai (telefon/web/desktop).

Auth: OAuth 2.1. claude.ai's connector UI only supports OAuth — it has no
field for a static Bearer token or custom headers — so ``/mcp`` is gated by an
OAuth flow (GitHub by default), NOT the ``CNS_API_TOKEN`` used by the REST API.
When the OAuth env vars are unset the server starts unauthenticated, which is
intended only for local development / Claude Desktop.

Provides 12 tools:
  - cortxt_list_active_quests
  - cortxt_get_quest
  - cortxt_complete_quest
  - cortxt_capture_idea
  - cortxt_list_ideas
  - cortxt_promote_idea_to_quest
  - cortxt_list_projects
  - cortxt_get_project
  - cortxt_start_session
  - cortxt_mark_session_done
  - cortxt_save_session
  - cortxt_list_sessions
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
    from scripts.md_parser import read_node
    quest = get_quest(quest_id)
    if not quest:
        return {"error": f"Quest {quest_id} not found"}
    # Add project context
    try:
        meta, sections, _ = read_node(quest["slug"])
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
def cortxt_promote_idea_to_quest(
    idea_id: str,
    title: str,
    estimated_impact: str = "",
    slug: str | None = None,
    description: str | None = None,
) -> dict:
    """Promote an idea into a quest, reusing the quest-creation logic.

    The new quest's slug comes from the idea (or the `slug` argument if the idea
    has none); its description defaults to the idea's text. The idea is kept and
    marked 'promoted'. Returns {"idea": ..., "quest": ...}.
    """
    from scripts.idea_inbox import get_idea, mark_promoted, IDEAS_DIR
    from scripts.quest_manager import create_quest, QUESTS_DIR
    from app.git_ops import push_file_immediately

    idea = get_idea(idea_id)
    if idea is None:
        raise ToolError(f"Idea {idea_id} not found")
    if idea.get("status") == "promoted":
        raise ToolError(
            f"Idea {idea_id} was already promoted to {idea.get('promoted_to')}"
        )

    quest_slug = slug or idea.get("slug")
    if not quest_slug:
        raise ToolError(
            "Idea has no linked slug — pass `slug` to say which node the quest is for."
        )

    quest = create_quest(
        slug=quest_slug,
        title=title,
        description=description or idea["text"],
        estimated_impact=estimated_impact,
        source="idea",
    )
    quest_path = QUESTS_DIR / f"{quest['id']}.json"
    push_file_immediately(
        quest_path, f"cns-vault: create quest {quest['id']} from idea {idea_id}"
    )

    idea = mark_promoted(idea_id, quest["id"])
    idea_path = IDEAS_DIR / f"{idea_id}.json"
    push_file_immediately(
        idea_path, f"cns-vault: promote idea {idea_id} to {quest['id']}"
    )

    return {"idea": idea, "quest": quest}


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


# ---------------------------------------------------------------------------
# Sessions — an AI work-pass as a first-class object (scripts/session_store.py).
# Mirrors the idea/quest tools: session_store stays pure storage, the push lives
# here in the MCP wrapper (same split as cortxt_capture_idea / btw_capture).
# ---------------------------------------------------------------------------


def _push_session(session: dict, action: str) -> None:
    """Best-effort GitHub push of one session file. Never fails the tool."""
    from scripts.session_store import SESSIONS_DIR
    from app.git_ops import push_file_immediately

    path = SESSIONS_DIR / f"{session['id']}.json"
    push_file_immediately(path, f"cns-vault: {action} {session['id']}")


@mcp.tool()
def cortxt_start_session(
    link_kind: str | None = None,
    link_ref: str | None = None,
    summary: str = "",
    source: str = "chat",
    transcript_id: str | None = None,
) -> dict:
    """Register a running AI work-pass (status=running) and push it to GitHub.

    Link it to a track via (link_kind, link_ref), e.g. ("node", "cns-core") or
    ("quest", "quest-a1c37d56"). link_kind is one of quest|issue|idea|node.
    `transcript_id` can point at the Claude Code session's .jsonl for traceability.

    The running→done flip is a pollable signal: another parallel session can
    wait (e.g. via /loop) until this one flips to done before merging its work.
    """
    from scripts.session_store import start_session
    session = start_session(
        link_kind=link_kind,
        link_ref=link_ref,
        summary=summary,
        source=source,
        transcript_id=transcript_id,
    )
    _push_session(session, "start session")
    return session


@mcp.tool()
def cortxt_mark_session_done(session_id: str, summary: str | None = None) -> dict:
    """Flip a running session to done — the signal a polling sibling waits on.

    Optionally overwrite the summary with the pass's conclusion. Pushes to GitHub.
    """
    from scripts.session_store import mark_done
    try:
        session = mark_done(session_id, summary=summary)
    except FileNotFoundError:
        raise ToolError(f"Session {session_id} not found")
    _push_session(session, "mark session done")
    return session


@mcp.tool()
def cortxt_save_session(
    summary: str,
    link_kind: str | None = None,
    link_ref: str | None = None,
    status: str = "done",
    source: str = "chat",
    transcript_id: str | None = None,
) -> dict:
    """Save an AI work-pass in one shot (default status=done) and push to GitHub.

    This is "save session to CNS": a summary plus a link to the node/quest/idea
    it advanced. Use this to flush a session's conclusion when you didn't open
    it with cortxt_start_session. link_kind is one of quest|issue|idea|node.
    """
    from scripts.session_store import save_session
    session = save_session(
        summary=summary,
        link_kind=link_kind,
        link_ref=link_ref,
        status=status,
        source=source,
        transcript_id=transcript_id,
    )
    _push_session(session, "save session")
    return session


@mcp.tool()
def cortxt_list_sessions(
    status: str | None = None, link_ref: str | None = None
) -> list[dict]:
    """List sessions, newest first; optionally filter by status and/or link_ref.

    Pass link_ref=<node slug or quest id> to see every session that touched the
    same track — this is the overlap query: if several sessions link to one node,
    their work may need reconciling. Pass status='running' to find passes still
    in flight.
    """
    from scripts.session_store import list_sessions
    return list_sessions(status=status, link_ref=link_ref)


if __name__ == "__main__":
    # Local development fallback: stdio transport for Claude Desktop.
    # The production deployment serves Streamable HTTP via app/asgi.py instead.
    mcp.run()
