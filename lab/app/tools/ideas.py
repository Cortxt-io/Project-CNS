"""Connector-wrapper: ``cortxt_idea`` (fett verktyg) över idea-domänkärnan.

Ersätter de 4 gamla ``cortxt_*_idea*``-verktygen (kvar som alias). Kärnan
(``scripts/tools/idea_core.py``) gör datalager-mutationen; **pushen av idéfilen ligger
här** (samma split som tidigare — idea_inbox är rent datalager).
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.tools._fat import call, push_idea as _push_idea


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_idea(
        action: str,
        text: str | None = None,
        source: str = "chat",
        slug: str | None = None,
        session_id: str | None = None,
        status: str = "open",
        idea_id: str | None = None,
        append: str | None = None,
        title: str | None = None,
        body: str | None = None,
        quest_number: int | None = None,
        resolution: str | None = None,
        reason: str | None = None,
    ) -> dict | list:
        """Idé-inkorg. Välj `action`:

        - `capture` (text; source?, slug?, session_id?) — fånga en idé.
        - `list` (status?, slug?, session_id?) — lista idéer (status='' = alla).
        - `update` (idea_id; text|append, slug?) — redigera en idé i stället för en dubblett
          (`text` skriver över, `append` lägger till en tidsstämplad notering).
        - `promote` (idea_id, title; slug?, body?, quest_number?) — promota till en issue.
        - `resolve` (idea_id, resolution, reason) — stäng utan issue (done|wontfix|duplicate).
        """
        result = call(
            "idea", action,
            text=text, source=source, slug=slug, session_id=session_id,
            status=status, idea_id=idea_id, append=append, title=title, body=body,
            quest_number=quest_number, resolution=resolution, reason=reason,
        )
        if action == "capture":
            _push_idea(result["id"], f"cns-vault: capture idea {result['id']}")
        elif action == "update":
            _push_idea(result["id"], f"cns-vault: update idea {result['id']}")
        elif action == "promote":
            iid = result["idea"]["id"]
            _push_idea(iid, f"cns-vault: promote idea {iid} to issue #{result['issue']['number']}")
        elif action == "resolve":
            _push_idea(result["id"], f"cns-vault: resolve idea {result['id']} ({resolution})")
        return result
