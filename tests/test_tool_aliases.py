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


# Förväntade params per gammalt verktyg = de ORIGINALA signaturerna (innan konsolideringen).
# Detta är connector-kontraktets vakt: ett alias måste exponera EXAKT den gamla signaturen,
# annars bryts claude.ai-anrop vid Fas α. Drift fångas här, inte i produktion.
_EXPECTED_ALIAS_PARAMS = {
    "cortxt_list_open_issues": {"node_slug"},
    "cortxt_get_issue": {"number"},
    "cortxt_create_issue": {"node_slug", "title", "body", "quest_number", "issue_type", "depends_on"},
    "cortxt_close_issue": {"number", "result_summary"},
    "cortxt_move_issue_to_quest": {"number", "quest_number"},
    "cortxt_add_todo": {"number", "text"},
    "cortxt_check_todo": {"number", "index", "done"},
    "cortxt_set_issue_type": {"number", "issue_type"},
    "cortxt_set_depends_on": {"number", "depends_on"},
    "cortxt_add_acceptance": {"number", "given", "when", "then"},
    "cortxt_list_quests": set(),
    "cortxt_get_quest": {"number"},
    "cortxt_create_quest": {"title", "description", "initiative"},
    "cortxt_close_quest": {"number"},
    "cortxt_capture_idea": {"text", "source", "slug", "session_id"},
    "cortxt_list_ideas": {"status", "slug", "session_id"},
    "cortxt_promote_idea_to_issue": {"idea_id", "title", "slug", "body", "quest_number"},
    "cortxt_resolve_idea": {"idea_id", "resolution", "reason"},
    "cortxt_start_session": {"link_kind", "link_ref", "summary", "source", "transcript_id"},
    "cortxt_mark_session_done": {"session_id", "summary"},
    "cortxt_save_session": {"summary", "link_kind", "link_ref", "status", "source", "transcript_id"},
    "cortxt_list_sessions": {"status", "link_ref"},
    "cortxt_fork_session": {"parent_id", "summary", "fork_name", "link_kind", "link_ref", "source", "transcript_id"},
    "cortxt_get_session_tree": {"root_id"},
    "cortxt_list_prs": {"state"},
    "cortxt_get_pr": {"number"},
    "cortxt_create_pr": {"title", "head", "base", "body", "draft"},
    "cortxt_set_pr_reviewers": {"number", "reviewers"},
    "cortxt_list_projects": set(),
    "cortxt_get_project": {"slug"},
    "cortxt_list_gh_projects": set(),
    "cortxt_list_gh_project_items": {"project_id", "first"},
    "cortxt_move_gh_project_item": {"project_id", "item_id", "field_id", "option_id"},
    "cortxt_list_workflow_runs": {"workflow_id", "limit"},
    "cortxt_trigger_workflow": {"workflow_id", "ref", "inputs"},
    "cortxt_get_workflow_run": {"run_id"},
    "cortxt_list_wiki_pages": set(),
    "cortxt_read_wiki_page": {"page"},
    "cortxt_write_wiki_page": {"page", "content", "message"},
    "cortxt_claim_issue": {"number"},
    "cortxt_release_issue": {"number"},
    "cortxt_heartbeat_issue": {"number"},
    "cortxt_list_leases": set(),
}


def test_aliases_preserve_original_signatures():
    """Connector-kontrakt: varje alias exponerar EXAKT den gamla signaturen (inget 'action')."""
    m = _build_server()
    assert set(_EXPECTED_ALIAS_PARAMS) == set(registry.LEGACY_TOOL_DOMAINS), "expected-tabellen täcker inte alla 43"
    for name, expected in _EXPECTED_ALIAS_PARAMS.items():
        tool = asyncio.run(m.get_tool(name))
        props = set((getattr(tool, "parameters", None) or {}).get("properties") or {})
        assert "action" not in props, f"{name}: läckte fett 'action'-param (fel signatur)"
        assert props == expected, f"{name}: signatur-drift — fick {sorted(props)}, väntade {sorted(expected)}"
