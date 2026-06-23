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
        infra_fn=lambda: {"level": "healthy", "checks": [], "running": "abc", "main_head": "abc", "behind_s": None},
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


def test_infra_field_injected() -> None:
    """infra-fältet kommer från injicerad infra_fn (deploy-/driftshälsa, parallellt med freshness)."""
    degraded = {"level": "degraded", "checks": [{"name": "deploy_staleness", "level": "degraded",
                "feedback": "Prod stale"}], "running": "old1234", "main_head": "new5678", "behind_s": 432000}
    s = cc.command_center_state(
        milestones_fn=lambda: [], issues_for_fn=lambda n: [], all_open_issues_fn=lambda: [],
        sessions_fn=lambda: [], recommend_fn=lambda: [], health_fn=lambda ms, now=None: {"level": "unknown", "checks": []},
        prs_fn=lambda: [], infra_fn=lambda: degraded, now=NOW,
    )
    assert s["infra"]["level"] == "degraded"
    assert s["infra"]["running"] == "old1234" and s["infra"]["main_head"] == "new5678"
    assert s["infra"]["checks"][0]["name"] == "deploy_staleness"


def test_vertical_next_step_rule() -> None:
    """Beskrivande nästa-steg-regel per vertikal (ren, härledd ur signaler)."""
    assert cc._vertical_next_step({"url_live": ""}) == "Skeppa/deploya MVP"
    assert cc._vertical_next_step({"url_live": "x", "activity": {"last_commit_age_s": 10 * 86400}}).startswith("Stale")
    assert cc._vertical_next_step({"url_live": "x", "activity": {"last_commit_age_s": 100},
                                   "open_issues": 2, "top_issue": "Fix scoring"}) == "Bygg: Fix scoring"
    assert cc._vertical_next_step({"url_live": "x", "activity": {"last_commit_age_s": 100},
                                   "open_issues": 0}) == "Definiera nästa arbete / skaffa användare"
    # repo_slug-parsning
    assert cc._repo_slug("https://github.com/Cortxt-io/juvahem") == "Cortxt-io/juvahem"
    assert cc._repo_slug("") is None


def test_verticals_field_injected() -> None:
    """verticals-fältet kommer från injicerad verticals_fn (parallellt med missions/infra)."""
    fake = [{"slug": "juvahem", "title": "Juvahem", "url_live": "https://juvahem.se",
             "open_issues": 1, "next_step": "Bygg: X"}]
    s = cc.command_center_state(
        milestones_fn=lambda: [], issues_for_fn=lambda n: [], all_open_issues_fn=lambda: [],
        sessions_fn=lambda: [], recommend_fn=lambda: [], health_fn=lambda ms, now=None: {"level": "unknown", "checks": []},
        prs_fn=lambda: [], infra_fn=lambda: {"level": "healthy", "checks": []},
        verticals_fn=lambda: fake, now=NOW,
    )
    assert s["verticals"] == fake and s["verticals"][0]["next_step"] == "Bygg: X"


def test_issues_client_repo_override() -> None:
    """list_issues/list_milestones repo-param overridar GITHUB_REPO (default oförändrat)."""
    import os
    from scripts import issues_client as ic
    os.environ["CNS_GITHUB_TOKEN"] = "t"
    os.environ["GITHUB_REPO"] = "Cortxt-io/Project-CNS"
    assert ic._require_config(None, "Cortxt-io/juvahem")[0] == "Cortxt-io/juvahem"
    assert ic._require_config(None)[0] == "Cortxt-io/Project-CNS"


def test_next_step_roadmap_aware() -> None:
    """När en roadmap finns styr den next_step (öppet beslut → fas), annars grova signaler."""
    assert cc._vertical_next_step({"url_live": "x", "roadmap": {"open_decisions": 2, "next_decision": "Publik yta?", "current_phase_title": "Spec"}}) == "Beslut: Publik yta?"
    assert cc._vertical_next_step({"url_live": "x", "roadmap": {"open_decisions": 0, "current_phase_title": "MVP"}}) == "Driv fas: MVP"
    assert cc._vertical_next_step({"url_live": "", "roadmap": None}) == "Skeppa/deploya MVP"
