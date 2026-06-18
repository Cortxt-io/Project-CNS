"""Domänkärna: efemära issue-claims (Redis, fail-open). Transport-fri.

``owner`` injiceras av wrappern (universum A: GitHub-login ur OAuth-token; universum B:
agent-id eller 'local') — kärnan tar emot det som kwarg, härleder det aldrig själv.
"""
from __future__ import annotations

from typing import Any


def lease(action: str, **kw: Any) -> Any:
    owner = kw.get("owner", "local")

    if action == "claim":
        from scripts.lease_store import claim

        return claim(kw["number"], owner)

    if action == "release":
        from scripts.lease_store import release

        return release(kw["number"], owner)

    if action == "heartbeat":
        from scripts.lease_store import heartbeat

        return heartbeat(kw["number"], owner)

    if action == "list":
        from scripts.lease_store import list_leases

        return list_leases()

    raise ValueError(f"okänd lease-action: {action}")
