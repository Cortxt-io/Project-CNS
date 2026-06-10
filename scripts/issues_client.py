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
import re
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
NODE_LABEL_PREFIX = "node:"
_TIMEOUT = 20

# A todo is a GitHub task-list checkbox in the issue body: ``- [ ] text`` / ``- [x] text``.
# This keeps the sub-task level on GitHub (the source of truth), rendered as native
# progress, with no side store to sync. (See CLAUDE.md: GitHub = sanning.)
_TODO_RE = re.compile(r"^(\s*[-*]\s+)\[([ xX])\]\s+(.*)$")

# --- Decomposition primitives (work-model taxonomy) ---------------------------
# Branschstandard-typ på en issue, lagrad som label ``type:<value>`` analogt med
# ``node:<slug>``. Default ``story`` = fallback för gamla issues utan label.
TYPE_LABEL_PREFIX = "type:"
VALID_ISSUE_TYPES = {"story", "bug", "spike", "chore"}
DEFAULT_ISSUE_TYPE = "story"

# ``depends_on`` lagras som body-rad ``Depends-on: #12, #34`` (labels passar dåligt
# för N dynamiska nummer). Idempotent replace via denna regex.
_DEPENDS_RE = re.compile(r"^Depends-on:\s*(.*)$", re.MULTILINE)
_ISSUE_REF_RE = re.compile(r"#?(\d+)")

# Acceptanskriterier = checkboxar under rubriken ``## Acceptanskriterier`` (Given/When/Then).
# Sektionsmedveten parsning skiljer dem från vanliga todos.
ACCEPTANCE_HEADING = "## Acceptanskriterier"
_HEADING_RE = re.compile(r"^#{1,6}\s+")


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


def parse_todos(body: Optional[str]) -> list[dict]:
    """Parse task-list checkboxes from an issue body into ``{index, text, done}``.

    ``index`` is the checkbox's ordinal in the body (0-based), the handle
    ``set_todo``/``cortxt_check_todo`` use to flip it. Non-checkbox lines are ignored.
    """
    todos: list[dict] = []
    for line in (body or "").splitlines():
        m = _TODO_RE.match(line)
        if m:
            todos.append(
                {
                    "index": len(todos),
                    "text": m.group(3).strip(),
                    "done": m.group(2).lower() == "x",
                }
            )
    return todos


def type_label(value: str) -> str:
    """The canonical label encoding an issue's type: ``type:<value>``."""
    return f"{TYPE_LABEL_PREFIX}{value}"


def type_from_labels(labels: list[dict] | list[str]) -> str:
    """Extract the issue type from its labels, defaulting to ``story`` (fallback)."""
    for lab in labels:
        name = lab.get("name") if isinstance(lab, dict) else lab
        if name and name.startswith(TYPE_LABEL_PREFIX):
            value = name[len(TYPE_LABEL_PREFIX):]
            if value in VALID_ISSUE_TYPES:
                return value
    return DEFAULT_ISSUE_TYPE


def parse_depends_on(body: Optional[str]) -> list[int]:
    """Parse the ``Depends-on: #12, #34`` body line into a list of issue numbers.

    Empty list = no declared dependencies (fallback for old issues).
    """
    m = _DEPENDS_RE.search(body or "")
    if not m:
        return []
    return [int(ref) for ref in _ISSUE_REF_RE.findall(m.group(1))]


def parse_acceptance(body: Optional[str]) -> list[dict]:
    """Parse acceptance-criteria checkboxes under the ``## Acceptanskriterier`` heading.

    Section-aware: only checkboxes after that heading (until the next ``## `` heading)
    count, so they are kept distinct from ordinary todos. Returns ``{index, text, done}``
    where ``index`` is the criterion's ordinal among acceptance criteria (0-based).
    """
    criteria: list[dict] = []
    in_section = False
    for line in (body or "").splitlines():
        stripped = line.strip()
        if stripped == ACCEPTANCE_HEADING:
            in_section = True
            continue
        if in_section and _HEADING_RE.match(line):
            break  # next heading ends the section
        if in_section:
            m = _TODO_RE.match(line)
            if m:
                criteria.append(
                    {
                        "index": len(criteria),
                        "text": m.group(3).strip(),
                        "done": m.group(2).lower() == "x",
                    }
                )
    return criteria


def _normalize(issue: dict) -> dict:
    """Shape a raw GitHub issue into the CNS-facing form the old quest dict had.

    Keeps the migration mechanical: number↔id, node_slug↔slug, state, urls.
    ``todos`` are the body's task-list checkboxes (the sub-task level under an issue).
    ``type``/``depends_on``/``acceptance_criteria`` are the work-model decomposition
    primitives — all derived here with empty/default fallbacks so old issues and the
    dashboard never break.
    """
    body = issue.get("body") or ""
    labels = issue.get("labels", [])
    return {
        "number": issue.get("number"),
        "node_slug": slug_from_labels(labels),
        "title": issue.get("title", ""),
        "body": body,
        "state": issue.get("state"),  # open | closed
        "url": issue.get("html_url"),
        "created_at": issue.get("created_at"),
        "closed_at": issue.get("closed_at"),
        "quest": (issue.get("milestone") or {}).get("number"),
        "labels": [l.get("name") for l in labels if isinstance(l, dict)],
        "todos": parse_todos(body),
        "type": type_from_labels(labels),
        "depends_on": parse_depends_on(body),
        "acceptance_criteria": parse_acceptance(body),
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


def _depends_line(depends_on: Optional[list[int]]) -> str:
    """Render the ``Depends-on:`` body line for a list of issue numbers, or ''."""
    nums = [int(n) for n in (depends_on or [])]
    if not nums:
        return ""
    return "Depends-on: " + ", ".join(f"#{n}" for n in nums)


def create_issue(
    node_slug: str,
    title: str,
    body: str = "",
    milestone: Optional[int] = None,
    issue_type: str = DEFAULT_ISSUE_TYPE,
    depends_on: Optional[list[int]] = None,
    token: Optional[str] = None,
) -> dict:
    """Create an issue tied to *node_slug*, optionally in a *milestone* (its quest).

    The ``node:<slug>`` label is auto-created by GitHub if it doesn't exist.
    A human-readable ``Node: <slug>`` line is prepended to the body, followed by
    the ``Depends-on:`` line when dependencies are given. *issue_type* is stored as
    the ``type:<value>`` label (default ``story``).
    """
    repo, _ = _require_config(token)
    if issue_type not in VALID_ISSUE_TYPES:
        raise ValueError(
            f"Invalid issue_type {issue_type!r}; expected one of {sorted(VALID_ISSUE_TYPES)}"
        )
    header = f"Node: `{node_slug}`"
    dep_line = _depends_line(depends_on)
    if dep_line:
        header = f"{header}\n{dep_line}"
    full_body = f"{header}\n\n{body}".rstrip() + "\n"
    payload: dict[str, Any] = {
        "title": title,
        "body": full_body,
        "labels": [node_label(node_slug), type_label(issue_type)],
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
# Todos == task-list checkboxes in the issue body (the sub-task level)
# ---------------------------------------------------------------------------


def update_issue_body(number: int, body: str, token: Optional[str] = None) -> dict:
    """PATCH an issue's body wholesale. Used by add_todo/set_todo."""
    repo, _ = _require_config(token)
    resp = requests.patch(
        f"{GITHUB_API}/repos/{repo}/issues/{number}",
        headers=_headers(token),
        json={"body": body},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return _normalize(resp.json())


def _raw_body(number: int, token: Optional[str]) -> str:
    """Fetch an issue's raw body (not normalized). Raises ValueError if missing."""
    repo, _ = _require_config(token)
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/issues/{number}",
        headers=_headers(token),
        timeout=_TIMEOUT,
    )
    if resp.status_code == 404:
        raise ValueError(f"Issue #{number} not found")
    resp.raise_for_status()
    return resp.json().get("body") or ""


def add_todo(number: int, text: str, token: Optional[str] = None) -> dict:
    """Append a new unchecked todo (``- [ ] text``) to the issue body."""
    body = _raw_body(number, token)
    new_body = body.rstrip("\n") + f"\n- [ ] {text}\n"
    return update_issue_body(number, new_body, token=token)


def set_todo(
    number: int, index: int, done: bool = True, token: Optional[str] = None
) -> dict:
    """Flip the *index*-th checkbox (0-based, body order) to done/undone.

    Raises ValueError if there is no checkbox at that index.
    """
    body = _raw_body(number, token)
    lines = body.splitlines()
    count = -1
    for i, line in enumerate(lines):
        m = _TODO_RE.match(line)
        if m:
            count += 1
            if count == index:
                mark = "x" if done else " "
                lines[i] = f"{m.group(1)}[{mark}] {m.group(3)}"
                break
    else:
        raise ValueError(f"No todo at index {index} on issue #{number}")
    new_body = "\n".join(lines)
    if body.endswith("\n"):
        new_body += "\n"
    return update_issue_body(number, new_body, token=token)


# ---------------------------------------------------------------------------
# Decomposition primitives: type / depends_on / acceptance criteria
# ---------------------------------------------------------------------------


def _issue_labels(number: int, token: Optional[str]) -> list[str]:
    """Fetch an issue's current label names."""
    repo, _ = _require_config(token)
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/issues/{number}",
        headers=_headers(token),
        timeout=_TIMEOUT,
    )
    if resp.status_code == 404:
        raise ValueError(f"Issue #{number} not found")
    resp.raise_for_status()
    return [l.get("name") for l in resp.json().get("labels", []) if isinstance(l, dict)]


def set_issue_type(number: int, issue_type: str, token: Optional[str] = None) -> dict:
    """Set an issue's ``type:<value>`` label, replacing any existing type label."""
    if issue_type not in VALID_ISSUE_TYPES:
        raise ValueError(
            f"Invalid issue_type {issue_type!r}; expected one of {sorted(VALID_ISSUE_TYPES)}"
        )
    repo, _ = _require_config(token)
    labels = [n for n in _issue_labels(number, token) if not n.startswith(TYPE_LABEL_PREFIX)]
    labels.append(type_label(issue_type))
    resp = requests.patch(
        f"{GITHUB_API}/repos/{repo}/issues/{number}",
        headers=_headers(token),
        json={"labels": labels},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return _normalize(resp.json())


def set_depends_on(
    number: int, depends_on: list[int], token: Optional[str] = None
) -> dict:
    """Set an issue's ``Depends-on:`` body line idempotently (replace, not append).

    Replaces an existing ``Depends-on:`` line if present; otherwise inserts it right
    after the ``Node:`` header line. An empty list removes the line.
    """
    body = _raw_body(number, token)
    dep_line = _depends_line(depends_on)
    if _DEPENDS_RE.search(body):
        if dep_line:
            new_body = _DEPENDS_RE.sub(dep_line, body, count=1)
        else:
            # drop the line (and a trailing blank artefact is harmless)
            new_body = _DEPENDS_RE.sub("", body, count=1)
    elif dep_line:
        lines = body.splitlines()
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("Node:"):
                insert_at = i + 1
                break
        lines.insert(insert_at, dep_line)
        new_body = "\n".join(lines)
        if body.endswith("\n"):
            new_body += "\n"
    else:
        return _normalize_from_number(number, token)
    return update_issue_body(number, new_body, token=token)


def _normalize_from_number(number: int, token: Optional[str]) -> dict:
    """Fetch + normalize an issue (used when a mutation is a no-op)."""
    issue = get_issue(number, token=token)
    if issue is None:
        raise ValueError(f"Issue #{number} not found")
    return issue


def add_acceptance_criterion(
    number: int, given: str, when: str, then: str, token: Optional[str] = None
) -> dict:
    """Append a Given/When/Then acceptance criterion under ``## Acceptanskriterier``.

    Ensures the heading exists (creating it at the end of the body if not), then
    appends a ``- [ ] Given … When … Then …`` checkbox. This is the agent-DoD: the
    done-gate is all acceptance checkboxes ticked.
    """
    body = _raw_body(number, token)
    criterion = f"- [ ] Given {given.strip()} When {when.strip()} Then {then.strip()}"
    if ACCEPTANCE_HEADING in body.splitlines():
        lines = body.splitlines()
        # find the end of the acceptance section (next heading or EOF)
        start = lines.index(ACCEPTANCE_HEADING)
        end = len(lines)
        for i in range(start + 1, len(lines)):
            if _HEADING_RE.match(lines[i]):
                end = i
                break
        # insert after the last non-blank line of the section
        insert_at = end
        while insert_at > start + 1 and not lines[insert_at - 1].strip():
            insert_at -= 1
        lines.insert(insert_at, criterion)
        new_body = "\n".join(lines)
        if body.endswith("\n"):
            new_body += "\n"
    else:
        new_body = body.rstrip("\n") + f"\n\n{ACCEPTANCE_HEADING}\n{criterion}\n"
    return update_issue_body(number, new_body, token=token)


# ---------------------------------------------------------------------------
# REST: milestones == quests  (a quest groups N issues; GitHub computes progress)
# ---------------------------------------------------------------------------


# An optional ``initiative`` (top level above epic/quest) is stored as an
# ``Initiative: <name>`` line in the milestone description — no new store, no enum.
_INITIATIVE_RE = re.compile(r"^Initiative:\s*(.*)$", re.MULTILINE)


def parse_initiative(description: Optional[str]) -> Optional[str]:
    """Parse the optional ``Initiative: <name>`` line from a milestone description."""
    m = _INITIATIVE_RE.search(description or "")
    if not m:
        return None
    name = m.group(1).strip()
    return name or None


def _normalize_milestone(ms: dict) -> dict:
    """Shape a raw GitHub milestone into the CNS-facing quest form.

    open_issues/closed_issues come straight from GitHub, so progress is free.
    ``initiative`` is the optional top level (None for old milestones = fallback).
    """
    open_n = ms.get("open_issues", 0) or 0
    closed_n = ms.get("closed_issues", 0) or 0
    total = open_n + closed_n
    description = ms.get("description") or ""
    return {
        "number": ms.get("number"),
        "title": ms.get("title", ""),
        "description": description,
        "initiative": parse_initiative(description),
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


def create_milestone(
    title: str,
    description: str = "",
    initiative: Optional[str] = None,
    token: Optional[str] = None,
) -> dict:
    """Create a quest (milestone). Mirrors ``create_quest`` at the grouping level.

    *initiative* (optional) records the top level above this epic as an
    ``Initiative: <name>`` line prepended to the description.
    """
    repo, _ = _require_config(token)
    full_description = description
    if initiative:
        line = f"Initiative: {initiative.strip()}"
        full_description = f"{line}\n\n{description}".rstrip() if description else line
    resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/milestones",
        headers=_headers(token),
        json={"title": title, "description": full_description},
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
