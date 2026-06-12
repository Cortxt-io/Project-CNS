"""Tester för kapabilitet som routningssignal (scripts/capabilities.py, Del B)."""
from __future__ import annotations

from scripts import capabilities as cap


def test_derive_capabilities_from_mcp_tools():
    caps = cap.derive_capabilities([
        "mcp__github__create_pull_request", "mcp__cns__list_nodes", "mcp__web__fetch",
    ])
    assert set(caps) == {"github", "cns", "web"}


def test_derive_capabilities_cortxt_and_code_and_read():
    caps = cap.derive_capabilities(["cortxt_create_pr", "Write", "Edit", "Read", "Glob"])
    assert set(caps) == {"cns", "code", "read"}


def test_derive_capabilities_skills_prefixed():
    caps = cap.derive_capabilities([], skills=["pr-protokoll", "session-bokfor"])
    assert caps == ["skill:pr-protokoll", "skill:session-bokfor"]


def test_derive_capabilities_empty_and_dirty():
    assert cap.derive_capabilities(None) == []
    assert cap.derive_capabilities(["", "  ", "mcp__"]) == []   # ofullständiga ignoreras


def test_required_from_node_type():
    assert "code" in cap.required_capabilities("mcp-server")
    assert cap.required_capabilities("agent") == []             # okänd typ → inget krav


def test_required_with_needs_override_and_integrations():
    req = cap.required_capabilities(
        "service",
        integrations={"deploy": {"vercel": {}}},
        needs=["github"],
    )
    assert set(req) >= {"code", "vercel", "github"}


def test_capability_score_counts_covered():
    assert cap.capability_score(["github", "code"], ["github", "vercel"]) == 1
    assert cap.capability_score(["github"], []) == 0
    assert cap.capability_score(None, ["github"]) == 0
