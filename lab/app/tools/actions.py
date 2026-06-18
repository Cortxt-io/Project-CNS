"""Connector-wrapper: ``cortxt_action`` (fett verktyg) över action-domänkärnan.

Ersätter de 3 gamla ``cortxt_*_workflow*``-verktygen (kvar som alias). GitHub Actions-
logiken bor nu i ``scripts/tools/action_core.py`` (delas av båda universum).
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.tools._fat import call


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_action(
        action: str,
        workflow_id: str | None = None,
        limit: int = 10,
        ref: str = "main",
        inputs: dict | None = None,
        run_id: int | None = None,
    ) -> dict | list:
        """GitHub Actions. Välj `action`:

        - `list_runs` (workflow_id?, limit?) — senaste körningar.
        - `trigger` (workflow_id; ref?, inputs?) — trigga workflow_dispatch.
        - `get_run` (run_id) — status/conclusion för en körning.
        """
        return call(
            "action", action,
            workflow_id=workflow_id, limit=limit, ref=ref, inputs=inputs, run_id=run_id,
        )
