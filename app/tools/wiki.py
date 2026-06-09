"""GitHub Wiki tools — read and write wiki pages via the wiki's git repo.

GitHub Wiki is a separate git repo at ``{repo}.wiki``. The Contents API works
against it using the same CNS_GITHUB_TOKEN (needs 'contents' write scope).
"""

from __future__ import annotations

import base64
import os
import requests
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

_GH_API = "https://api.github.com"
_TIMEOUT = 20


def _repo() -> str:
    return os.getenv("GITHUB_REPO", "")


def _wiki_repo() -> str:
    return f"{_repo()}.wiki"


def _headers() -> dict:
    token = os.getenv("CNS_GITHUB_TOKEN", "")
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_list_wiki_pages() -> list[dict]:
        """List all pages in the GitHub wiki (root level)."""
        resp = requests.get(
            f"{_GH_API}/repos/{_wiki_repo()}/contents/",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return [
            {"name": f["name"], "path": f["path"], "sha": f["sha"]}
            for f in resp.json()
            if f["type"] == "file" and f["name"].endswith(".md")
        ]

    @mcp.tool()
    def cortxt_read_wiki_page(page: str) -> dict:
        """Read a wiki page by name (without .md extension, e.g. 'Home' or 'Architecture').

        Returns the raw markdown content.
        """
        path = f"{page}.md" if not page.endswith(".md") else page
        resp = requests.get(
            f"{_GH_API}/repos/{_wiki_repo()}/contents/{path}",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        if resp.status_code == 404:
            return {"error": f"Wiki page '{page}' not found"}
        resp.raise_for_status()
        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return {"page": page, "content": content, "sha": data["sha"]}

    @mcp.tool()
    def cortxt_write_wiki_page(page: str, content: str, message: str = "") -> dict:
        """Create or update a wiki page.

        page: page name without .md extension (e.g. 'Architecture').
        content: full markdown content for the page.
        message: optional commit message (defaults to 'Update <page>').
        """
        path = f"{page}.md" if not page.endswith(".md") else page
        commit_message = message or f"Update {page}"

        # Check if page exists to get current sha (needed for updates).
        existing = requests.get(
            f"{_GH_API}/repos/{_wiki_repo()}/contents/{path}",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        payload: dict = {
            "message": commit_message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        }
        if existing.status_code == 200:
            payload["sha"] = existing.json()["sha"]
        elif existing.status_code != 404:
            existing.raise_for_status()

        resp = requests.put(
            f"{_GH_API}/repos/{_wiki_repo()}/contents/{path}",
            headers=_headers(),
            json=payload,
            timeout=_TIMEOUT,
        )
        if resp.status_code == 404:
            raise ToolError(
                f"Wiki repo not found or not enabled for {_repo()}. "
                "Enable the wiki in GitHub repo settings first."
            )
        resp.raise_for_status()
        action = "updated" if "sha" in payload else "created"
        return {"page": page, "action": action}
