"""Connector-wrapper: ``cortxt_quest`` (fett verktyg) över quest-domänkärnan.

Ersätter de 4 gamla ``cortxt_*_quest``-verktygen (kvar som alias). En quest = GitHub
Milestone som grupperar issues; progress (closed/total) beräknas av GitHub.
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.tools._fat import call


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_quest(
        action: str,
        number: int | None = None,
        title: str | None = None,
        description: str = "",
        initiative: str | None = None,
    ) -> dict | list:
        """Quests (GitHub Milestones). Välj `action`:

        - `list` — öppna quests med progress (closed/total).
        - `get` (number) — en quest med dess issues.
        - `create` (title; description?, initiative?) — skapa en quest.
        - `close` (number) — stäng en quest (issues behåller sitt eget tillstånd).
        """
        return call(
            "quest", action,
            number=number, title=title, description=description, initiative=initiative,
        )
