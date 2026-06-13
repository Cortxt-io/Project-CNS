"""Connector-wrapper: ``cortxt_wiki`` (fett verktyg) över wiki-domänkärnan.

Ersätter de 3 gamla ``cortxt_*_wiki_page*``-verktygen (kvar som alias). Contents-API-
logiken mot ``{repo}.wiki`` bor nu i ``scripts/tools/wiki_core.py``.
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.tools._fat import call


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_wiki(
        action: str,
        page: str | None = None,
        content: str | None = None,
        message: str = "",
    ) -> dict | list:
        """GitHub Wiki. Välj `action`:

        - `list` — wiki-sidor (root).
        - `read` (page) — läs en sida (namn utan .md).
        - `write` (page, content; message?) — skapa/uppdatera en sida.
        """
        return call("wiki", action, page=page, content=content, message=message)
