"""Domänkärna: GitHub Projects v2 (GraphQL). Transport-fri.

GraphQL-logiken bor här (flyttad från app/tools/gh_projects.py) så båda universum delar
den. Kastar ValueError vid GraphQL-fel (wrappern översätter till ToolError vid behov).
Kräver CNS_GITHUB_TOKEN med 'project'-scope för skrivning.
"""
from __future__ import annotations

import os
from typing import Any

_GH_GRAPHQL = "https://api.github.com/graphql"
_TIMEOUT = 20


def _token() -> str:
    return os.getenv("CNS_GITHUB_TOKEN", "")


def _owner() -> str:
    repo = os.getenv("GITHUB_REPO", "")
    return repo.split("/")[0] if "/" in repo else repo


def _project_owner() -> str:
    """Ägare av GitHub-projektet — CNS_PROJECT_OWNER (org), fallback repo-ägaren.

    Projektet kan vara org-ägt (Cortxt-io) medan repot ligger på ett user-konto.
    """
    return os.getenv("CNS_PROJECT_OWNER", "").strip() or _owner()


def _graphql(query: str, variables: dict | None = None) -> dict:
    import requests

    resp = requests.post(
        _GH_GRAPHQL,
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise ValueError(str(data["errors"]))
    return data["data"]


def _graphql_safe(query: str, variables: dict | None = None) -> dict | None:
    """Som _graphql men returnerar None i stället för att resa vid GraphQL-fel.

    Används för org→user-sonderingen: en ``organization(login:)``-fråga mot ett
    user-konto reser ett GraphQL-fel (``ValueError``) — det ska falla igenom till
    user-frågan, inte krascha verktyget. Nätverksfel (requests) propageras alltjämt.
    """
    try:
        return _graphql(query, variables)
    except ValueError:
        return None


def gh_project(action: str, **kw: Any) -> Any:
    if action == "list":
        login = _project_owner()
        # Org-konto först (robust: _graphql_safe reser inte om login är ett user-konto,
        # då faller vi igenom till user-frågan i stället för att krascha verktyget).
        data = _graphql_safe(
            """
            query($login: String!) {
              organization(login: $login) {
                projectsV2(first: 20) { nodes { id number title url closed } }
              }
            }
            """,
            {"login": login},
        )
        org = (data or {}).get("organization") or {}
        projects = org.get("projectsV2", {}).get("nodes", [])
        if not projects:
            data2 = _graphql_safe(
                """
                query($login: String!) {
                  user(login: $login) {
                    projectsV2(first: 20) { nodes { id number title url closed } }
                  }
                }
                """,
                {"login": login},
            )
            projects = ((data2 or {}).get("user") or {}).get("projectsV2", {}).get("nodes", [])
        return [p for p in projects if not p.get("closed")]

    if action == "list_items":
        data = _graphql(
            """
            query($id: ID!, $first: Int!) {
              node(id: $id) {
                ... on ProjectV2 {
                  items(first: $first) {
                    nodes {
                      id
                      fieldValues(first: 10) {
                        nodes {
                          ... on ProjectV2ItemFieldSingleSelectValue {
                            name field { ... on ProjectV2SingleSelectField { name } }
                          }
                          ... on ProjectV2ItemFieldTextValue {
                            text field { ... on ProjectV2Field { name } }
                          }
                        }
                      }
                      content {
                        ... on Issue { number title state url }
                        ... on PullRequest { number title state url }
                        ... on DraftIssue { title body }
                      }
                    }
                  }
                }
              }
            }
            """,
            {"id": kw["project_id"], "first": kw.get("first", 30)},
        )
        items = data.get("node", {}).get("items", {}).get("nodes", [])
        result = []
        for item in items:
            content = item.get("content") or {}
            fields = {
                fv.get("field", {}).get("name"): fv.get("name") or fv.get("text")
                for fv in item.get("fieldValues", {}).get("nodes", [])
                if fv and fv.get("field")
            }
            result.append({"id": item["id"], "content": content, "fields": fields})
        return result

    if action == "move_item":
        data = _graphql(
            """
            mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
              updateProjectV2ItemFieldValue(input: {
                projectId: $projectId itemId: $itemId fieldId: $fieldId
                value: { singleSelectOptionId: $optionId }
              }) { projectV2Item { id } }
            }
            """,
            {
                "projectId": kw["project_id"],
                "itemId": kw["item_id"],
                "fieldId": kw["field_id"],
                "optionId": kw["option_id"],
            },
        )
        return {"updated": data.get("updateProjectV2ItemFieldValue", {}).get("projectV2Item", {})}

    raise ValueError(f"okänd gh_project-action: {action}")
