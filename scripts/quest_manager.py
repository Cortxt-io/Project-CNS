"""Quest lifecycle management for Cortxt.

Quests track actionable tasks across the portfolio with a defined state machine:
    suggested -> active -> in_progress -> completed -> archived

Storage: exports/quests/<id>.json (one file per quest)
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"
QUESTS_DIR = EXPORTS_DIR / "quests"

VALID_STATUSES = {"suggested", "active", "in_progress", "completed", "archived"}

TRANSITIONS = {
    "suggested": {"active", "archived"},
    "active": {"in_progress", "completed", "archived"},
    "in_progress": {"completed", "archived"},
    "completed": {"archived"},
    "archived": set(),
}


def _ensure_dir() -> None:
    """Create the quests directory if it doesn't exist."""
    QUESTS_DIR.mkdir(parents=True, exist_ok=True)


def _quest_path(quest_id: str) -> Path:
    """Return the file path for a quest."""
    return QUESTS_DIR / f"{quest_id}.json"


def _short_id() -> str:
    """Generate a short quest ID like quest-a1b2c3d4."""
    return f"quest-{uuid4().hex[:8]}"


def create_quest(
    slug: str,
    title: str,
    description: str,
    estimated_impact: str,
    source: str = "manual",
) -> dict:
    """Create a new quest and persist it to disk.

    Returns the created quest dict.
    """
    _ensure_dir()
    quest_id = _short_id()
    today = date.today().isoformat()
    quest = {
        "id": quest_id,
        "slug": slug,
        "title": title,
        "description": description,
        "estimated_impact": estimated_impact,
        "status": "suggested",
        "source": source,
        "created_at": today,
        "started_at": None,
        "completed_at": None,
        "result_summary": None,
        "ci_status": None,
    }
    _quest_path(quest_id).write_text(
        json.dumps(quest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return quest


def get_quest(quest_id: str) -> dict | None:
    """Load a quest by ID. Returns None if not found."""
    path = _quest_path(quest_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_quests(status: str | None = None, slug: str | None = None) -> list[dict]:
    """List quests, optionally filtered by status and/or slug."""
    _ensure_dir()
    quests = load_all_quests()
    if status:
        quests = [q for q in quests if q.get("status") == status]
    if slug:
        quests = [q for q in quests if q.get("slug") == slug]
    # Sort by created_at descending (newest first)
    quests.sort(key=lambda q: q.get("created_at", ""), reverse=True)
    return quests


def update_quest(quest_id: str, **fields) -> dict:
    """Update arbitrary fields on a quest and persist.

    Raises FileNotFoundError if quest doesn't exist.
    """
    quest = get_quest(quest_id)
    if quest is None:
        raise FileNotFoundError(f"Quest not found: {quest_id}")
    for key, value in fields.items():
        if value is not None:
            quest[key] = value
    _quest_path(quest_id).write_text(
        json.dumps(quest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return quest


def transition_quest(quest_id: str, new_status: str) -> dict:
    """Transition a quest to a new status, validating the state machine.

    Raises FileNotFoundError if quest doesn't exist.
    Raises ValueError if the transition is invalid.
    """
    quest = get_quest(quest_id)
    if quest is None:
        raise FileNotFoundError(f"Quest not found: {quest_id}")

    current = quest.get("status", "suggested")
    if new_status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{new_status}'. Allowed: {', '.join(sorted(VALID_STATUSES))}"
        )

    allowed = TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition from '{current}' to '{new_status}'. "
            f"Allowed from '{current}': {', '.join(sorted(allowed)) or 'none'}"
        )

    now = datetime.now().isoformat(timespec="seconds")
    quest["status"] = new_status

    if new_status == "active" and quest.get("started_at") is None:
        quest["started_at"] = now

    if new_status == "completed":
        quest["completed_at"] = now

    _quest_path(quest_id).write_text(
        json.dumps(quest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return quest


def load_all_quests() -> list[dict]:
    """Load all quests from the quests directory."""
    _ensure_dir()
    quests = []
    for path in QUESTS_DIR.glob("quest-*.json"):
        try:
            quests.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return quests
