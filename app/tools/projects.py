"""Connector-wrapper: ``cortxt_project`` (fett verktyg) över project-domänkärnan.

Ersätter ``cortxt_list_projects``/``cortxt_get_project`` (kvar som alias). Exponerar
catalog.yaml-noderna; läs-only. Logiken bor i ``scripts/tools/project_core.py``.
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.tools._fat import call


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_project(action: str, slug: str | None = None) -> dict | list:
        """Katalognoder (catalog.yaml), läs-only. Välj `action`:

        - `list` — alla noder med metadata (slug, title, kind, type, domain, part_of, …).
        - `get` (slug) — en nods meta + ev. decisions/<slug>.md-prosa.
        """
        return call("project", action, slug=slug)
