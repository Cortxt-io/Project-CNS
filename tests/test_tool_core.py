"""Tester för den delade verktygstaxonomin + domänkärnorna (scripts/tools)."""
from __future__ import annotations

import pytest

from scripts.tools import registry


def test_taxonomy_shape():
    assert len(registry.FAT_TOOLS) == 10
    assert sum(len(t.actions) for t in registry.FAT_TOOLS) == 43
    # namnkonvention
    issue = registry.by_domain("issue")
    assert issue.cortxt_name == "cortxt_issue"
    assert issue.local_name == "mcp__cns__issue"
    assert issue.read_actions() == ("list", "get")


def test_all_handlers_resolve_and_reject_unknown_action():
    for t in registry.FAT_TOOLS:
        handler = registry.get_handler(t.domain)
        assert callable(handler)
        with pytest.raises(ValueError):
            handler("___unknown___")


def test_dispatch_validates_action_and_required():
    with pytest.raises(ValueError):
        registry.dispatch("issue", "frobnicate")
    with pytest.raises(ValueError) as ei:
        registry.dispatch("issue", "get")  # saknar required 'number'
    assert "number" in str(ei.value)


def test_dispatch_routes_to_core(monkeypatch):
    captured = {}

    def fake_list_issues(node_slug=None, state="open"):
        captured["node_slug"] = node_slug
        captured["state"] = state
        return [{"number": 1}]

    monkeypatch.setattr("scripts.issues_client.list_issues", fake_list_issues)
    out = registry.dispatch("issue", "list", node_slug="cns-core")
    assert out == [{"number": 1}]
    assert captured == {"node_slug": "cns-core", "state": "open"}


def test_legacy_and_family_resolution():
    # family
    assert registry.domain_for_token("issues") == "issue"
    # fett connector-namn + lokalt namn
    assert registry.domain_for_token("cortxt_issue") == "issue"
    assert registry.domain_for_token("mcp__cns__issue") == "issue"
    # gammalt granulärt namn — OBS lease-namnen pekar på lease, inte issue
    assert registry.domain_for_token("cortxt_create_issue") == "issue"
    assert registry.domain_for_token("cortxt_claim_issue") == "lease"
    assert registry.domain_for_token("okänt") is None


def test_local_names_for_dedupes_and_maps():
    names = registry.local_names_for(["issues", "cortxt_create_issue", "prs", "wiki", "okänt"])
    # issues + cortxt_create_issue → samma domän (en post), plus pr + wiki
    assert names == ["mcp__cns__issue", "mcp__cns__pr", "mcp__cns__wiki"]


def test_legacy_map_covers_all_43_old_names():
    assert len(registry.LEGACY_TOOL_DOMAINS) == 43
    assert set(registry.LEGACY_TOOL_DOMAINS.values()) == {t.domain for t in registry.FAT_TOOLS}
