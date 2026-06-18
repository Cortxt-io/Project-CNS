"""Connector-wrapper: ``cortxt_lease`` (fett verktyg) över lease-domänkärnan.

Ersätter de 4 gamla ``cortxt_*_issue``-lease-verktygen (kvar som alias). **Ägaren härleds
här** ur OAuth-token (GitHub-login) och injiceras i kärnan — agenten anger den aldrig, så
ett pass kan bara släppa/heartbeata sina egna claims.
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.tools._fat import call, owner as _owner


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_lease(action: str, number: int | None = None) -> dict | list:
        """Efemära issue-claims (Redis, fail-open). Välj `action`:

        - `claim` (number) — claima en issue atomiskt så inget annat pass dubbelarbetar den.
        - `release` (number) — släpp din claim (bara om du håller den).
        - `heartbeat` (number) — förnya din claims TTL.
        - `list` — alla hållna claims just nu (vem äger vad).
        """
        return call("lease", action, number=number, owner=_owner())
