"""Tester för org-Project-spegling (scripts/gh_project_sync.py) med fejkad GraphQL-transport.

Verifierar projektionslogiken (resolva fält/option på namn, idempotent add, högnivå
set_initiative) utan live-anrop. Live-verifiering sker separat mot ett riktigt org-Project.
"""
from __future__ import annotations

import pytest

from scripts import gh_project_sync as gps


class FakeGraphQL:
    """Spelar upp kanned svar baserat på vilken mutation/query som körs; loggar anrop."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, query: str, variables: dict) -> dict:
        self.calls.append((query, variables))
        if "fields(first" in query:
            return {
                "node": {
                    "fields": {
                        "nodes": [
                            {"id": "FLD_status", "name": "Status"},
                            {
                                "id": "FLD_init",
                                "name": "Initiative",
                                "options": [
                                    {"id": "opt_ag", "name": "Agentur"},
                                    {"id": "opt_in", "name": "Integrations"},
                                ],
                            },
                        ]
                    }
                }
            }
        if "addProjectV2ItemById" in query:
            return {"addProjectV2ItemById": {"item": {"id": "ITEM_1"}}}
        if "updateProjectV2ItemFieldValue" in query:
            return {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": variables["itemId"]}}}
        raise AssertionError(f"oväntad query: {query[:40]}")


def test_resolve_single_select_finds_field_and_option():
    fake = FakeGraphQL()
    fid, oid = gps.resolve_single_select("PVT_x", "Initiative", "Agentur", fake)
    assert (fid, oid) == ("FLD_init", "opt_ag")


def test_resolve_raises_on_missing_option():
    fake = FakeGraphQL()
    with pytest.raises(ValueError, match="option 'Saknas'"):
        gps.resolve_single_select("PVT_x", "Initiative", "Saknas", fake)


def test_resolve_raises_on_missing_field():
    fake = FakeGraphQL()
    with pytest.raises(ValueError, match="single-select-fält 'Sprint'"):
        gps.resolve_single_select("PVT_x", "Sprint", "S1", fake)


def test_add_item_returns_item_id():
    fake = FakeGraphQL()
    assert gps.add_item("PVT_x", "I_issue", fake) == "ITEM_1"


def test_set_initiative_orchestrates_add_resolve_set():
    fake = FakeGraphQL()
    item = gps.set_initiative("PVT_x", "I_issue", "Integrations", fake)
    assert item == "ITEM_1"
    # Rätt sekvens: add → fields(resolve) → update
    kinds = [
        "add" if "addProjectV2ItemById" in q else
        "fields" if "fields(first" in q else
        "update" if "updateProjectV2ItemFieldValue" in q else "?"
        for q, _ in fake.calls
    ]
    assert kinds == ["add", "fields", "update"]
    # Update sattes med Integrations-optionen.
    _, last_vars = fake.calls[-1]
    assert last_vars["optionId"] == "opt_in"
    assert last_vars["fieldId"] == "FLD_init"


# --- Backfill (Fas 1d) ---------------------------------------------------------------
_MS_INIT = {10: "Agentur", 11: "Integrations"}  # ms 12 saknar initiativ
_ISSUES = [
    {"number": 1, "node_id": "I_1", "milestone": 10},   # → Agentur
    {"number": 2, "node_id": "I_2", "milestone": 11},   # → Integrations
    {"number": 3, "node_id": "I_3", "milestone": 12},   # ms utan initiativ → skip
    {"number": 4, "node_id": "I_4", "milestone": None},  # ingen milestone → skip
    {"number": 5, "node_id": None, "milestone": 10},     # saknar node_id → skip
]


def test_plan_backfill_only_includes_issues_with_initiative():
    plan = gps.plan_initiative_backfill(_ISSUES, _MS_INIT)
    assert plan == [
        {"number": 1, "node_id": "I_1", "initiative": "Agentur"},
        {"number": 2, "node_id": "I_2", "initiative": "Integrations"},
    ]


def test_backfill_dry_run_writes_nothing():
    fake = FakeGraphQL()
    res = gps.backfill_initiatives("PVT_x", _ISSUES, _MS_INIT, dry_run=True, graphql_fn=fake)
    assert res["dry_run"] is True
    assert len(res["actions"]) == 2
    assert fake.calls == []  # inga GraphQL-anrop i dry-run


def test_backfill_live_sets_each():
    fake = FakeGraphQL()
    res = gps.backfill_initiatives("PVT_x", _ISSUES, _MS_INIT, dry_run=False, graphql_fn=fake)
    assert res["dry_run"] is False
    assert [a["number"] for a in res["actions"]] == [1, 2]
    assert all(a.get("item_id") == "ITEM_1" for a in res["actions"])
    # Två issues × (add+fields+update) = 6 anrop
    assert len(fake.calls) == 6


# --- Full backlog-synk: field_value_for + sync() (epic #13, port av #120) -------------

def test_field_value_for_maps_label_and_milestone():
    issue = {"node_slug": "cns-mcp", "type": "chore", "quest": 13}
    vals = gps.field_value_for(issue, {13: "Integrations"})
    assert vals[gps.FIELD_SYSTEM] == "cns-mcp"
    assert vals[gps.FIELD_TYPE] == "chore"
    assert vals[gps.FIELD_INITIATIVE] == "Integrations"


def test_field_value_for_defaults_and_no_milestone():
    issue = {"node_slug": "cns-core", "type": None, "quest": None}
    vals = gps.field_value_for(issue, {})
    assert vals[gps.FIELD_TYPE] == "story"          # default
    assert vals[gps.FIELD_INITIATIVE] is None        # ingen quest → ingen initiative


class FakeSyncGraphQL:
    """Spelar upp svar för hela sync()-vägen (resolve → node-ids → items → mutationer)."""

    def __init__(self, existing=None):
        self.calls: list[tuple[str, dict]] = []
        self._existing = existing or {}  # {content_id: item_id} redan i Projektet

    def __call__(self, query: str, variables: dict | None = None) -> dict:
        variables = variables or {}
        self.calls.append((query, variables))
        if "organization" in query and "projectsV2" in query:
            return {
                "organization": {
                    "projectsV2": {
                        "nodes": [
                            {
                                "id": "PVT_backlog",
                                "title": "Backlog",
                                "fields": {
                                    "nodes": [
                                        {"id": "FLD_sys", "name": "System",
                                         "options": [{"id": "o_mcp", "name": "cns-mcp"},
                                                     {"id": "o_core", "name": "cns-core"}]},
                                        # Type-fältet saknar 'chore'-optionen med flit.
                                        {"id": "FLD_type", "name": "Type",
                                         "options": [{"id": "o_story", "name": "story"}]},
                                        {"id": "FLD_init", "name": "Initiative",
                                         "options": [{"id": "o_int", "name": "Integrations"}]},
                                    ]
                                },
                            },
                            {"id": "PVT_other", "title": "Annat", "fields": {"nodes": []}},
                        ]
                    }
                }
            }
        if "repository" in query and "issues(first" in query:
            return {"repository": {"issues": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [{"number": 1, "id": "I_1"}, {"number": 2, "id": "I_2"}],
            }}}
        if "items(first" in query:
            return {"node": {"items": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [{"id": v, "content": {"id": k}} for k, v in self._existing.items()],
            }}}
        if "addProjectV2ItemById" in query:
            return {"addProjectV2ItemById": {"item": {"id": f"ITEM_{variables['contentId']}"}}}
        if "updateProjectV2ItemFieldValue" in query:
            return {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": variables["itemId"]}}}
        raise AssertionError(f"oväntad query: {query[:60]}")


_SYNC_ISSUES = [
    {"number": 1, "node_slug": "cns-mcp", "type": "chore", "quest": 13},   # Type:chore → option saknas
    {"number": 2, "node_slug": "cns-core", "type": None, "quest": None},   # Type default story, ingen initiative
    {"number": 3, "node_slug": "x", "type": "story", "quest": 99},         # saknar node-id → hoppas över
]
_SYNC_MS = [{"number": 13, "initiative": "Integrations"}, {"number": 99, "initiative": None}]


def _patch_issue_sources(monkeypatch):
    monkeypatch.setattr(gps, "list_issues", lambda state="open": list(_SYNC_ISSUES))
    monkeypatch.setattr(gps, "list_milestones", lambda state="open": list(_SYNC_MS))


def test_sync_live_adds_and_sets_fields(monkeypatch):
    _patch_issue_sources(monkeypatch)
    fake = FakeSyncGraphQL(existing={})
    res = gps.sync(dry_run=False, graphql_fn=fake)

    assert res["issues"] == 3          # alla öppna, men #3 saknar node-id
    assert res["added"] == 2           # bara #1 och #2 läggs till
    # #1: System(ok) + Initiative(ok) = 2 (Type:chore saknar option) · #2: System + Type(story) = 2
    assert res["field_values_set"] == 4
    assert res["missing_options"] == ["Type:chore"]
    assert res["dry_run"] is False
    # Två add-mutationer kördes.
    assert sum("addProjectV2ItemById" in q for q, _ in fake.calls) == 2
    assert sum("updateProjectV2ItemFieldValue" in q for q, _ in fake.calls) == 4


def test_sync_is_idempotent_when_item_present(monkeypatch):
    _patch_issue_sources(monkeypatch)
    # Båda issuesa ligger redan i Projektet → inga add-mutationer.
    fake = FakeSyncGraphQL(existing={"I_1": "EXIST_1", "I_2": "EXIST_2"})
    res = gps.sync(dry_run=False, graphql_fn=fake)
    assert res["added"] == 0
    assert sum("addProjectV2ItemById" in q for q, _ in fake.calls) == 0
    # Fält sätts ändå (på de befintliga items).
    assert res["field_values_set"] == 4


def test_sync_dry_run_writes_nothing(monkeypatch):
    _patch_issue_sources(monkeypatch)
    fake = FakeSyncGraphQL(existing={})
    res = gps.sync(dry_run=True, graphql_fn=fake)
    assert res["dry_run"] is True
    assert res["added"] == 2
    assert res["field_values_set"] == 4
    # Inga muterande anrop i dry-run (varken add eller update).
    assert not any("addProjectV2ItemById" in q or "updateProjectV2ItemFieldValue" in q
                   for q, _ in fake.calls)


def test_sync_raises_when_project_missing(monkeypatch):
    _patch_issue_sources(monkeypatch)

    def no_backlog(query, variables=None):
        return {"organization": {"projectsV2": {"nodes": [
            {"id": "PVT_other", "title": "Annat", "fields": {"nodes": []}},
        ]}}}

    with pytest.raises(RuntimeError, match="Backlog"):
        gps.sync(dry_run=True, graphql_fn=no_backlog)
