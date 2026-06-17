"""Domänkärna: issues (arbetsuppgifter = GitHub Issues).

Transport-fri: wrappar ``scripts.issues_client`` (REST mot CNS_GITHUB_TOKEN), kastar
``ValueError`` vid fel. Ingen FastMCP/SDK/push — connector-wrappern (universum A) och
SDK-wrappern (universum B) anropar denna via ``registry.dispatch('issue', action, ...)``.
"""
from __future__ import annotations

from typing import Any


def issue(action: str, **kw: Any) -> Any:
    """Dispatcha en issue-action mot datalagret. Se ``registry.FAT_TOOLS`` för actions."""
    if action == "list":
        from scripts.issues_client import list_issues

        return list_issues(node_slug=kw.get("node_slug"), state="open")

    if action == "get":
        from scripts.issues_client import get_issue
        from scripts.md_parser import read_node

        number = kw["number"]
        issue_obj = get_issue(number)
        if not issue_obj:
            return {"error": f"Issue #{number} not found"}
        slug = issue_obj.get("node_slug")
        if slug:
            try:
                meta, _sections, _ = read_node(slug)
                issue_obj["node_context"] = {
                    "meta": meta,
                    "summary": meta.get("summary", ""),
                    "kind": meta.get("kind", ""),
                    "stage": meta.get("stage", ""),
                }
            except Exception:
                pass
        return issue_obj

    if action == "create":
        from scripts.issues_client import create_issue

        return create_issue(
            node_slug=kw["node_slug"],
            title=kw["title"],
            body=kw.get("body", ""),
            milestone=kw.get("quest_number"),
            issue_type=kw.get("issue_type", "story"),
            depends_on=kw.get("depends_on"),
        )

    if action == "close":
        from scripts.issues_client import close_issue

        return close_issue(kw["number"], comment=kw["result_summary"])

    if action == "move_to_quest":
        from scripts.issues_client import set_milestone

        return set_milestone(kw["number"], kw.get("quest_number"))

    if action == "add_todo":
        from scripts.issues_client import add_todo

        return add_todo(kw["number"], kw["text"])

    if action == "check_todo":
        from scripts.issues_client import set_todo

        return set_todo(kw["number"], kw["index"], done=kw.get("done", True))

    if action == "set_type":
        from scripts.issues_client import set_issue_type

        return set_issue_type(kw["number"], kw["issue_type"])

    if action == "set_depends_on":
        from scripts.issues_client import set_depends_on

        return set_depends_on(kw["number"], kw["depends_on"])

    if action == "add_acceptance":
        from scripts.issues_client import add_acceptance_criterion

        return add_acceptance_criterion(kw["number"], kw["given"], kw["when"], kw["then"])

    raise ValueError(f"okänd issue-action: {action}")
