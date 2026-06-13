"""Domänkärna: GitHub Actions (trigga workflows, inspektera körningar). Transport-fri."""
from __future__ import annotations

import os
from typing import Any

_GH_API = "https://api.github.com"
_TIMEOUT = 20


def _repo() -> str:
    return os.getenv("GITHUB_REPO", "")


def _headers() -> dict:
    token = os.getenv("CNS_GITHUB_TOKEN", "")
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def action(action: str, **kw: Any) -> Any:  # noqa: A002 — domännamnet är 'action'
    import requests

    if action == "list_runs":
        workflow_id = kw.get("workflow_id")
        limit = kw.get("limit") or 10  # None (wrapper-default) → 10
        if workflow_id:
            url = f"{_GH_API}/repos/{_repo()}/actions/workflows/{workflow_id}/runs"
        else:
            url = f"{_GH_API}/repos/{_repo()}/actions/runs"
        resp = requests.get(url, headers=_headers(), params={"per_page": limit}, timeout=_TIMEOUT)
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

    if action == "trigger":
        resp = requests.post(
            f"{_GH_API}/repos/{_repo()}/actions/workflows/{kw['workflow_id']}/dispatches",
            headers=_headers(),
            json={"ref": kw.get("ref", "main"), "inputs": kw.get("inputs") or {}},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return {"triggered": True, "workflow": kw["workflow_id"], "ref": kw.get("ref", "main")}

    if action == "get_run":
        resp = requests.get(
            f"{_GH_API}/repos/{_repo()}/actions/runs/{kw['run_id']}",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        if resp.status_code == 404:
            return {"error": f"Run {kw['run_id']} not found"}
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

    raise ValueError(f"okänd action-action: {action}")
