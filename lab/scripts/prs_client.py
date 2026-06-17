"""Pull Request-klient för CNS — plain REST-lager (samma mönster som ``issues_client``).

Logiken bodde tidigare direkt i ``app/tools/prs.py`` (MCP-wrappers). Den är nu lyft hit
som rena, importbara funktioner så ÄVEN dispatch-loopen (#59) kan öppna en **draft-PR**
utan att gå via MCP-servern. ``app/tools/prs.py`` blev tunna wrappers som delegerar hit
— samma split som ``issues_client`` ↔ ``app/tools/issues.py``.

Auth: ``GITHUB_REPO`` + token (arg eller ``CNS_GITHUB_TOKEN``), precis som issues_client.
"""
from __future__ import annotations

import os
from typing import Optional

import requests

GITHUB_API = "https://api.github.com"
_TIMEOUT = 20


def _repo() -> str:
    return os.getenv("GITHUB_REPO", "")


def _resolve_token(token: Optional[str]) -> str:
    return token or os.getenv("CNS_GITHUB_TOKEN", "")


def _headers(token: Optional[str] = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_resolve_token(token)}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def list_prs(state: str = "open", token: Optional[str] = None) -> list[dict]:
    """Lista pull requests (state: open | closed | all)."""
    resp = requests.get(
        f"{GITHUB_API}/repos/{_repo()}/pulls",
        headers=_headers(token),
        params={"state": state, "per_page": 30},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return [
        {
            "number": pr["number"],
            "title": pr["title"],
            "state": pr["state"],
            "author": pr["user"]["login"],
            "head": pr["head"]["ref"],
            "base": pr["base"]["ref"],
            "url": pr["html_url"],
            "draft": pr["draft"],
            "created_at": pr["created_at"],
            "updated_at": pr["updated_at"],
        }
        for pr in resp.json()
    ]


def get_pr(number: int, token: Optional[str] = None) -> dict:
    """Hämta en PR med review-status/checks, eller ``{"error": ...}`` om 404."""
    resp = requests.get(
        f"{GITHUB_API}/repos/{_repo()}/pulls/{number}",
        headers=_headers(token),
        timeout=_TIMEOUT,
    )
    if resp.status_code == 404:
        return {"error": f"PR #{number} not found"}
    resp.raise_for_status()
    pr = resp.json()
    return {
        "number": pr["number"],
        "title": pr["title"],
        "state": pr["state"],
        "author": pr["user"]["login"],
        "body": pr["body"] or "",
        "head": pr["head"]["ref"],
        "base": pr["base"]["ref"],
        "url": pr["html_url"],
        "draft": pr["draft"],
        "mergeable": pr.get("mergeable"),
        "created_at": pr["created_at"],
        "updated_at": pr["updated_at"],
    }


def create_pr(
    title: str,
    head: str,
    base: str = "main",
    body: str = "",
    draft: bool = False,
    token: Optional[str] = None,
) -> dict:
    """Skapa en PR. ``head`` = branch att merga från, ``base`` = mål (default main)."""
    resp = requests.post(
        f"{GITHUB_API}/repos/{_repo()}/pulls",
        headers=_headers(token),
        json={"title": title, "head": head, "base": base, "body": body, "draft": draft},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    pr = resp.json()
    return {"number": pr["number"], "url": pr["html_url"], "state": pr["state"], "draft": pr["draft"]}


def merge_pr(number: int, *, method: str = "squash", token: Optional[str] = None) -> dict:
    """Merga en PR (method: merge | squash | rebase). Kastar vid fel (t.ex. draft/ej mergebar)."""
    resp = requests.put(
        f"{GITHUB_API}/repos/{_repo()}/pulls/{number}/merge",
        headers=_headers(token),
        json={"merge_method": method},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return {"number": number, "merged": bool(data.get("merged", True)), "message": data.get("message")}


def close_pr(number: int, token: Optional[str] = None) -> dict:
    """Stäng en PR utan merge (PATCH state=closed)."""
    resp = requests.patch(
        f"{GITHUB_API}/repos/{_repo()}/pulls/{number}",
        headers=_headers(token),
        json={"state": "closed"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return {"number": number, "state": "closed"}


def set_reviewers(number: int, reviewers: list[str], token: Optional[str] = None) -> dict:
    """Begär review från GitHub-användare (logins) på en PR."""
    resp = requests.post(
        f"{GITHUB_API}/repos/{_repo()}/pulls/{number}/requested_reviewers",
        headers=_headers(token),
        json={"reviewers": reviewers},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return {"number": number, "requested_reviewers": reviewers}
