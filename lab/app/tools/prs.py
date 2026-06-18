"""Connector-wrapper: ``cortxt_pr`` (fett verktyg) över pr-domänkärnan.

Ersätter de 4 gamla ``cortxt_*_pr``-verktygen (kvar som alias). Logiken bor i
``scripts/prs_client.py`` (plain REST) via ``scripts/tools/pr_core.py``.
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.tools._fat import call


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_pr(
        action: str,
        number: int | None = None,
        state: str = "open",
        title: str | None = None,
        head: str | None = None,
        base: str = "main",
        body: str = "",
        draft: bool = False,
        reviewers: list[str] | None = None,
    ) -> dict | list:
        """Pull Requests. Välj `action`:

        - `list` (state?) — PR:er (open|closed|all).
        - `get` (number) — en PR med review-status och checks.
        - `create` (title, head; base?, body?, draft?) — skapa en PR.
        - `set_reviewers` (number, reviewers) — begär granskning (lista av GitHub-login).
        """
        return call(
            "pr", action,
            number=number, state=state, title=title, head=head, base=base,
            body=body, draft=draft, reviewers=reviewers,
        )
