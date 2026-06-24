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
    s = roadmap.roadmap_summary("crusade")
    assert s is not None
    assert s["current_phase"] == "spec" and s["phase_index"] == 2 and s["total_phases"] == 8
    assert s["open_decisions"] >= 1 and s["next_decision"]


def test_missing_roadmap_is_none() -> None:
    assert roadmap.load_roadmap("does-not-exist") is None
    assert roadmap.roadmap_summary("does-not-exist") is None


def test_detail_merges_recipe_and_status() -> None:
    d = roadmap.roadmap_detail("crusade")
    assert d is not None
    assert [p["key"] for p in d["phases"]] == ["discovery", "spec", "mvp", "konsolidera", "live", "users", "validated", "paying"]
    spec = next(p for p in d["phases"] if p["key"] == "spec")
    assert spec["status"] == "active" and len(spec["epics"]) >= 1
    assert isinstance(d["open_decisions"], list)


if __name__ == "__main__":
    test_recipe_phases(); test_summary_crusade(); test_missing_roadmap_is_none(); test_detail_merges_recipe_and_status()
    print("OK — roadmap reader green")
