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
