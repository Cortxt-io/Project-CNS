"""Connector-wrapper: ``cortxt_session`` (fett verktyg) över session-domänkärnan.

Ersätter de 6 gamla ``cortxt_*_session*``-verktygen (kvar som alias). Kärnan
(``scripts/tools/session_core.py``) är rent datalager; **pushen ligger här** (samma
split som idéer/btw).
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.tools._fat import call, push_session as _push_session


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_session(
        action: str,
        session_id: str | None = None,
        parent_id: str | None = None,
        summary: str = "",
        fork_name: str | None = None,
        link_kind: str | None = None,
        link_ref: str | None = None,
        status: str | None = None,
        source: str = "chat",
        transcript_id: str | None = None,
        root_id: str | None = None,
    ) -> dict | list | None:
        """AI-arbetspass. Välj `action`:

        - `start` (link_kind?, link_ref?, summary?, source?, transcript_id?) — registrera ett pågående pass.
        - `done` (session_id; summary?) — flippa ett pass till done (pollbar signal).
        - `save` (summary; link_kind?, link_ref?, status?, …) — spara ett pass i ett svep.
        - `list` (status?, link_ref?) — lista pass (overlap-query via link_ref).
        - `fork` (parent_id; summary?, fork_name?, link_kind?, link_ref?, …) — forka ett barnpass.
        - `tree` (root_id?) — sessionsträdet nästlat.
        """
        result = call(
            "session", action,
            session_id=session_id, parent_id=parent_id, summary=summary,
            fork_name=fork_name, link_kind=link_kind, link_ref=link_ref,
            status=status,  # None = osatt; kärnan defaultar 'save' till 'done', 'list' filtrerar ej
            source=source, transcript_id=transcript_id, root_id=root_id,
        )
        if action in ("start", "done", "save", "fork") and isinstance(result, dict):
            _push_session(result, f"{action} session")
        return result
