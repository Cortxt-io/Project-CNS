"""GitHub Actions tools — trigger workflows and inspect run status."""

from __future__ import annotations

import os
import requests
from fastmcp import FastMCP

_GH_API = "https://api.github.com"
_TIMEOUT = 20


def _repo() -> str:
    return os.getenv("GITHUB_REPO", "")


def _headers() -> dict:
    token = os.getenv("CNS_GITHUB_TOKEN", "")
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_list_workflow_runs(workflow_id: str | None = None, limit: int = 10) -> list[dict]:
        """List recent GitHub Actions workflow runs.

        workflow_id: filename or numeric ID to filter (e.g. 'export-dashboard.yml').
        Omit to list runs across all workflows.
        """
        if workflow_id:
            url = f"{_GH_API}/repos/{_repo()}/actions/workflows/{workflow_id}/runs"
        else:
            url = f"{_GH_API}/repos/{_repo()}/actions/runs"
        resp = requests.get(
            url, headers=_headers(), params={"per_page": limit}, timeout=_TIMEOUT
        )
        resp.raise_for_status()
        runs = resp.json().get("workflow_runs", [])
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "workflow": r.get("path", ""),
                "status": r["status"],
                "conclusion": r["conclusion"],
                "branch": r["head_branch"],
                "created_at": r["created_at"],
                "url": r["html_url"],
            }
            for r in runs
        ]

    @mcp.tool()
    def cortxt_trigger_workflow(
        workflow_id: str, ref: str = "main", inputs: dict | None = None
    ) -> dict:
        """Trigger a workflow_dispatch event on a GitHub Actions workflow.

        workflow_id: workflow filename (e.g. 'export-dashboard.yml').
        ref: branch or tag to run on (default: 'main').
        inputs: optional dict of workflow input values.
        """
        resp = requests.post(
            f"{_GH_API}/repos/{_repo()}/actions/workflows/{workflow_id}/dispatches",
            headers=_headers(),
            json={"ref": ref, "inputs": inputs or {}},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return {"triggered": True, "workflow": workflow_id, "ref": ref}

    @mcp.tool()
    def cortxt_get_workflow_run(run_id: int) -> dict:
        """Get status and conclusion of a specific workflow run by its ID."""
        resp = requests.get(
            f"{_GH_API}/repos/{_repo()}/actions/runs/{run_id}",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        if resp.status_code == 404:
            return {"error": f"Run {run_id} not found"}
        resp.raise_for_status()
        r = resp.json()
        return {
            "id": r["id"],
            "name": r["name"],
            "status": r["status"],
            "conclusion": r["conclusion"],
            "branch": r["head_branch"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "url": r["html_url"],
        }
