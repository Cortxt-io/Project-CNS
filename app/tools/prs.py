"""Pull Request-verktyg (MCP) — tunna wrappers över ``scripts.prs_client``.

Logiken bor i ``scripts/prs_client.py`` (plain REST) så även dispatch-loopen (#59) kan
återanvända den. Dessa MCP-verktyg är connector-kontrakt mot claude.ai — namnen
(``cortxt_*``) hålls oförändrade.
"""

from __future__ import annotations

from fastmcp import FastMCP

from scripts import prs_client


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_list_prs(state: str = "open") -> list[dict]:
        """List pull requests for the CNS repo.

        state: 'open' | 'closed' | 'all'
        """
        return prs_client.list_prs(state=state)

    @mcp.tool()
    def cortxt_get_pr(number: int) -> dict:
        """Get details for a pull request including review status and checks."""
        return prs_client.get_pr(number)

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
        return prs_client.create_pr(title, head, base=base, body=body, draft=draft)

    @mcp.tool()
    def cortxt_set_pr_reviewers(number: int, reviewers: list[str]) -> dict:
        """Request reviews from GitHub users on a PR.

        reviewers: list of GitHub login strings.
        """
        return prs_client.set_reviewers(number, reviewers)
