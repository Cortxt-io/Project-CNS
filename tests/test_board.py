"""Verifiering av Control Tower-tavlans komposition (scripts/board.board_state).

board_state är injicerbar (husmönstret från dispatch.py), så testerna matar in
fejk-hämtare direkt — ingen disk/Redis/GitHub. Körs fristående eller under pytest.

Täcker: fas-härledning (explicit label / länkad session / default + synlig stale),
WIP-tak, enablement-spår, avblockerings-hävstång + sortering, vem-agerar, tyst degradering.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import board  # noqa: E402

NOW = datetime(2026, 6, 14, 12, 0, 0)


def _issue(number, *, labels=None, depends_on=None, todos=None, acc=None, quest=None, type="story", title=""):
    return {
        "number": number,
        "title": title or f"issue {number}",
        "type": type,
        "quest": quest,
        "node_slug": None,
        "labels": labels or [],
        "depends_on": depends_on or [],
        "todos": todos or [],
        "acceptance_criteria": acc or [],
    }


def _session(number, stype, *, status="done", updated="2026-06-14T11:30:00"):
    return {
        "id": f"session-{number}-{stype}",
        "type": stype,
        "status": status,
        "link": {"kind": "issue", "ref": str(number)},
        "created_at": updated,
        "updated_at": updated,
    }


def _state(*, issues, sessions=None, closed=None, recommend=None, health=None):
    return board.board_state(
        issues_fn=lambda: issues,
        sessions_fn=lambda: sessions or [],
        closed_numbers_fn=lambda: closed or set(),
        recommend_fn=lambda: recommend or [],
        health_fn=health or (lambda issue, **kw: {"level": "healthy", "checks": []}),
        now=NOW,
    )


def _find(state, number):
    for p in board.PHASES:
        for c in state["columns"][p]["cards"]:
            if c["number"] == number:
                return c
    return None


def test_phase_derivation() -> None:
    issues = [
        _issue(1, labels=["phase:review"]),                       # explicit override
        _issue(2),                                                # länkad delivery-session (färsk)
        _issue(3),                                                # ingen länk/label → triage
        _issue(4),                                                # länkad men inaktuell → stale
    ]
    sessions = [
        _session(2, "delivery", updated="2026-06-14T11:00:00"),   # 1h sedan → ej stale
        _session(4, "definition", updated="2026-06-12T00:00:00"), # 60h sedan → stale
    ]
    s = _state(issues=issues, sessions=sessions)

    c1 = _find(s, 1)
    assert c1["phase"] == "review" and c1["phase_explicit"] is True

    c2 = _find(s, 2)
    assert c2["phase"] == "delivery" and c2["phase_explicit"] is False and c2["phase_stale"] is False

    c3 = _find(s, 3)
    assert c3["phase"] == "triage"

    c4 = _find(s, 4)
    assert c4["phase"] == "definition" and c4["phase_stale"] is True


def test_wip_cap_and_pulse() -> None:
    # delivery-tak = 3; fyra delivery-kort ⇒ over_wip. triage saknar tak ⇒ aldrig over.
    issues = [_issue(n, labels=["phase:delivery"]) for n in range(1, 5)]
    issues += [_issue(n) for n in range(10, 16)]  # 6 triage
    s = _state(issues=issues)

    deliv = s["columns"]["delivery"]
    assert deliv["count"] == 4 and deliv["wip_cap"] == 3 and deliv["over_wip"] is True

    triage = s["columns"]["triage"]
    assert triage["count"] == 6 and triage["wip_cap"] is None and triage["over_wip"] is False

    assert s["pulse"]["delivery"] == 4 and s["pulse"]["triage"] == 6


def test_enablement_track_separate() -> None:
    issues = [_issue(1)]
    sessions = [
        _session(1, "enablement", status="running"),  # → enablement-spår, ej kolumn
        _session(99, "delivery", status="running"),
    ]
    s = _state(issues=issues, sessions=sessions)
    assert len(s["enablement"]) == 1
    assert "enablement" not in s["columns"]  # inte en kolumn
    # issue 1 hamnar i enablement-fas? Nej — enablement är ej en PHASE, så fasen blir
    # härledd ur den senaste sessionen vars typ är en PHASE; här finns ingen → triage.
    assert _find(s, 1)["phase"] == "triage"


def test_unlocks_and_leverage_sort() -> None:
    # Beroendekedja: 2,3 → 1 ; 4 → 2.  unlocks[1]=3 (2,3,4 transitivt), unlocks[2]=1.
    issues = [
        _issue(1),
        _issue(2, depends_on=[1]),
        _issue(3, depends_on=[1]),
        _issue(4, depends_on=[2]),
    ]
    s = _state(issues=issues)  # alla → triage (ingen länk)
    cards = s["columns"]["triage"]["cards"]

    by_num = {c["number"]: c for c in cards}
    assert by_num[1]["unlocks"] == 3
    assert by_num[2]["unlocks"] == 1
    assert by_num[3]["unlocks"] == 0

    # Sortering inom kolumnen: störst hävstång först ⇒ kort 1 överst.
    assert cards[0]["number"] == 1
    assert cards[0]["leverage"] >= cards[1]["leverage"] >= cards[-1]["leverage"]


def test_who_acts() -> None:
    issues = [_issue(10), _issue(11), _issue(12)]
    sessions = [_session(10, "delivery", status="running")]  # 10 har agent igång

    def health(issue, **kw):
        return {"level": "attention" if issue["number"] == 11 else "healthy", "checks": []}

    s = _state(issues=issues, sessions=sessions, health=health)
    assert _find(s, 10)["who_acts"] == "agent"   # running länkat pass
    assert _find(s, 11)["who_acts"] == "you"      # health attention
    assert _find(s, 12)["who_acts"] is None        # friskt, ingen session


def test_degrades_silently() -> None:
    def boom(*a, **k):
        raise RuntimeError("källa nere")

    s = board.board_state(
        issues_fn=boom,
        sessions_fn=boom,
        closed_numbers_fn=boom,
        recommend_fn=boom,
        health_fn=boom,
        now=NOW,
    )
    assert s["phases"] == board.PHASES
    assert all(s["columns"][p]["cards"] == [] for p in board.PHASES)
    assert s["enablement"] == [] and s["nudges"] == []
    assert "reachable" in s["freshness"]


if __name__ == "__main__":
    test_phase_derivation()
    test_wip_cap_and_pulse()
    test_enablement_track_separate()
    test_unlocks_and_leverage_sort()
    test_who_acts()
    test_degrades_silently()
    print("OK — board_state: fas-härledning + WIP + enablement + hävstång + vem-agerar + degradering gröna")
