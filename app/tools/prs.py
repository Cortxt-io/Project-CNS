"""Pull Request tools — list, create, and inspect GitHub PRs for the CNS repo."""

from __future__ import annotations

import os
import requests
from fastmcp import FastMCP

_GH_API = "https://api.github.com"
_TIMEOUT = 20


def _repo() -> str:
    return os.getenv("GITHUB_REPO", "")


def _token() -> str:
    return os.getenv("CNS_GITHUB_TOKEN", "")


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token()}", "Accept": "application/vnd.github+json"}


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_list_prs(state: str = "open") -> list[dict]:
        """List pull requests for the CNS repo.

        state: 'open' | 'closed' | 'all'
        """
        resp = requests.get(
            f"{_GH_API}/repos/{_repo()}/pulls",
            headers=_headers(),
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

    @mcp.tool()
    def cortxt_get_pr(number: int) -> dict:
        """Get details for a pull request including review status and checks."""
        resp = requests.get(
            f"{_GH_API}/repos/{_repo()}/pulls/{number}",
            headers=_headers(),
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

    @mcp.tool()
    def cortxt_create_pr(
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
        draft: bool = False,
    ) -> dict:
        """Create a pull request.

        head: the branch to merge from (e.g. 'feat/my-branch').
        base: the branch to merge into (default: 'main').
        """
        resp = requests.post(
            f"{_GH_API}/repos/{_repo()}/pulls",
            headers=_headers(),
            json={"title": title, "head": head, "base": base, "body": body, "draft": draft},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        pr = resp.json()
        return {"number": pr["number"], "url": pr["html_url"], "state": pr["state"]}

    @mcp.tool()
    def cortxt_set_pr_reviewers(number: int, reviewers: list[str]) -> dict:
        """Request reviews from GitHub users on a PR.

        reviewers: list of GitHub login strings.
        """
        resp = requests.post(
            f"{_GH_API}/repos/{_repo()}/pulls/{number}/requested_reviewers",
            headers=_headers(),
            json={"reviewers": reviewers},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return {"number": number, "requested_reviewers": reviewers}
