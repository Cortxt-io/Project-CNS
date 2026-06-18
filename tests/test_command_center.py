"""Verifiering av Command Center-komposition (scripts/command_center.command_center_state).

Injicerbar → fejk-hämtare, ingen GitHub/disk. Täcker: readiness ur health, multi-fas-fronter,
units/commander, contact report, hävstångs-sortering (degraded→operational, sen hävstång),
sitrep-räkning, logistics, tyst degradering.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import command_center as cc  # noqa: E402

NOW = datetime(2026, 6, 14, 12, 0, 0)


def _sess(issue, stype, status="running"):
    return {"type": stype, "status": status, "link": {"kind": "issue", "ref": str(issue)}}


def _state(*, milestones, issues_map, all_open, sessions, orders=None, health_map=None, prs=None):
    def health(ms, now=None):
        lvl = (health_map or {}).get(ms["number"], "unknown")
        checks = [{"name": "blocked", "level": "degraded", "feedback": "PR #99 väntar på review"}] if lvl == "degraded" else []
        return {"level": lvl, "checks": checks}

    return cc.command_center_state(
        milestones_fn=lambda: milestones,
        issues_for_fn=lambda n: issues_map.get(n, []),
        all_open_issues_fn=lambda: all_open,
        sessions_fn=lambda: sessions,
        recommend_fn=lambda: orders or [],
        health_fn=health,
        prs_fn=lambda: prs or [],
        now=NOW,
    )


def _mission(state, number):
    return next((m for m in state["missions"] if m["number"] == number), None)


def test_readiness_fronts_units_contact() -> None:
    milestones = [{"number": 8, "title": "Control Tower", "open_issues": 2}]
    issues_map = {8: [{"number": 50, "depends_on": []}, {"number": 51, "depends_on": []}]}
    sessions = [_sess(50, "delivery"), _sess(51, "discovery")]  # två fronter samtidigt
    s = _state(milestones=milestones, issues_map=issues_map, all_open=issues_map[8],
               sessions=sessions, orders=[{"type": "delivery", "refs": ["quest #8"]}],
               health_map={8: "degraded"})
    m = _mission(s, 8)
    assert m["readiness"] == "degraded"
    assert m["fronts"] == ["discovery", "delivery"]   # MULTI-FAS, fas-ordning bevarad
    assert m["units"] == 2 and m["commander"] is False  # enheter kör → ej väntar på dig
    assert m["contact"] == "PR #99 väntar på review"
    assert m["order"] == "delivery → /session delivery"  # ur FRAGO


def test_commander_when_idle_and_unhealthy() -> None:
    milestones = [{"number": 9, "title": "X", "open_issues": 1}]
    issues_map = {9: [{"number": 60, "depends_on": []}]}
    s = _state(milestones=milestones, issues_map=issues_map, all_open=issues_map[9],
               sessions=[], health_map={9: "attention"})
    m = _mission(s, 9)
    assert m["readiness"] == "watch"
    assert m["units"] == 0 and m["commander"] is True   # inget kör + ohälsosam → väntar på dig
    assert m["fronts"] == []


def test_leverage_sort_and_sitrep() -> None:
    milestones = [
        {"number": 9, "title": "frisk", "open_issues": 1},
        {"number": 8, "title": "degraded", "open_issues": 1},
        {"number": 10, "title": "watch", "open_issues": 1},
    ]
    issues_map = {9: [{"number": 60, "depends_on": []}], 8: [{"number": 50, "depends_on": []}], 10: [{"number": 70, "depends_on": []}]}
    # #61 beror på #60 → mission 9 får hävstång 1 (men degraded sorteras ändå först)
    all_open = [{"number": 60, "depends_on": []}, {"number": 61, "depends_on": [60]},
                {"number": 50, "depends_on": []}, {"number": 70, "depends_on": []}]
    s = _state(milestones=milestones, issues_map=issues_map, all_open=all_open,
               sessions=[], health_map={8: "degraded", 10: "attention", 9: "healthy"})
    order = [m["number"] for m in s["missions"]]
    assert order == [8, 10, 9]   # degraded → watch → operational
    assert s["sitrep"] == {"operational": 1, "watch": 1, "degraded": 1, "dark": 0}


def test_logistics_track() -> None:
    s = _state(milestones=[], issues_map={}, all_open=[],
               sessions=[{"type": "enablement", "status": "running", "summary": "uppdatera skill", "link": None}])
    assert len(s["logistics"]) == 1 and s["logistics"][0]["summary"] == "uppdatera skill"


def test_council_decisions_and_badge() -> None:
    prs = [
        {"number": 50, "title": "draft A", "draft": True, "created_at": "2026-06-14T10:00:00Z"},
        {"number": 51, "title": "ready B", "draft": False, "created_at": "2026-06-13T10:00:00Z"},
    ]
    # draft sorteras först (väntar på review), oavsett ålder
    decisions = cc.council_decisions(prs_fn=lambda: prs)
    assert [d["number"] for d in decisions] == [50, 51]
    # badge-räknaren speglar antalet
    s = _state(milestones=[], issues_map={}, all_open=[], sessions=[], prs=prs)
    assert s["command"]["decisions"] == 2


def test_degrades_silently() -> None:
    def boom(*a, **k):
        raise RuntimeError("nere")

    s = cc.command_center_state(
        milestones_fn=boom, issues_for_fn=boom, all_open_issues_fn=boom,
        sessions_fn=boom, recommend_fn=boom, health_fn=boom, prs_fn=boom, now=NOW,
    )
    assert s["missions"] == [] and s["orders"] == [] and s["logistics"] == []
    assert s["sitrep"]["degraded"] == 0 and s["command"]["decisions"] == 0 and "reachable" in s["freshness"]


if __name__ == "__main__":
    test_readiness_fronts_units_contact()
    test_commander_when_idle_and_unhealthy()
    test_leverage_sort_and_sitrep()
    test_logistics_track()
    test_degrades_silently()
    print("OK — command_center_state: readiness/fronter/units/contact/sortering/sitrep/logistics/degradering gröna")
