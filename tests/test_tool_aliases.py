"""Tester för connector-registreringen: feta verktyg + bakåtkompat-alias (Fas α)."""
from __future__ import annotations

import asyncio

import pytest

from scripts.tools import registry

fastmcp = pytest.importorskip("fastmcp")


def _build_server():
    from fastmcp import FastMCP
    from app.tools import (
        actions, gh_projects, ideas, issues, leases, projects, prs, quests, sessions, wiki,
    )
    from app.tools._aliases import register_aliases

    m = FastMCP("test")
    for mod in (issues, quests, ideas, projects, sessions, prs, gh_projects, actions, wiki, leases):
        mod.register(m)
    register_aliases(m)
    return m


def _tool_names(m):
    return {t.name for t in asyncio.run(m.list_tools())}


def test_fat_tools_registered():
    names = _tool_names(_build_server())
    fat = {t.cortxt_name for t in registry.FAT_TOOLS}
    assert fat <= names, f"saknade feta verktyg: {fat - names}"


def test_all_legacy_aliases_present():
    names = _tool_names(_build_server())
    legacy = set(registry.LEGACY_TOOL_DOMAINS)
    assert legacy <= names, f"saknade alias: {legacy - names}"


def test_total_count_is_fat_plus_aliases():
    names = _tool_names(_build_server())
    cortxt = {n for n in names if n.startswith("cortxt_")}
    assert len(cortxt) == 10 + 43  # 10 feta + 43 alias = 53


def test_fat_tool_has_action_param_in_schema():
    m = _build_server()
    tool = asyncio.run(m.get_tool("cortxt_issue"))
    schema = getattr(tool, "parameters", None) or {}
    props = (schema.get("properties") or {})
    assert "action" in props, f"cortxt_issue saknar action-param i schema: {list(props)}"
