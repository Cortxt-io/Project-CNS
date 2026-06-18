"""Linear MCP tools — list/create issues and link them to CNS nodes.

Auth: LINEAR_API_KEY env var. Uses the Linear GraphQL API.
Railway: add LINEAR_API_KEY to the service's environment variables.
"""

from __future__ import annotations

import os
import requests
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

_LINEAR_API = "https://api.linear.app/graphql"
_TIMEOUT = 20


def _headers() -> dict:
    token = os.getenv("LINEAR_API_KEY", "")
    if not token:
        raise ToolError("LINEAR_API_KEY is not set — add it to Railway environment variables.")
    return {"Authorization": token, "Content-Type": "application/json"}


def _gql(query: str, variables: dict | None = None) -> dict:
    resp = requests.post(
        _LINEAR_API,
        headers=_headers(),
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
    def cortxt_list_linear_issues(
        team: str | None = None, state: str | None = None, limit: int = 20
    ) -> list[dict]:
        """List Linear issues, optionally filtered by team key and/or state name.

        team: Linear team key (e.g. 'ENG'). Omit to list across all teams.
        state: state name filter (e.g. 'In Progress', 'Todo'). Case-insensitive prefix match.
        """
        filter_parts = []
        if team:
            filter_parts.append(f'team: {{ key: {{ eq: "{team}" }} }}')
        if state:
            filter_parts.append(f'state: {{ name: {{ containsIgnoreCase: "{state}" }} }}')
        filter_clause = f"filter: {{ {', '.join(filter_parts)} }}" if filter_parts else ""

        data = _gql(
            f"""
            query($limit: Int!) {{
              issues({filter_clause} first: $limit orderBy: updatedAt) {{
                nodes {{
                  id identifier title priority
                  state {{ name color }}
                  team {{ key name }}
                  assignee {{ name }}
                  url
                  updatedAt
                }}
              }}
            }}
            """,
            {"limit": limit},
        )
        return data.get("issues", {}).get("nodes", [])

    @mcp.tool()
    def cortxt_create_linear_issue(
        title: str,
        description: str = "",
        team: str = "",
    ) -> dict:
        """Create a Linear issue.

        team: Linear team key (e.g. 'ENG'). Required — Linear issues always belong to a team.
        """
        if not team:
            raise ToolError("team is required — provide the Linear team key (e.g. 'ENG').")

        team_data = _gql(
            """
            query($key: String!) {
              teams(filter: { key: { eq: $key } }) {
                nodes { id key name }
              }
            }
            """,
            {"key": team},
        )
        nodes = team_data.get("teams", {}).get("nodes", [])
        if not nodes:
            raise ToolError(f"Linear team '{team}' not found.")
        team_id = nodes[0]["id"]

        data = _gql(
            """
            mutation($title: String!, $description: String, $teamId: String!) {
              issueCreate(input: { title: $title, description: $description, teamId: $teamId }) {
                success
                issue { id identifier title url }
              }
            }
            """,
            {"title": title, "description": description, "teamId": team_id},
        )
        result = data.get("issueCreate", {})
        if not result.get("success"):
            raise ToolError("Linear issue creation failed.")
        return result.get("issue", {})

    @mcp.tool()
    def cortxt_link_linear_to_cns(linear_id: str, cns_slug: str) -> dict:
        """Attach a CNS node slug to a Linear issue as an external link.

        linear_id: the Linear issue identifier (e.g. 'ENG-42').
        cns_slug: the CNS node slug to link (e.g. 'cns-mcp').

        This writes a link attachment on the Linear issue pointing to the CNS node
        so context is surfaced in Linear without duplicating data.
        """
        issue_data = _gql(
            """
            query($id: String!) {
              issue(id: $id) { id title }
            }
            """,
            {"id": linear_id},
        )
        issue = issue_data.get("issue")
        if not issue:
            raise ToolError(f"Linear issue '{linear_id}' not found.")

        data = _gql(
            """
            mutation($issueId: String!, $url: String!, $title: String!) {
              attachmentCreate(input: { issueId: $issueId, url: $url, title: $title }) {
                success
                attachment { id url title }
              }
            }
            """,
            {
                "issueId": issue["id"],
                "url": f"https://github.com/{os.getenv('GITHUB_REPO', '')}/tree/main/nodes/{cns_slug}",
                "title": f"CNS node: {cns_slug}",
            },
        )
        result = data.get("attachmentCreate", {})
        if not result.get("success"):
            raise ToolError("Failed to create Linear attachment.")
        return {"linear_issue": linear_id, "cns_slug": cns_slug, **result.get("attachment", {})}
