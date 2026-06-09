"""Cortxt MCP Server – exposes Cortxt data as tools over Streamable HTTP.

Remote MCP server built on FastMCP 2.x. Mounted into the Flask app via the
ASGI entrypoint (``app/asgi.py``) and served at ``/mcp`` so it can be added as
a remote Custom Connector in claude.ai (telefon/web/desktop).

Auth: OAuth 2.1. claude.ai's connector UI only supports OAuth — it has no
field for a static Bearer token or custom headers — so ``/mcp`` is gated by an
OAuth flow (GitHub by default), NOT the ``CNS_API_TOKEN`` used by the REST API.
When the OAuth env vars are unset the server starts unauthenticated, which is
intended only for local development / Claude Desktop.

This module owns auth, the GitHub allowlist middleware and the ``mcp`` instance.
The 19 ``cortxt_*`` tools themselves live in ``app/tools/`` — one domain module
per area, each with a ``register(mcp)``. Add a new tool as an ``@mcp.tool`` in
the right module (or a new module + its register call below), against the
``scripts/`` data layer — NOT as another decorator here. Tool names are a public
connector contract (claude.ai) and must stay stable when moved between modules.

  - issues:      cortxt_list_open_issues / get_issue / create_issue / close_issue
                 / add_todo / check_todo
  - quests:      cortxt_list_quests / get_quest / create_quest / close_quest  (milestones)
  - ideas:       cortxt_capture_idea / list_ideas / promote_idea_to_issue
  - projects:    cortxt_list_projects / get_project  (CNS nodes)
  - sessions:    cortxt_start_session / mark_session_done / save_session / list_sessions
                 / fork_session / get_session_tree
  - prs:         cortxt_list_prs / get_pr / create_pr / set_pr_reviewers
  - gh_projects: cortxt_list_gh_projects / list_gh_project_items / move_gh_project_item
  - actions:     cortxt_list_workflow_runs / trigger_workflow / get_workflow_run
  - wiki:        cortxt_list_wiki_pages / read_wiki_page / write_wiki_page
  - linear:      cortxt_list_linear_issues / create_linear_issue / link_linear_to_cns
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


# Attach the cortxt_* tools. Each domain module owns its tools via register(mcp).
from app.tools import issues, quests, ideas, projects, sessions
from app.tools import prs, gh_projects, actions, wiki, linear

issues.register(mcp)
quests.register(mcp)
ideas.register(mcp)
projects.register(mcp)
sessions.register(mcp)
prs.register(mcp)
gh_projects.register(mcp)
actions.register(mcp)
wiki.register(mcp)
linear.register(mcp)


if __name__ == "__main__":
    # Local development fallback: stdio transport for Claude Desktop.
    # The production deployment serves Streamable HTTP via app/asgi.py instead.
    mcp.run()
