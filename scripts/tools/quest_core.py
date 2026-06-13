"""Domänkärna: quests (GitHub Milestones som grupperar issues). Transport-fri."""
from __future__ import annotations

from typing import Any


def quest(action: str, **kw: Any) -> Any:
    if action == "list":
        from scripts.issues_client import list_milestones

        return list_milestones(state="open")

    if action == "get":
        from scripts.issues_client import get_milestone, list_issues

        number = kw["number"]
        q = get_milestone(number)
        if not q:
            return {"error": f"Quest (milestone) #{number} not found"}
        q["issues"] = list_issues(milestone=number, state="all")
        return q

    if action == "create":
        from scripts.issues_client import create_milestone

        return create_milestone(
            title=kw["title"],
            description=kw.get("description", ""),
            initiative=kw.get("initiative"),
        )

    if action == "close":
        from scripts.issues_client import close_milestone

        return close_milestone(kw["number"])

    raise ValueError(f"okänd quest-action: {action}")
