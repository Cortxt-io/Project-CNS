"""Session-poster för CNS — ett AI-arbetspass som förstklassigt objekt.

Speglar ``scripts.idea_inbox`` och ``scripts.quest_manager``: en post per fil
i ``exports/sessions/session-<id>.json``. En session är ett stycke AI-arbete
som kan knytas till ett quest/issue/idé (samma paraply-modell: quest = spåret,
issue = uppgift, session = arbetspass).

Status ``running`` → ``done`` gör posten till en pollbar signal: ett annat
spår kan vänta (``/loop``) tills sessionen flippar till ``done``. Att skriva
``running`` kräver att passet registrerar sig vid start; annars används bara
``save_session`` som en done-markör i efterhand.

Isolerat och read/write-mot-disk. GitHub-push (som idea_inbox/quests) sker i
MCP-/server-lagret — läggs additivt EFTER quest→issues-migreringen (het fil).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"
SESSIONS_DIR = EXPORTS_DIR / "sessions"

VALID_STATUSES = {"running", "done"}
VALID_LINK_KINDS = {"quest", "issue", "idea", "node"}
VALID_SOURCES = {"chat", "code"}


def _ensure_dir() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def _short_id() -> str:
    return f"session-{uuid4().hex[:8]}"


def _write(session: dict) -> None:
    _session_path(session["id"]).write_text(
        json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _link(link_kind: str | None, link_ref: str | None) -> dict | None:
    if not link_kind or not link_ref:
        return None
    if link_kind not in VALID_LINK_KINDS:
        raise ValueError(
            f"Invalid link_kind '{link_kind}'. Allowed: {', '.join(sorted(VALID_LINK_KINDS))}"
        )
    return {"kind": link_kind, "ref": str(link_ref)}


def start_session(
    link_kind: str | None = None,
    link_ref: str | None = None,
    summary: str = "",
    source: str = "chat",
    transcript_id: str | None = None,
) -> dict:
    """Registrera ett pågående arbetspass (status=running).

    Knyt det till ett spår via (link_kind, link_ref), t.ex. ("quest", quest_id).
    transcript_id kan peka på Claude Code-sessionens .jsonl för spårbarhet.
    """
    if source not in VALID_SOURCES:
        raise ValueError(
            f"Invalid source '{source}'. Allowed: {', '.join(sorted(VALID_SOURCES))}"
        )
    _ensure_dir()
    now = datetime.now().isoformat(timespec="seconds")
    session = {
        "id": _short_id(),
        "created_at": now,
        "updated_at": now,
        "status": "running",
        "summary": summary,
        "link": _link(link_kind, link_ref),
        "transcript_id": transcript_id,
        "source": source,
    }
    _write(session)
    return session


def save_session(
    summary: str,
    link_kind: str | None = None,
    link_ref: str | None = None,
    status: str = "done",
    source: str = "chat",
    transcript_id: str | None = None,
) -> dict:
    """Spara ett arbetspass direkt (default status=done — done-markör i efterhand).

    Detta är "Spara session till CNS": en sammanfattning + länk till quest/issue/idé.
    """
    if status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Allowed: {', '.join(sorted(VALID_STATUSES))}"
        )
    if source not in VALID_SOURCES:
        raise ValueError(
            f"Invalid source '{source}'. Allowed: {', '.join(sorted(VALID_SOURCES))}"
        )
    _ensure_dir()
    now = datetime.now().isoformat(timespec="seconds")
    session = {
        "id": _short_id(),
        "created_at": now,
        "updated_at": now,
        "status": status,
        "summary": summary,
        "link": _link(link_kind, link_ref),
        "transcript_id": transcript_id,
        "source": source,
    }
    _write(session)
    return session


def get_session(session_id: str) -> dict | None:
    path = _session_path(session_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def mark_done(session_id: str, summary: str | None = None) -> dict:
    """Flippa ett pågående pass till done (signalen en /loop väntar på)."""
    session = get_session(session_id)
    if session is None:
        raise FileNotFoundError(f"Session '{session_id}' not found")
    session["status"] = "done"
    session["updated_at"] = datetime.now().isoformat(timespec="seconds")
    if summary is not None:
        session["summary"] = summary
    _write(session)
    return session


def load_all_sessions() -> list[dict]:
    if not SESSIONS_DIR.exists():
        return []
    sessions: list[dict] = []
    for path in SESSIONS_DIR.glob("session-*.json"):
        try:
            sessions.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return sessions


def list_sessions(
    status: str | None = None, link_ref: str | None = None
) -> list[dict]:
    """Lista sessioner, valfritt filtrerade på status och/eller länkad ref, nyast först."""
    sessions = load_all_sessions()
    if status:
        sessions = [s for s in sessions if s.get("status") == status]
    if link_ref:
        sessions = [
            s for s in sessions if (s.get("link") or {}).get("ref") == link_ref
        ]
    sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return sessions
