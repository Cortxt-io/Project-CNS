"""Domänkärna: sessioner (AI-arbetspass). Transport-fri — INGEN GitHub-push.

Push ligger i wrappern (samma split: session_store är rent datalager). Write-actions
returnerar sessionsobjektet så wrappern kan pusha rätt fil. FileNotFoundError → ValueError.
"""
from __future__ import annotations

from typing import Any


def session(action: str, **kw: Any) -> Any:
    if action == "start":
        from scripts.session_store import start_session

        return start_session(
            link_kind=kw.get("link_kind"),
            link_ref=kw.get("link_ref"),
            summary=kw.get("summary", ""),
            source=kw.get("source", "chat"),
            transcript_id=kw.get("transcript_id"),
        )

    if action == "done":
        from scripts.session_store import mark_done

        try:
            return mark_done(kw["session_id"], summary=kw.get("summary"))
        except FileNotFoundError:
            raise ValueError(f"Session {kw['session_id']} not found")

    if action == "save":
        from scripts.session_store import save_session

        return save_session(
            summary=kw["summary"],
            link_kind=kw.get("link_kind"),
            link_ref=kw.get("link_ref"),
            status=kw.get("status", "done"),
            source=kw.get("source", "chat"),
            transcript_id=kw.get("transcript_id"),
        )

    if action == "list":
        from scripts.session_store import list_sessions

        return list_sessions(status=kw.get("status"), link_ref=kw.get("link_ref"))

    if action == "fork":
        from scripts.session_store import fork_session

        try:
            return fork_session(
                parent_id=kw["parent_id"],
                summary=kw.get("summary", ""),
                fork_name=kw.get("fork_name"),
                link_kind=kw.get("link_kind"),
                link_ref=kw.get("link_ref"),
                source=kw.get("source", "chat"),
                transcript_id=kw.get("transcript_id"),
            )
        except FileNotFoundError:
            raise ValueError(f"Parent session {kw['parent_id']} not found")

    if action == "tree":
        from scripts.session_store import tree

        return tree(kw.get("root_id"))

    raise ValueError(f"okänd session-action: {action}")
