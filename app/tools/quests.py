"""Quest tools: GitHub Milestones grouping N issues (progress computed by GitHub).

A quest is a GitHub milestone that groups several work-item issues into one work
package; its progress (closed/total issues) is computed by GitHub. This replaces
the old quest_manager JSON lifecycle — the cortxt_*_quest names are kept but now
operate on milestones, so the claude.ai connector must be re-authed/refreshed.
"""

from __future__ import annotations

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_list_quests() -> list[dict]:
        """List open quests (GitHub milestones) with progress (closed/total issues)."""
        from scripts.issues_client import list_milestones
        return list_milestones(state="open")

    @mcp.tool()
    def cortxt_get_quest(number: int) -> dict:
        """Get a quest (milestone) with its issues. `number` is the milestone number."""
        from scripts.issues_client import get_milestone, list_issues
        quest = get_milestone(number)
        if not quest:
            return {"error": f"Quest (milestone) #{number} not found"}
        quest["issues"] = list_issues(milestone=number, state="all")
        return quest

    @mcp.tool()
    def cortxt_create_quest(title: str, description: str = "") -> dict:
        """Create a quest (GitHub milestone) to group several issues under one work package."""
        from scripts.issues_client import create_milestone
        return create_milestone(title=title, description=description)

    @mcp.tool()
    def cortxt_close_quest(number: int) -> dict:
        """Close a quest (milestone). Its issues keep their own open/closed state."""
        from scripts.issues_client import close_milestone
        return close_milestone(number)
