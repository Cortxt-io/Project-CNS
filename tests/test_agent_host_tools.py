"""Tester för universum B: feta lokala verktyg + action-nivå read-first-grind."""
from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("claude_agent_sdk")

from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny  # noqa: E402

from scripts.tui import agent_host as ah  # noqa: E402


def test_local_fat_names_from_registry():
    assert len(ah.CNS_TOOL_NAMES) == 10
    assert "mcp__cns__issue" in ah.CNS_TOOL_NAMES
    # baseline = läs-kärna (katalog/issues/idéer)
    assert ah.BASELINE_CNS_TOOLS == ["mcp__cns__project", "mcp__cns__issue", "mcp__cns__idea"]


def _gate(tool_name, inp):
    return asyncio.run(ah._deny_unlisted(tool_name, inp, None))


def test_read_action_allowed_in_read_mode():
    assert isinstance(_gate("mcp__cns__issue", {"action": "list"}), PermissionResultAllow)
    assert isinstance(_gate("mcp__cns__issue", {"action": "get"}), PermissionResultAllow)


def test_write_action_denied_in_read_mode():
    assert isinstance(_gate("mcp__cns__issue", {"action": "create"}), PermissionResultDeny)
    assert isinstance(_gate("mcp__cns__pr", {"action": "create"}), PermissionResultDeny)
    # lease har inga läs-actions utom 'list' — claim ska nekas
    assert isinstance(_gate("mcp__cns__lease", {"action": "claim"}), PermissionResultDeny)
    assert isinstance(_gate("mcp__cns__lease", {"action": "list"}), PermissionResultAllow)


def test_plain_read_tools_allowed_others_denied():
    assert isinstance(_gate("Read", {}), PermissionResultAllow)
    assert isinstance(_gate("Bash", {}), PermissionResultDeny)
    assert isinstance(_gate("mcp__github__create_issue", {}), PermissionResultDeny)


# -- #137: router-medveten read-grind (externa MCP-läsverktyg) --------------

def test_external_read_shaped_classification():
    assert ah._external_is_read_shaped("mcp__github__issue_read")
    assert ah._external_is_read_shaped("mcp__github__get_file_contents")
    assert not ah._external_is_read_shaped("mcp__github__create_pull_request")
    assert not ah._external_is_read_shaped("mcp__github__issue_write")


def test_external_read_tools_extracts_only_external_reads():
    allowed = [
        "Read", "Glob",
        "mcp__cns__issue",            # cns — inte externt
        "mcp__github__issue_read",    # externt läs → tas med
        "mcp__github__create_pull_request",  # externt skriv → utelämnas
    ]
    assert ah._external_read_tools(allowed) == frozenset({"mcp__github__issue_read"})


def test_router_mounted_external_read_tool_allowed():
    gate = ah._make_read_gate(frozenset({"mcp__github__issue_read"}))
    res = asyncio.run(gate("mcp__github__issue_read", {}, None))
    assert isinstance(res, PermissionResultAllow)
    # ett externt verktyg routern INTE släppt in nekas fortfarande
    res2 = asyncio.run(gate("mcp__github__create_pull_request", {}, None))
    assert isinstance(res2, PermissionResultDeny)
