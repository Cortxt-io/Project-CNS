"""Delade hjälpare för de feta connector-wrappers (universum A).

Wrappers är tunna: typad signatur (FastMCP-schema) → ``call()`` → domänkärnan i
``scripts/tools``. Kärnan kastar ``ValueError``; här översätts det till ``ToolError`` så
claude.ai får ett rent fel i stället för ett maskerat internt. Push (idéer/sessioner)
och OAuth-owner (leases) hanteras i respektive wrapper, inte i kärnan.
"""
from __future__ import annotations

from typing import Any


def call(domain: str, action: str, **kwargs: Any) -> Any:
    """Kör en domän-action via registry.dispatch, översätt ValueError → ToolError."""
    from fastmcp.exceptions import ToolError

    from scripts.tools import registry

    try:
        return registry.dispatch(domain, action, **kwargs)
    except ValueError as e:
        raise ToolError(str(e)) from e


def push_idea(idea_id: str, msg: str) -> None:
    """Best-effort GitHub-push av en idéfil. Stjälper aldrig anroparen."""
    try:
        from scripts.idea_inbox import IDEAS_DIR
        from app.git_ops import push_file_immediately

        push_file_immediately(IDEAS_DIR / f"{idea_id}.json", msg)
    except Exception:
        pass


def push_session(session: dict, action: str) -> None:
    """Best-effort GitHub-push av en sessionsfil. Stjälper aldrig anroparen."""
    try:
        from scripts.session_store import SESSIONS_DIR
        from app.git_ops import push_file_immediately

        push_file_immediately(
            SESSIONS_DIR / f"{session['id']}.json", f"cns-vault: {action} {session['id']}"
        )
    except Exception:
        pass


def owner() -> str:
    """Anropande sessionens GitHub-login ur OAuth-token; 'local' i odefinierat dev-läge."""
    try:
        from fastmcp.server.dependencies import get_access_token

        token = get_access_token()
        login = token.claims.get("login") if token and token.claims else None
        return login or "local"
    except Exception:
        return "local"
