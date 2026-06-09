"""GitHub Projects v2 tools — list items and move cards via GraphQL.

Uses the GitHub GraphQL API (Projects v2 does not have REST endpoints).
Requires CNS_GITHUB_TOKEN with 'project' scope for writes.
"""

from __future__ import annotations

import os
import requests
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

_GH_GRAPHQL = "https://api.github.com/graphql"
_TIMEOUT = 20


def _token() -> str:
    return os.getenv("CNS_GITHUB_TOKEN", "")


def _owner() -> str:
    repo = os.getenv("GITHUB_REPO", "")
    return repo.split("/")[0] if "/" in repo else repo


def _graphql(query: str, variables: dict | None = None) -> dict:
    resp = requests.post(
        _GH_GRAPHQL,
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise ToolError(str(data["errors"]))
    return data["data"]


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_list_gh_projects() -> list[dict]:
        """List GitHub Projects v2 for the repo owner."""
        data = _graphql(
            """
            query($login: String!) {
              organization(login: $login) {
                projectsV2(first: 20) {
                  nodes { id number title url closed }
                }
              }
            }
            """,
            {"login": _owner()},
        )
        org = data.get("organization") or {}
        projects = org.get("projectsV2", {}).get("nodes", [])
        if not projects:
            data2 = _graphql(
                """
                query($login: String!) {
                  user(login: $login) {
                    projectsV2(first: 20) {
                      nodes { id number title url closed }
                    }
                  }
                }
                """,
                {"login": _owner()},
            )
            projects = (data2.get("user") or {}).get("projectsV2", {}).get("nodes", [])
        return [p for p in projects if not p.get("closed")]

    @mcp.tool()
    def cortxt_list_gh_project_items(project_id: str, first: int = 30) -> list[dict]:
        """List items in a GitHub Projects v2 board.

        project_id: the node ID returned by cortxt_list_gh_projects.
        """
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
                            name
                            field { ... on ProjectV2SingleSelectField { name } }
                          }
                          ... on ProjectV2ItemFieldTextValue {
                            text
                            field { ... on ProjectV2Field { name } }
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
            {"id": project_id, "first": first},
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

    @mcp.tool()
    def cortxt_move_gh_project_item(
        project_id: str, item_id: str, field_id: str, option_id: str
    ) -> dict:
        """Move a project item to a new column/status by setting a single-select field.

        Get field_id and option_id from the project's field configuration.
        """
        data = _graphql(
            """
            mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
              updateProjectV2ItemFieldValue(input: {
                projectId: $projectId
                itemId: $itemId
                fieldId: $fieldId
                value: { singleSelectOptionId: $optionId }
              }) {
                projectV2Item { id }
              }
            }
            """,
            {
                "projectId": project_id,
                "itemId": item_id,
                "fieldId": field_id,
                "optionId": option_id,
            },
        )
        return {"updated": data.get("updateProjectV2ItemFieldValue", {}).get("projectV2Item", {})}
