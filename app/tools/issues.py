"""Work-item tools: GitHub Issues (replaces the quest lifecycle).

A node's work items are GitHub Issues tagged with the ``node:<slug>`` label.
These call ``scripts.issues_client`` with token=None, which uses CNS_GITHUB_TOKEN
(the server token git_ops already relies on). NOTE: these are breaking renames of
the old cortxt_*_quest tools — the claude.ai connector must be re-authed/refreshed.
"""

from __future__ import annotations

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_list_open_issues(node_slug: str | None = None) -> list[dict]:
        """List open work-item issues, optionally filtered to one node via its node:<slug> label."""
        from scripts.issues_client import list_issues
        return list_issues(node_slug=node_slug, state="open")

    @mcp.tool()
    def cortxt_get_issue(number: int) -> dict:
        """Get a work-item issue enriched with its node context (kind/stage/summary)."""
        from scripts.issues_client import get_issue
        from scripts.md_parser import read_node
        issue = get_issue(number)
        if not issue:
            return {"error": f"Issue #{number} not found"}
        slug = issue.get("node_slug")
        if slug:
            try:
                meta, _sections, _ = read_node(slug)
                issue["node_context"] = {
                    "meta": meta,
                    "summary": meta.get("summary", ""),
                    "kind": meta.get("kind", ""),
                    "stage": meta.get("stage", ""),
                }
            except Exception:
                pass
        return issue

    @mcp.tool()
    def cortxt_create_issue(
        node_slug: str, title: str, body: str = "", quest_number: int | None = None
    ) -> dict:
        """Create a work-item issue tied to a node, optionally inside a quest (milestone).

        `quest_number` is a GitHub milestone number (see cortxt_list_quests).
        """
        from scripts.issues_client import create_issue
        return create_issue(node_slug=node_slug, title=title, body=body, milestone=quest_number)

    @mcp.tool()
    def cortxt_close_issue(number: int, result_summary: str) -> dict:
        """Close a work-item issue, leaving the result summary as a closing comment."""
        from scripts.issues_client import close_issue
        return close_issue(number, comment=result_summary)
