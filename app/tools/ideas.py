"""Idea-inbox tools: capture, list, promote to a GitHub Issue."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_capture_idea(
        text: str,
        source: str = "chat",
        slug: str | None = None,
        session_id: str | None = None,
    ) -> dict:
        """Capture a raw idea into the inbox — lighter than a quest.

        Use this for any thought worth keeping that isn't yet an actionable task.
        `source` is "chat" or "code"; `slug` optionally links the idea to a node;
        `session_id` optionally ties it to the session it was born in, so a
        session's ideas can be enumerated later (route-session / wake-on-session).
        """
        from scripts.idea_inbox import capture_idea, IDEAS_DIR
        from app.git_ops import push_file_immediately
        idea = capture_idea(text=text, source=source, slug=slug, session_id=session_id)
        idea_path = IDEAS_DIR / f"{idea['id']}.json"
        push_file_immediately(idea_path, f"cns-vault: capture idea {idea['id']}")
        return idea

    @mcp.tool()
    def cortxt_list_ideas(
        status: str = "open",
        slug: str | None = None,
        session_id: str | None = None,
    ) -> list[dict]:
        """List captured ideas, newest first. Pass status='' to include all.

        Filter by `slug` (node) and/or `session_id` (the session that bore them).
        """
        from scripts.idea_inbox import list_ideas
        return list_ideas(status=status or None, slug=slug, session_id=session_id)

    @mcp.tool()
    def cortxt_promote_idea_to_issue(
        idea_id: str,
        title: str,
        slug: str | None = None,
        body: str | None = None,
        quest_number: int | None = None,
    ) -> dict:
        """Promote an inbox idea into a GitHub Issue (a node work item).

        The issue's node comes from the idea (or the `slug` argument if the idea has
        none); its body defaults to the idea's text. `quest_number` optionally files
        the new issue under a quest (GitHub milestone, see cortxt_list_quests). The
        idea is kept and marked 'promoted' to the new issue. Returns {"idea", "issue"}.
        """
        from scripts.idea_inbox import get_idea, mark_promoted, IDEAS_DIR
        from scripts.issues_client import create_issue
        from app.git_ops import push_file_immediately

        idea = get_idea(idea_id)
        if idea is None:
            raise ToolError(f"Idea {idea_id} not found")
        if idea.get("status") == "promoted":
            raise ToolError(
                f"Idea {idea_id} was already promoted to {idea.get('promoted_to')}"
            )

        node_slug = slug or idea.get("slug")
        if not node_slug:
            raise ToolError(
                "Idea has no linked slug — pass `slug` to say which node the issue is for."
            )

        issue = create_issue(
            node_slug=node_slug, title=title, body=body or idea["text"], milestone=quest_number
        )

        idea = mark_promoted(idea_id, f"#{issue['number']}")
        idea_path = IDEAS_DIR / f"{idea_id}.json"
        push_file_immediately(
            idea_path, f"cns-vault: promote idea {idea_id} to issue #{issue['number']}"
        )

        return {"idea": idea, "issue": issue}
