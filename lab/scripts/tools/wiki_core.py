"""Domänkärna: GitHub Wiki (separat git-repo {repo}.wiki via Contents API). Transport-fri."""
from __future__ import annotations

import base64
import os
from typing import Any

_GH_API = "https://api.github.com"
_TIMEOUT = 20


def _repo() -> str:
    return os.getenv("GITHUB_REPO", "")


def _wiki_repo() -> str:
    return f"{_repo()}.wiki"


def _headers() -> dict:
    token = os.getenv("CNS_GITHUB_TOKEN", "")
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def wiki(action: str, **kw: Any) -> Any:
    import requests

    if action == "list":
        resp = requests.get(
            f"{_GH_API}/repos/{_wiki_repo()}/contents/", headers=_headers(), timeout=_TIMEOUT
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return [
            {"name": f["name"], "path": f["path"], "sha": f["sha"]}
            for f in resp.json()
            if f["type"] == "file" and f["name"].endswith(".md")
        ]

    if action == "read":
        page = kw["page"]
        path = f"{page}.md" if not page.endswith(".md") else page
        resp = requests.get(
            f"{_GH_API}/repos/{_wiki_repo()}/contents/{path}", headers=_headers(), timeout=_TIMEOUT
        )
        if resp.status_code == 404:
            return {"error": f"Wiki page '{page}' not found"}
        resp.raise_for_status()
        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return {"page": page, "content": content, "sha": data["sha"]}

    if action == "write":
        page = kw["page"]
        content = kw["content"]
        path = f"{page}.md" if not page.endswith(".md") else page
        commit_message = kw.get("message") or f"Update {page}"
        existing = requests.get(
            f"{_GH_API}/repos/{_wiki_repo()}/contents/{path}", headers=_headers(), timeout=_TIMEOUT
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
            raise ValueError(
                f"Wiki repo not found or not enabled for {_repo()}. "
                "Enable the wiki in GitHub repo settings first."
            )
        resp.raise_for_status()
        return {"page": page, "action": "updated" if "sha" in payload else "created"}

    raise ValueError(f"okänd wiki-action: {action}")
