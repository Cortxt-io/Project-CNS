"""Domänkärna: idé-inkorg. Transport-fri — datalager-mutation, INGEN GitHub-push.

Push av idéfilen ligger i wrappern (universum A: ``app/tools/ideas.py``; universum B:
``agent_host``), samma split som tidigare (idea_inbox är rent datalager). Write-actions
returnerar objektet inkl. ``id`` så wrappern vet vilken fil att pusha.
"""
from __future__ import annotations

from typing import Any


def idea(action: str, **kw: Any) -> Any:
    if action == "capture":
        from scripts.idea_inbox import capture_idea

        return capture_idea(
            text=kw["text"],
            source=kw.get("source", "chat"),
            slug=kw.get("slug"),
            session_id=kw.get("session_id"),
        )

    if action == "list":
        from scripts.idea_inbox import list_ideas

        return list_ideas(
            status=kw.get("status", "open") or None,
            slug=kw.get("slug"),
            session_id=kw.get("session_id"),
        )

    if action == "update":
        from scripts.idea_inbox import update_idea

        return update_idea(
            idea_id=kw["idea_id"],
            text=kw.get("text"),
            append=kw.get("append"),
            slug=kw.get("slug"),
        )

    if action == "promote":
        from scripts.idea_inbox import get_idea, mark_promoted
        from scripts.issues_client import create_issue

        idea_id = kw["idea_id"]
        idea_obj = get_idea(idea_id)
        if idea_obj is None:
            raise ValueError(f"Idea {idea_id} not found")
        if idea_obj.get("status") == "promoted":
            raise ValueError(
                f"Idea {idea_id} was already promoted to {idea_obj.get('promoted_to')}"
            )
        node_slug = kw.get("slug") or idea_obj.get("slug")
        if not node_slug:
            raise ValueError(
                "Idea has no linked slug — pass `slug` to say which node the issue is for."
            )
        issue_obj = create_issue(
            node_slug=node_slug,
            title=kw["title"],
            body=kw.get("body") or idea_obj["text"],
            milestone=kw.get("quest_number"),
        )
        idea_obj = mark_promoted(idea_id, f"#{issue_obj['number']}")
        return {"idea": idea_obj, "issue": issue_obj}

    if action == "resolve":
        from scripts.idea_inbox import get_idea, resolve_idea

        idea_id = kw["idea_id"]
        idea_obj = get_idea(idea_id)
        if idea_obj is None:
            raise ValueError(f"Idea {idea_id} not found")
        if idea_obj.get("status") in ("promoted", "resolved"):
            raise ValueError(
                f"Idea {idea_id} is already {idea_obj.get('status')} — cannot resolve again."
            )
        return resolve_idea(idea_id, kw["resolution"], kw["reason"])

    raise ValueError(f"okänd idea-action: {action}")
