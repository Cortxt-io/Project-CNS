"""Verifiering av den härledda hälso-scorecarden (scripts/health.py).

Rena funktioner — alla indata är syntetiska dicts, ingen GitHub/nätverk. ``now``
injiceras så staleness blir deterministisk. Speglar test_dispatch.py-stilen och
kör fristående eller under pytest.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import health  # noqa: E402
from scripts.health import (  # noqa: E402
    Check,
    _rollup,
    _scorecard,
    health_for_initiative,
    health_for_issue,
    health_for_milestone,
    health_for_node,
    health_for_session,
)

NOW = datetime(2026, 6, 13, 12, 0, 0)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _session(**kw) -> dict:
    base = {
        "status": "running",
        "created_at": _iso(NOW - timedelta(hours=1)),
        "updated_at": _iso(NOW - timedelta(hours=1)),
        "metrics": {"tokens_in": 0, "tokens_out": 0, "artifacts": []},
    }
    base.update(kw)
    return base


def _issue(**kw) -> dict:
    base = {
        "number": 1,
        "node_slug": "cns-core",
        "state": "open",
        "created_at": _iso(NOW - timedelta(days=1)),
        "todos": [],
        "depends_on": [],
        "acceptance_criteria": [],
    }
    base.update(kw)
    return base


def _milestone(**kw) -> dict:
    base = {
        "number": 8,
        "title": "Epic",
        "state": "open",
        "open_issues": 3,
        "closed_issues": 1,
        "progress": 0.25,
        "initiative": "Agentur",
        "created_at": _iso(NOW - timedelta(days=10)),
        "updated_at": _iso(NOW - timedelta(days=1)),
    }
    base.update(kw)
    return base


# --- _rollup / _scorecard --------------------------------------------------

def test_rollup_worst_wins():
    checks = [Check("a", "healthy", ""), Check("b", "degraded", ""), Check("c", "attention", "")]
    assert _rollup(checks) == "degraded"


def test_rollup_all_unknown():
    assert _rollup([Check("a", "unknown", ""), Check("b", "unknown", "")]) == "unknown"


def test_rollup_unknown_never_outranks_signal():
    # Ett enda riktigt healthy vinner över unknown.
    assert _rollup([Check("a", "unknown", ""), Check("b", "healthy", "")]) == "healthy"


def test_scorecard_shape():
    sc = _scorecard([Check("x", "attention", "fix it")])
    assert sc["level"] == "attention"
    assert sc["checks"] == [{"name": "x", "level": "attention", "feedback": "fix it"}]


# --- Session ---------------------------------------------------------------

def test_session_phantom_degraded():
    s = _session(metrics={"tokens_in": 3000, "tokens_out": 4000, "artifacts": []})
    assert health_for_session(s, now=NOW)["level"] == "degraded"


def test_session_fresh_running_healthy():
    s = _session(updated_at=_iso(NOW - timedelta(minutes=10)))
    assert health_for_session(s, now=NOW)["level"] == "healthy"


def test_session_stale_running_attention():
    s = _session(updated_at=_iso(NOW - timedelta(hours=24)))
    assert health_for_session(s, now=NOW)["level"] == "attention"


def test_session_done_healthy():
    s = _session(status="done", updated_at=_iso(NOW - timedelta(days=5)))
    assert health_for_session(s, now=NOW)["level"] == "healthy"


# --- Issue -----------------------------------------------------------------

def test_issue_blocked_degraded():
    i = _issue(depends_on=[99])
    assert health_for_issue(i, closed_numbers=set(), now=NOW)["level"] == "degraded"


def test_issue_dependency_met_not_blocked():
    i = _issue(depends_on=[99])
    assert health_for_issue(i, closed_numbers={99}, now=NOW)["level"] in ("healthy", "unknown")


def test_issue_partial_stale_attention():
    i = _issue(
        created_at=_iso(NOW - timedelta(weeks=5)),
        todos=[{"done": True}, {"done": False}],
    )
    assert health_for_issue(i, closed_numbers=set(), now=NOW)["level"] == "attention"


def test_issue_acceptance_done_but_open_attention():
    i = _issue(acceptance_criteria=[{"done": True}, {"done": True}])
    assert health_for_issue(i, closed_numbers=set(), now=NOW)["level"] == "attention"


# --- Epic / milestone ------------------------------------------------------

def test_epic_stalled_attention():
    ms = _milestone(open_issues=4, closed_issues=0, progress=0.0, created_at=_iso(NOW - timedelta(weeks=6)))
    assert health_for_milestone(ms, now=NOW)["level"] == "attention"


def test_epic_bookkeeping_lag_attention():
    ms = _milestone(open_issues=0, closed_issues=5, progress=1.0, state="open")
    assert health_for_milestone(ms, now=NOW)["level"] == "attention"


def test_epic_missing_updated_at_staleness_unknown():
    ms = _milestone(updated_at=None)
    # Staleness-checken degraderar till unknown, kraschar inte; epic är annars frisk.
    sc = health_for_milestone(ms, now=NOW)
    staleness = next(c for c in sc["checks"] if c["name"] == "milestone_staleness")
    assert staleness["level"] == "unknown"


def test_epic_healthy_when_moving():
    ms = _milestone(open_issues=2, closed_issues=2, progress=0.5, updated_at=_iso(NOW - timedelta(days=1)))
    assert health_for_milestone(ms, now=NOW)["level"] == "healthy"


# --- Initiativ -------------------------------------------------------------

def test_initiative_rollup_worst_child():
    healthy = _milestone(number=1, initiative="X", open_issues=1, closed_issues=1, progress=0.5)
    stalled = _milestone(number=2, initiative="X", open_issues=4, closed_issues=0, progress=0.0,
                         created_at=_iso(NOW - timedelta(weeks=6)))
    other = _milestone(number=3, initiative="Y")
    sc = health_for_initiative("X", [healthy, stalled, other], now=NOW)
    assert sc["level"] == "attention"


def test_initiative_no_epics_unknown():
    assert health_for_initiative("Z", [], now=NOW)["level"] == "unknown"


# --- Nod -------------------------------------------------------------------

def test_node_degraded_issue_bubbles_up():
    blocked = _issue(number=1, node_slug="cns-core", depends_on=[99])
    issues = [blocked, _issue(number=99, state="open", node_slug="other")]
    # systems=None ⇒ strukturell check kör mot riktig katalog; använd ett känt slug.
    sc = health_for_node("cns-core", issues=issues, systems={"cns-core": {}}, now=NOW)
    assert sc["level"] == "degraded"


def test_node_structural_error_degraded():
    # Trasig part_of ⇒ validate_catalog ger fel för slug ⇒ degraded.
    systems = {"broken": {"part_of": "does-not-exist"}}
    sc = health_for_node("broken", issues=[], systems=systems, now=NOW)
    assert sc["level"] == "degraded"


def test_node_clean_no_issues_unknown_or_healthy():
    systems = {"clean": {}}
    sc = health_for_node("clean", issues=[], systems=systems, now=NOW)
    # Inga issues ⇒ issue-roll-up unknown; strukturellt ren ⇒ healthy. Roll-up = healthy.
    assert sc["level"] in ("healthy", "unknown")


if __name__ == "__main__":
    import traceback

    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passerade")
    sys.exit(1 if failed else 0)


def test_deploy_staleness() -> None:
    """check_deploy_staleness: prod vs main HEAD — degraderar till unknown, aldrig falsk grön."""
    assert health.check_deploy_staleness("abc123def456", "abc123def456ff", None).level == "healthy"
    assert health.check_deploy_staleness("aaa", "bbb", 600).level == "attention"
    assert health.check_deploy_staleness("aaa", "bbb", 5 * 3600).level == "degraded"
    assert health.check_deploy_staleness(None, "bbb", None).level == "unknown"
    assert health.check_deploy_staleness("aaa", None, None).level == "unknown"
    # scorecard-form
    sc = health.health_for_deploy("aaa", "bbb", gap_seconds=5 * 3600)
    assert sc["level"] == "degraded" and sc["checks"][0]["name"] == "deploy_staleness"
