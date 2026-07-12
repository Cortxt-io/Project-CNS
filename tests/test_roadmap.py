"""Verifiering av roadmap-läsaren (scripts/roadmap.py) mot de committade roadmaps/-filerna.

Rena läsare, ingen GitHub/nät. Speglar test_health.py-stilen.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import roadmap  # noqa: E402


def test_recipe_phases() -> None:
    phases = roadmap.load_recipe()["phases"]
    keys = [p["key"] for p in phases]
    assert keys == ["discovery", "spec", "mvp", "konsolidera", "live", "users", "validated", "paying"]


def test_summary_crusade() -> None:
    """Fasen HÄRLEDS numera — testa kontraktet, inte ett hårdkodat värde.

    Den gamla versionen låste `current_phase == "spec"`, vilket bara var det handskrivna
    fältet i filen. Det var fel i verkligheten (crusade har ett repo → mvp), och ett test
    som låser fast ett osant fält skyddar bara lögnen.
    """
    s = roadmap.roadmap_summary("crusade")
    assert s is not None

    keys = [p["key"] for p in roadmap.load_recipe()["phases"]]
    assert s["current_phase"] in keys                       # en giltig receptfas
    assert s["phase_index"] == keys.index(s["current_phase"]) + 1
    assert s["total_phases"] == 8
    assert s["open_decisions"] >= 1 and s["next_decision"]
    assert isinstance(s["gates_skipped"], list)             # skulden följer med


def test_missing_roadmap_is_none() -> None:
    assert roadmap.load_roadmap("does-not-exist") is None
    assert roadmap.roadmap_summary("does-not-exist") is None


def test_detail_merges_recipe_and_status() -> None:
    """Fas-status HÄRLEDS: passed / skipped / active / todo. `status:` finns inte i filerna längre."""
    d = roadmap.roadmap_detail("crusade")
    assert d is not None
    assert [p["key"] for p in d["phases"]] == [
        "discovery", "spec", "mvp", "konsolidera", "live", "users", "validated", "paying"]

    valid = {"passed", "skipped", "active", "todo"}
    assert {p["status"] for p in d["phases"]} <= valid
    assert sum(1 for p in d["phases"] if p["status"] == "active") == 1   # man står på ETT ställe

    spec = next(p for p in d["phases"] if p["key"] == "spec")
    assert len(spec["epics"]) >= 1
    assert spec["steps"]                                    # receptets steg följer med till appen
    assert isinstance(d["open_decisions"], list)


def test_a_skipped_gate_is_visible_in_the_detail() -> None:
    """Skulden ska synas i per-projekt-vyn — annars kan appen inte visa den."""
    d = roadmap.roadmap_detail("orgkomp")
    assert d is not None

    skipped = [p["key"] for p in d["phases"] if p["status"] == "skipped"]
    assert skipped == d["gates_skipped"]
    assert "konsolidera" in skipped      # orgkomp är live men aldrig konsoliderad


if __name__ == "__main__":
    test_recipe_phases(); test_summary_crusade(); test_missing_roadmap_is_none(); test_detail_merges_recipe_and_status()
    print("OK — roadmap reader green")
