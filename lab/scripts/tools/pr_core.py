"""Domänkärna: Pull Requests. Transport-fri — wrappar ``scripts.prs_client``."""
from __future__ import annotations

from typing import Any


def pr(action: str, **kw: Any) -> Any:
    from scripts import prs_client

    if action == "list":
        return prs_client.list_prs(state=kw.get("state", "open"))

    if action == "get":
        return prs_client.get_pr(kw["number"])

    if action == "create":
        return prs_client.create_pr(
            kw["title"],
            kw["head"],
            base=kw.get("base", "main"),
            body=kw.get("body", ""),
            draft=kw.get("draft", False),
        )

    if action == "set_reviewers":
        return prs_client.set_reviewers(kw["number"], kw["reviewers"])

    raise ValueError(f"okänd pr-action: {action}")
