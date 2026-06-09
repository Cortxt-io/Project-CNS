"""GitHub Issues client for CNS — the work-item layer (replaces the quest store).

Mirrors ``app/git_ops.py``: pure GitHub REST API, no ``git`` subprocess (Railway
has no ``.git/``). Three tiers:
  - node  — a CNS node (node.md); an issue links to it via the ``node:<slug>`` label
  - quest — a GitHub **Milestone** grouping N issues; GitHub computes progress (X/Y)
  - issue — a concrete task, open/closed, optionally assigned to a milestone (its quest)

No GitHub Projects board: a quest's stage is its milestone open/closed + progress,
and node maturity is the node's own ``stage`` field. Milestones need only the
``repo`` scope.

Auth: pass an explicit ``token`` (e.g. the per-user OAuth token the MCP server
already holds via ``get_access_token()``) so calls act as the right user.
Falls back to ``CNS_GITHUB_TOKEN`` for server-initiated calls (webhook mirror,
migration). ``GITHUB_REPO`` (``owner/name``) is the single home for node issues.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
NODE_LABEL_PREFIX = "node:"
_TIMEOUT = 20


# ---------------------------------------------------------------------------
# Config / auth
# ---------------------------------------------------------------------------


def _repo() -> str:
    return os.getenv("GITHUB_REPO", "")


def _resolve_token(token: Optional[str]) -> str:
    return token or os.getenv("CNS_GITHUB_TOKEN", "")


def _headers(token: Optional[str]) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_resolve_token(token)}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


class IssuesConfigError(RuntimeError):
    """Raised when GITHUB_REPO or a usable token is missing."""


def _require_config(token: Optional[str]) -> tuple[str, str]:
    repo, tok = _repo(), _resolve_token(token)
    if not repo or not tok:
        raise IssuesConfigError(
            "GITHUB_REPO and a token (arg or CNS_GITHUB_TOKEN) are required."
        )
    return repo, tok


# ---------------------------------------------------------------------------
# Node <-> issue bridge
# ---------------------------------------------------------------------------


def node_label(slug: str) -> str:
    """The canonical label that ties an issue to a node: ``node:<slug>``."""
    return f"{NODE_LABEL_PREFIX}{slug}"


def slug_from_labels(labels: list[dict] | list[str]) -> Optional[str]:
    """Extract the node slug from an issue's labels, or None."""
    for lab in labels:
        name = lab.get("name") if isinstance(lab, dict) else lab
        if name and name.startswith(NODE_LABEL_PREFIX):
            return name[len(NODE_LABEL_PREFIX):]
    return None


def _normalize(issue: dict) -> dict:
    """Shape a raw GitHub issue into the CNS-facing form the old quest dict had.

    Keeps the migration mechanical: number↔id, node_slug↔slug, state, urls.
    """
    return {
        "number": issue.get("number"),
        "node_slug": slug_from_labels(issue.get("labels", [])),
        "title": issue.get("title", ""),
        "body": issue.get("body") or "",
        "state": issue.get("state"),  # open | closed
        "url": issue.get("html_url"),
        "created_at": issue.get("created_at"),
        "closed_at": issue.get("closed_at"),
        "quest": (issue.get("milestone") or {}).get("number"),
        "labels": [l.get("name") for l in issue.get("labels", []) if isinstance(l, dict)],
    }


# ---------------------------------------------------------------------------
# REST: issue CRUD  (1:1 with the old quest_manager surface)
# ---------------------------------------------------------------------------


def list_issues(
    node_slug: Optional[str] = None,
    state: str = "open",
    milestone: Optional[int] = None,
    token: Optional[str] = None,
) -> list[dict]:
    """List node issues. Filters by ``node:<slug>`` label and/or *milestone* (quest).

    Pull requests are excluded (the REST issues endpoint includes them).
    Mirrors ``quest_manager.list_quests``.
    """
    repo, _ = _require_config(token)
    params: dict[str, str] = {"state": state, "per_page": "100"}
    if node_slug:
        params["labels"] = node_label(node_slug)
    if milestone is not None:
        params["milestone"] = str(milestone)
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/issues",
        headers=_headers(token),
        params=params,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return [_normalize(i) for i in resp.json() if "pull_request" not in i]


def get_issue(number: int, token: Optional[str] = None) -> Optional[dict]:
    """Fetch a single issue, or None if not found. Mirrors ``get_quest``."""
    repo, _ = _require_config(token)
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/issues/{number}",
        headers=_headers(token),
        timeout=_TIMEOUT,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return _normalize(resp.json())


def create_issue(
    node_slug: str,
    title: str,
    body: str = "",
    milestone: Optional[int] = None,
    token: Optional[str] = None,
) -> dict:
    """Create an issue tied to *node_slug*, optionally in a *milestone* (its quest).

    The ``node:<slug>`` label is auto-created by GitHub if it doesn't exist.
    A human-readable ``Node: <slug>`` line is prepended to the body.
    """
    repo, _ = _require_config(token)
    full_body = f"Node: `{node_slug}`\n\n{body}".rstrip() + "\n"
    payload: dict[str, Any] = {
        "title": title,
        "body": full_body,
        "labels": [node_label(node_slug)],
    }
    if milestone is not None:
        payload["milestone"] = milestone
    resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/issues",
        headers=_headers(token),
        json=payload,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return _normalize(resp.json())


def add_comment(number: int, body: str, token: Optional[str] = None) -> dict:
    """Add a comment to an issue (used for the close summary)."""
    repo, _ = _require_config(token)
    resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/issues/{number}/comments",
        headers=_headers(token),
        json={"body": body},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def close_issue(
    number: int,
    comment: Optional[str] = None,
    token: Optional[str] = None,
) -> dict:
    """Close an issue, optionally leaving a summary comment first.

    Mirrors ``transition_quest(id, "completed")`` + ``update_quest(result_summary)``.
    """
    repo, _ = _require_config(token)
    if comment:
        add_comment(number, comment, token=token)
    resp = requests.patch(
        f"{GITHUB_API}/repos/{repo}/issues/{number}",
        headers=_headers(token),
        json={"state": "closed", "state_reason": "completed"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return _normalize(resp.json())


# ---------------------------------------------------------------------------
# REST: milestones == quests  (a quest groups N issues; GitHub computes progress)
# ---------------------------------------------------------------------------


def _normalize_milestone(ms: dict) -> dict:
    """Shape a raw GitHub milestone into the CNS-facing quest form.

    open_issues/closed_issues come straight from GitHub, so progress is free.
    """
    open_n = ms.get("open_issues", 0) or 0
    closed_n = ms.get("closed_issues", 0) or 0
    total = open_n + closed_n
    return {
        "number": ms.get("number"),
        "title": ms.get("title", ""),
        "description": ms.get("description") or "",
        "state": ms.get("state"),  # open | closed
        "open_issues": open_n,
        "closed_issues": closed_n,
        "progress": round(closed_n / total, 3) if total else 0.0,
        "url": ms.get("html_url"),
        "created_at": ms.get("created_at"),
        "closed_at": ms.get("closed_at"),
        "due_on": ms.get("due_on"),
    }


def list_milestones(state: str = "open", token: Optional[str] = None) -> list[dict]:
    """List quests (milestones). Mirrors ``list_quests`` at the grouping level."""
    repo, _ = _require_config(token)
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/milestones",
        headers=_headers(token),
        params={"state": state, "per_page": "100"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return [_normalize_milestone(m) for m in resp.json()]


def get_milestone(number: int, token: Optional[str] = None) -> Optional[dict]:
    """Fetch a single quest (milestone), or None if not found."""
    repo, _ = _require_config(token)
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/milestones/{number}",
        headers=_headers(token),
        timeout=_TIMEOUT,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return _normalize_milestone(resp.json())


def create_milestone(title: str, description: str = "", token: Optional[str] = None) -> dict:
    """Create a quest (milestone). Mirrors ``create_quest`` at the grouping level."""
    repo, _ = _require_config(token)
    resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/milestones",
        headers=_headers(token),
        json={"title": title, "description": description},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return _normalize_milestone(resp.json())


def close_milestone(number: int, token: Optional[str] = None) -> dict:
    """Close a quest (milestone). Issues within keep their own open/closed state."""
    repo, _ = _require_config(token)
    resp = requests.patch(
        f"{GITHUB_API}/repos/{repo}/milestones/{number}",
        headers=_headers(token),
        json={"state": "closed"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return _normalize_milestone(resp.json())
