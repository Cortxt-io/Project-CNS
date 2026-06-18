"""Connector-wrapper: ``cortxt_gh_project`` (fett verktyg) över gh_project-domänkärnan.

Ersätter de 3 gamla ``cortxt_*_gh_project*``-verktygen (kvar som alias). GraphQL-logiken
(Projects v2) bor nu i ``scripts/tools/gh_project_core.py`` (delas av båda universum).
Kräver CNS_GITHUB_TOKEN med 'project'-scope för skrivning.
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.tools._fat import call


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_gh_project(
        action: str,
        project_id: str | None = None,
        item_id: str | None = None,
        field_id: str | None = None,
        option_id: str | None = None,
        first: int = 30,
    ) -> dict | list:
        """GitHub Projects v2. Välj `action`:

        - `list` — boards för repo-ägaren.
        - `list_items` (project_id; first?) — items i en board.
        - `move_item` (project_id, item_id, field_id, option_id) — flytta kort via single-select.
        """
        return call(
            "gh_project", action,
            project_id=project_id, item_id=item_id, field_id=field_id,
            option_id=option_id, first=first,
        )
