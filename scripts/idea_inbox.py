"""Idea inbox for Cortxt — a lightweight capture layer below quests.

An idea is a raw, unstructured thought worth keeping: it has none of a quest's
ceremony (no title, no impact estimate, no state machine). Once an idea proves
worth acting on, ``promote`` turns it into a real quest via the existing
``scripts.quest_manager`` logic.

Storage: exports/ideas/<id>.json (one file per idea), mirroring quest storage.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"
IDEAS_DIR = EXPORTS_DIR / "ideas"

VALID_SOURCES = {"chat", "code"}
VALID_STATUSES = {"open", "promoted"}


def _ensure_dir() -> None:
    """Create the ideas directory if it doesn't exist."""
    IDEAS_DIR.mkdir(parents=True, exist_ok=True)


def _idea_path(idea_id: str) -> Path:
    """Return the file path for an idea."""
    return IDEAS_DIR / f"{idea_id}.json"


def _short_id() -> str:
    """Generate a short idea ID like idea-a1b2c3d4."""
    return f"idea-{uuid4().hex[:8]}"


def _write(idea: dict) -> None:
    """Persist an idea to disk (UTF-8, matching quest serialization)."""
    _idea_path(idea["id"]).write_text(
        json.dumps(idea, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def capture_idea(
    text: str,
    source: str = "chat",
    slug: str | None = None,
    session_id: str | None = None,
) -> dict:
    """Create a new idea and persist it to disk.

    Args:
        text: The idea itself (free text).
        source: Where it came from — "chat" or "code".
        slug: Optional node slug this idea relates to (soft link, not validated,
            matching how quests reference a slug).
        session_id: Optional session this idea was born in (soft link, not
            validated). Lets a session's ideas be enumerated later — the
            prerequisite for routing a session's parts (idea-337b37ff).

    Returns the created idea dict.
    """
    if source not in VALID_SOURCES:
        raise ValueError(
            f"Invalid source '{source}'. Allowed: {', '.join(sorted(VALID_SOURCES))}"
        )
    _ensure_dir()
    idea = {
        "id": _short_id(),
        "text": text,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "slug": slug,
        "session_id": session_id,
        "status": "open",
    }
    _write(idea)
    return idea


def get_idea(idea_id: str) -> dict | None:
    """Load an idea by ID. Returns None if not found."""
    path = _idea_path(idea_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_ideas(
    status: str | None = "open",
    slug: str | None = None,
    session_id: str | None = None,
) -> list[dict]:
    """List ideas, optionally filtered by status, slug and/or session, newest first.

    Pass status=None to include every status. ``session_id`` enables the
    "wake this session's open ideas" flow (idea-337b37ff).
    """
    _ensure_dir()
    ideas = load_all_ideas()
    if status:
        ideas = [i for i in ideas if i.get("status") == status]
    if slug:
        ideas = [i for i in ideas if i.get("slug") == slug]
    if session_id:
        ideas = [i for i in ideas if i.get("session_id") == session_id]
    ideas.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    return ideas


def mark_promoted(idea_id: str, quest_id: str) -> dict:
    """Mark an idea as promoted and record the quest it became.

    Keeps the idea file (status flips to 'promoted') so the trail survives.
    Raises FileNotFoundError if the idea doesn't exist.
    """
    idea = get_idea(idea_id)
    if idea is None:
        raise FileNotFoundError(f"Idea not found: {idea_id}")
    idea["status"] = "promoted"
    idea["promoted_to"] = quest_id
    _write(idea)
    return idea


def load_all_ideas() -> list[dict]:
    """Load all ideas from the ideas directory."""
    _ensure_dir()
    ideas = []
    for path in IDEAS_DIR.glob("idea-*.json"):
        try:
            ideas.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return ideas
