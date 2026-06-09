"""Session tools — an AI work-pass as a first-class object (scripts/session_store.py).

Mirrors the idea/quest tools: session_store stays pure storage, the push lives
here in the MCP wrapper (same split as cortxt_capture_idea / btw_capture).
"""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError


def _push_session(session: dict, action: str) -> None:
    """Best-effort GitHub push of one session file. Never fails the tool."""
    from scripts.session_store import SESSIONS_DIR
    from app.git_ops import push_file_immediately

    path = SESSIONS_DIR / f"{session['id']}.json"
    push_file_immediately(path, f"cns-vault: {action} {session['id']}")


def register(mcp: FastMCP) -> None:
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
