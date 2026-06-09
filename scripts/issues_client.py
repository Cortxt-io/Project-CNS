"""GitHub Issues client for CNS — issues as the work-item layer (replaces quests).

Mirrors ``app/git_ops.py``: pure GitHub REST/GraphQL API, no ``git`` subprocess
(Railway has no ``.git/``). A CNS node maps to its work items via the label
``node:<slug>``; an issue belongs to exactly one node. Coarse lifecycle is the
issue's open/closed state; the fine-grained stage (suggested → active →
in_progress → done) lives on a GitHub Projects (v2) board — see
``set_project_status``.

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
GITHUB_GRAPHQL = "https://api.github.com/graphql"
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
        "labels": [l.get("name") for l in issue.get("labels", []) if isinstance(l, dict)],
    }


# ---------------------------------------------------------------------------
# REST: issue CRUD  (1:1 with the old quest_manager surface)
# ---------------------------------------------------------------------------


def list_issues(
    node_slug: Optional[str] = None,
    state: str = "open",
    token: Optional[str] = None,
) -> list[dict]:
    """List node issues. Filters by ``node:<slug>`` label when *node_slug* given.

    Pull requests are excluded (the REST issues endpoint includes them).
    Mirrors ``quest_manager.list_quests``.
    """
    repo, _ = _require_config(token)
    params: dict[str, str] = {"state": state, "per_page": "100"}
    if node_slug:
        params["labels"] = node_label(node_slug)
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
    token: Optional[str] = None,
) -> dict:
    """Create an issue tied to *node_slug*. Mirrors ``create_quest``.

    The ``node:<slug>`` label is auto-created by GitHub if it doesn't exist.
    A human-readable ``Node: <slug>`` line is prepended to the body.
    """
    repo, _ = _require_config(token)
    full_body = f"Node: `{node_slug}`\n\n{body}".rstrip() + "\n"
    resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/issues",
        headers=_headers(token),
        json={"title": title, "body": full_body, "labels": [node_label(node_slug)]},
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
# Projects v2 (GraphQL) — fine-grained lifecycle stage
# ---------------------------------------------------------------------------
#
# Stage (suggested/active/in_progress/done) is a single-select "Status" field on
# a GitHub Projects v2 board. Setting it needs the project node-id, the field id
# and the target option id — all discovered via GraphQL. Configure the board via
# env so this stays data-driven:
#   CNS_GH_PROJECT_NUMBER   the Projects v2 number (e.g. 1)
#   CNS_GH_PROJECT_OWNER    the org/user that owns the project (defaults to repo owner)
#
# Guarded: if the project isn't configured, set_project_status is a no-op that
# returns {"configured": False} rather than raising, so REST issue flow works
# before the board exists.


def _graphql(query: str, variables: dict, token: Optional[str]) -> dict:
    resp = requests.post(
        GITHUB_GRAPHQL,
        headers={"Authorization": f"Bearer {_resolve_token(token)}"},
        json={"query": query, "variables": variables},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        raise RuntimeError(f"GraphQL error: {data['errors']}")
    return data["data"]


def set_project_status(
    number: int,
    status: str,
    token: Optional[str] = None,
) -> dict:
    """Set an issue's Projects-v2 Status column to *status* (e.g. "In progress").

    Returns {"configured": False} when CNS_GH_PROJECT_NUMBER is unset (no-op),
    so callers don't need to special-case an un-provisioned board.

    NOTE: requires a token with the ``project`` scope. Implementation is staged
    for step 1 — the GraphQL discovery (project id, Status field id, option id,
    item id for this issue) is wired in step 2 once the board exists. See the
    module docstring and the plan's decision B.
    """
    proj_number = os.getenv("CNS_GH_PROJECT_NUMBER")
    if not proj_number:
        logger.info("CNS_GH_PROJECT_NUMBER unset — skipping project status update")
        return {"configured": False, "number": number, "status": status}
    # Discovery + updateProjectV2ItemFieldValue mutation land in step 2 (needs the
    # provisioned board's ids). Kept explicit rather than half-implemented.
    raise NotImplementedError(
        "Projects v2 status update pending board provisioning (step 2)."
    )
