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
