"""BTW session log for Cortxt — captures the `/btw` asides raised in a session.

`/btw <text>` is a Claude Code command that forks a side-branch seeded with a
passing thought. The thought itself — the *aside* — is the artifact worth
keeping. This module stores those asides, grouped by the session they came from
and softly linkable to a quest or idea, so the context survives ("these asides
came up while working on quest X").

This is not product data (nodes/ideas/quests); it's a personal log. It lives
under exports/ alongside ideas so it rides the same GitHub-sync path, but it has
its own store and never touches the node model.

Storage: exports/btw/<session-id>.json (one file per session), mirroring
``scripts.idea_inbox``. This module is pure storage — it never pushes to GitHub;
the caller (``scripts.btw_capture``) owns the push, matching how ``mcp_server``
pushes after ``idea_inbox.capture_idea``.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"
BTW_DIR = EXPORTS_DIR / "btw"


def _ensure_dir() -> None:
    """Create the btw directory if it doesn't exist."""
    BTW_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
    """Return the file path for a session log."""
    return BTW_DIR / f"{session_id}.json"


def _now() -> str:
    """Local timestamp, matching idea/quest serialization."""
    return datetime.now().isoformat(timespec="seconds")


def _write(session: dict) -> None:
    """Persist a session log to disk (UTF-8, matching idea serialization)."""
    _session_path(session["session_id"]).write_text(
        json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _new_session(session_id: str) -> dict:
    now = _now()
    return {
        "session_id": session_id,
        "created_at": now,
        "updated_at": now,
        "linked_quest": None,
        "linked_idea": None,
        "asides": [],
    }


def get_session(session_id: str) -> dict | None:
    """Load a session log by id. Returns None if not found."""
    path = _session_path(session_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def add_aside(
    session_id: str,
    text: str,
    src_uuid: str,
    fork: str | None = None,
    ts: str | None = None,
) -> tuple[dict, bool]:
    """Append one `/btw` aside to a session log, creating it if needed.

    Idempotent: if an aside with the same ``src_uuid`` is already logged, the
    file is left untouched. This lets the capture hook re-scan the whole
    transcript on every stop and only ever add what's new.

    Args:
        session_id: The Claude Code session the aside belongs to.
        text: The aside itself — the `<command-args>` of the `/btw` call.
        src_uuid: The transcript uuid of the `/btw` command (dedup key).
        fork: Optional fork name parsed from the command's stdout.
        ts: When the aside was raised (transcript timestamp); defaults to now.

    Returns ``(session, added)`` where ``added`` is False on a duplicate.
    """
    _ensure_dir()
    session = get_session(session_id) or _new_session(session_id)
    if any(a.get("src_uuid") == src_uuid for a in session["asides"]):
        return session, False
    session["asides"].append(
        {
            "ts": ts or _now(),
            "text": text,
            "fork": fork,
            "src_uuid": src_uuid,
        }
    )
    session["updated_at"] = _now()
    _write(session)
    return session, True


def link_session(
    session_id: str,
    quest_id: str | None = None,
    idea_id: str | None = None,
) -> dict:
    """Soft-link a session to a quest and/or idea (unvalidated, like idea.slug).

    Creates the session file if it doesn't exist yet. Only the arguments you
    pass are applied; omit one to leave it unchanged. Raises ValueError if
    neither is given.
    """
    if quest_id is None and idea_id is None:
        raise ValueError("Pass quest_id and/or idea_id to link.")
    _ensure_dir()
    session = get_session(session_id) or _new_session(session_id)
    if quest_id is not None:
        session["linked_quest"] = quest_id
    if idea_id is not None:
        session["linked_idea"] = idea_id
    session["updated_at"] = _now()
    _write(session)
    return session


def list_sessions() -> list[dict]:
    """Load all session logs, most-recently-updated first."""
    _ensure_dir()
    sessions = []
    for path in BTW_DIR.glob("*.json"):
        try:
            sessions.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return sessions
