"""Lease tools: ephemeral claims over GitHub Issues for multi-agent coordination.

When many agent-runs share the repo, a lease lets one run say "I've got issue
#N" so others don't double-work it. The issue stays the source of truth on
GitHub; the claim lives only in Redis (TTL'd, fail-open). See
``scripts/lease_store.py`` and ``plans/lease-layer-spec.md``.

The owner is the authenticated GitHub login (from the OAuth token) — the agent
never supplies it, so a run can only release/heartbeat its own claims.
"""

from __future__ import annotations

from fastmcp import FastMCP


def _owner() -> str:
    """The current caller's GitHub login from the OAuth token.

    Falls back to ``local`` in unauthenticated dev mode (no OAuth configured).
    """
    try:
        from fastmcp.server.dependencies import get_access_token
        token = get_access_token()
        login = token.claims.get("login") if token and token.claims else None
        return login or "local"
    except Exception:
        return "local"


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_claim_issue(number: int) -> dict:
        """Atomically claim an issue so no other agent-run works it concurrently.

        Returns `{claimed: true, ...}` if you got it, or `{claimed: false, owner}`
        if someone already holds it. The claim is yours (your GitHub login) and
        auto-expires after ~5 min unless you heartbeat it. Fail-open: if Redis is
        down it returns `claimed: false` with a reason and agents coordinate as before.
        """
        from scripts.lease_store import claim
        return claim(number, _owner())

    @mcp.tool()
    def cortxt_release_issue(number: int) -> dict:
        """Release your claim on an issue (only succeeds if you hold it)."""
        from scripts.lease_store import release
        return release(number, _owner())

    @mcp.tool()
    def cortxt_heartbeat_issue(number: int) -> dict:
        """Renew your claim's TTL on a long-running issue (only if you hold it)."""
        from scripts.lease_store import heartbeat
        return heartbeat(number, _owner())

    @mcp.tool()
    def cortxt_list_leases() -> list[dict]:
        """List all currently held issue claims (who owns what right now)."""
        from scripts.lease_store import list_leases
        return list_leases()
