"""Connector-wrapper: ``cortxt_issue`` (fett verktyg) över issue-domänkärnan.

Ett fett verktyg ersätter de 10 gamla granulära ``cortxt_*_issue/-todo``-verktygen
(kvar som bakåtkompat-alias i ``_aliases.py``). Logiken bor i
``scripts/tools/issue_core.py``; denna fil är bara typad transport + dispatch.
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.tools._fat import call


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_issue(
        action: str,
        number: int | None = None,
        node_slug: str | None = None,
        title: str | None = None,
        body: str = "",
        quest_number: int | None = None,
        issue_type: str = "story",
        depends_on: list[int] | None = None,
        text: str | None = None,
        index: int | None = None,
        done: bool = True,
        result_summary: str | None = None,
        given: str | None = None,
        when: str | None = None,
        then: str | None = None,
    ) -> dict | list:
        """Arbetsuppgifter (GitHub Issues). Välj `action`:

        - `list` (node_slug?) — öppna issues, valfritt filtrerat på nod.
        - `get` (number) — en issue med nodkontext.
        - `create` (node_slug, title; body?, quest_number?, issue_type?, depends_on?) — skapa.
        - `close` (number, result_summary) — stäng med avslutskommentar.
        - `move_to_quest` (number; quest_number?) — flytta till/från quest (milestone).
        - `add_todo` (number, text) — lägg en todo-checkbox i body.
        - `check_todo` (number, index; done?) — bocka todo på/av via 0-baserat index.
        - `set_type` (number, issue_type) — story|bug|spike|chore.
        - `set_depends_on` (number, depends_on) — sätt beroende-issues (tom lista rensar).
        - `add_acceptance` (number, given, when, then) — Given/When/Then-acceptanskriterium.
        """
        return call(
            "issue", action,
            number=number, node_slug=node_slug, title=title, body=body,
            quest_number=quest_number, issue_type=issue_type, depends_on=depends_on,
            text=text, index=index, done=done, result_summary=result_summary,
            given=given, when=when, then=then,
        )
