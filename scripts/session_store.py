"""Session-poster för CNS — ett AI-arbetspass som förstklassigt objekt.

Speglar ``scripts.idea_inbox`` och ``scripts.quest_manager``: en post per fil
i ``exports/sessions/session-<id>.json``. En session är ett stycke AI-arbete
som kan knytas till ett quest/issue/idé (samma paraply-modell: quest = spåret,
issue = uppgift, session = arbetspass).

Status ``running`` → ``done`` gör posten till en pollbar signal: ett annat
spår kan vänta (``/loop``) tills sessionen flippar till ``done``. Att skriva
``running`` kräver att passet registrerar sig vid start; annars används bara
``save_session`` som en done-markör i efterhand.

Sessioner bildar ett **träd**: valfritt ``parent_id`` pekar på den session forken
sprang ur (``None`` = rot/"main"-pass). ``parent_id`` är ortogonalt mot ``link``
— en session kan samtidigt arbeta på ett issue (``link``) och vara ett barn till
en annan session (``parent_id``). ``children``/``ancestry``/``tree`` traverserar
trädet; ``fork_session`` skapar ett barn med ``parent_id`` satt explicit (till
skillnad från ``/btw``, vars hook-payload saknar förälder-id).

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
    parent_id: str | None = None,
    fork_name: str | None = None,
) -> dict:
    """Registrera ett pågående arbetspass (status=running).

    Knyt det till ett spår via (link_kind, link_ref), t.ex. ("quest", quest_id).
    transcript_id kan peka på Claude Code-sessionens .jsonl för spårbarhet.
    parent_id pekar (om satt) på den session detta pass forkades ur — None = rot.
    fork_name är en valfri mänsklig etikett på forken.
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
        "parent_id": parent_id,
        "fork_name": fork_name,
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
    parent_id: str | None = None,
    fork_name: str | None = None,
) -> dict:
    """Spara ett arbetspass direkt (default status=done — done-markör i efterhand).

    Detta är "Spara session till CNS": en sammanfattning + länk till quest/issue/idé.
    parent_id/fork_name knyter passet in i sessionsträdet (None = rot).
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
        "parent_id": parent_id,
        "fork_name": fork_name,
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


def fork_session(
    parent_id: str,
    summary: str = "",
    fork_name: str | None = None,
    link_kind: str | None = None,
    link_ref: str | None = None,
    source: str = "chat",
    transcript_id: str | None = None,
) -> dict:
    """Skapa en barn-session (status=running) under parent_id — en explicit fork.

    Till skillnad från ``/btw`` (vars hook-payload saknar förälder-id) skrivs
    parent_id här ut explicit i posten, vilket är vad ett session-träd kräver.
    Höjer FileNotFoundError om föräldern inte finns.
    """
    if get_session(parent_id) is None:
        raise FileNotFoundError(f"Parent session '{parent_id}' not found")
    return start_session(
        link_kind=link_kind,
        link_ref=link_ref,
        summary=summary,
        source=source,
        transcript_id=transcript_id,
        parent_id=parent_id,
        fork_name=fork_name,
    )


def children(session_id: str) -> list[dict]:
    """Direkta barn till en session, äldst först (forkningsordning)."""
    kids = [s for s in load_all_sessions() if s.get("parent_id") == session_id]
    kids.sort(key=lambda s: s.get("created_at", ""))
    return kids


def ancestry(session_id: str) -> list[dict]:
    """Kedjan av förfäder, närmast förälder först, upp till roten (exkl. self).

    Bryter vid saknad förälder eller cykel (besökta id:n spåras)."""
    by_id = {s["id"]: s for s in load_all_sessions()}
    chain: list[dict] = []
    seen: set[str] = {session_id}
    cur = by_id.get(session_id)
    while cur and cur.get("parent_id"):
        pid = cur["parent_id"]
        if pid in seen:
            break  # cykelskydd
        parent = by_id.get(pid)
        if parent is None:
            break
        chain.append(parent)
        seen.add(pid)
        cur = parent
    return chain


def tree(root_id: str | None = None) -> list[dict] | dict | None:
    """Bygg sessionsträdet som nästlade noder ({**session, "children": [...]}).

    root_id=None → lista av alla rötter (parent_id saknas) nästlade. Annars
    delträdet för den givna sessionen (None om den inte finns). Barn äldst först."""
    all_sessions = load_all_sessions()
    by_parent: dict[str | None, list[dict]] = {}
    for s in all_sessions:
        by_parent.setdefault(s.get("parent_id"), []).append(s)
    for kids in by_parent.values():
        kids.sort(key=lambda s: s.get("created_at", ""))

    seen: set[str] = set()

    def build(node: dict) -> dict:
        seen.add(node["id"])
        kids = [k for k in by_parent.get(node["id"], []) if k["id"] not in seen]
        return {**node, "children": [build(k) for k in kids]}

    if root_id is not None:
        node = next((s for s in all_sessions if s["id"] == root_id), None)
        return build(node) if node else None
    roots = by_parent.get(None, [])
    return [build(r) for r in roots]
