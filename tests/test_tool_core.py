"""Tester för den delade verktygstaxonomin + domänkärnorna (scripts/tools)."""
from __future__ import annotations

import pytest

from scripts.tools import registry


def test_taxonomy_shape():
    assert len(registry.FAT_TOOLS) == 10
    assert sum(len(t.actions) for t in registry.FAT_TOOLS) == 44
    # namnkonvention
    issue = registry.by_domain("issue")
    assert issue.cortxt_name == "cortxt_issue"
    assert issue.local_name == "mcp__cns__issue"
    assert issue.read_actions() == ("list", "get")


def test_idea_update_action(tmp_path, monkeypatch):
    from scripts import idea_inbox as ib
    monkeypatch.setattr(ib, "IDEAS_DIR", tmp_path)
    created = registry.dispatch("idea", "capture", text="rå tanke", slug="cns-core")
    iid = created["id"]
    upd = registry.dispatch("idea", "update", idea_id=iid, append="tillägg")
    assert "rå tanke" in upd["text"] and "tillägg" in upd["text"] and "updated_at" in upd
    ovr = registry.dispatch("idea", "update", idea_id=iid, text="ny", slug="agentur")
    assert ovr["text"] == "ny" and ovr["slug"] == "agentur"
    with pytest.raises(ValueError):
        registry.dispatch("idea", "update")  # saknar required idea_id


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


def test_session_list_does_not_force_status(monkeypatch):
    """Regression: action='list' får INTE tvinga status='done' (skulle dölja andra pass)."""
    seen = {}
    monkeypatch.setattr("scripts.session_store.list_sessions",
                        lambda status=None, link_ref=None: seen.update(status=status) or [])
    registry.dispatch("session", "list", status=None, link_ref=None)
    assert seen["status"] is None  # list filtrerar inte när status osatt


def test_session_save_defaults_status_to_done(monkeypatch):
    """save med status=None (wrapper-default) ska bli 'done', inte None."""
    seen = {}
    monkeypatch.setattr("scripts.session_store.save_session",
                        lambda **kw: seen.update(kw) or {"id": "s1"})
    registry.dispatch("session", "save", summary="x", status=None)
    assert seen["status"] == "done"


def test_legacy_map_covers_all_43_old_names():
    assert len(registry.LEGACY_TOOL_DOMAINS) == 43
    assert set(registry.LEGACY_TOOL_DOMAINS.values()) == {t.domain for t in registry.FAT_TOOLS}
