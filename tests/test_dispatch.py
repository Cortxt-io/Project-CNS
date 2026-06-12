"""Verifiering av dispatch-loopen (scripts/dispatch.py, #59 Fas 3, övervakad crawl).

Ren logik — ALLA beroenden injiceras (ingen GitHub/Redis/LLM/SDK behövs). Bevisar:
lämplighetsgrinden hoppar diffusa/feature-tunga/oklara-dep; crawl_once gatear varje
muterande steg bakom ``approve`` (default nekar); leasen släpps alltid (orphan-cleanup);
eval-grinden (#57) stoppar done; kill-switch bryter. Körs fristående eller under pytest.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import dispatch  # noqa: E402
from scripts.dispatch import (  # noqa: E402
    ACTION_CLAIM,
    ACTION_OPEN_PR,
    ACTION_RUN,
    CrawlResult,
    _reduce_events,
    assess_suitability,
    crawl_once,
    select_next_issue,
)


# --- testfixtur: en minimal in-memory session_store ------------------------


class FakeSessions:
    def __init__(self):
        self.store = {}
        self._n = 0

    def start_session(self, **kw):
        self._n += 1
        sid = f"session-{self._n:04x}"
        self.store[sid] = {"id": sid, "status": "running", **kw}
        return self.store[sid]

    def mark_done(self, sid, summary=None):
        self.store[sid]["status"] = "done"
        if summary:
            self.store[sid]["summary"] = summary
        return self.store[sid]

    def record_metrics(self, sid, **kw):
        self.store[sid].setdefault("metrics", []).append(kw)
        return self.store[sid]


def _issue(number, **kw):
    base = {
        "number": number,
        "title": f"Issue {number}",
        "node_slug": "agentur",
        "state": "open",
        "type": "bug",
        "todos": [{"text": "fix", "done": False}],
        "acceptance_criteria": [],
        "depends_on": [],
        "body": "gör grejen",
    }
    base.update(kw)
    return base


def _base_kwargs(sessions, **over):
    """Default-injektioner som låter crawlen köra utan något riktigt I/O."""
    kw = dict(
        owner="tester",
        candidates_fn=lambda: [_issue(10)],
        closed_numbers_fn=lambda: set(),
        approve=lambda a, c: True,
        run_pass=lambda **k: {"result": "förslag: ändra X", "metrics": {"turns": 3, "tokens": 1000}},
        is_claimable_fn=lambda n: True,
        claim_fn=lambda n, o: {"claimed": True, "owner": o},
        release_fn=lambda n, o: {"released": True},
        overlap_fn=lambda slug: (True, []),
        role_fn=lambda slug, itype: {"slug": "byggare", "model": "sonnet"},
        eval_fn=lambda slug, output: {"status": "ok", "all_pass": True, "passed": 2, "total": 2},
        session_store=sessions,
    )
    kw.update(over)
    return kw


# --- lämplighetsbedömning --------------------------------------------------


def test_suitability_skips_unmet_dependency():
    s = assess_suitability(_issue(1, depends_on=[99]), closed_numbers=set())
    assert not s.suitable and "depends_on" in s.reason


def test_suitability_passes_when_dependency_closed():
    s = assess_suitability(_issue(1, depends_on=[99]), closed_numbers={99})
    assert s.suitable


def test_suitability_skips_diffuse_issue():
    s = assess_suitability(_issue(1, todos=[], acceptance_criteria=[]), closed_numbers=set())
    assert not s.suitable and "diffus" in s.reason


def test_suitability_skips_feature_heavy_story():
    big = [{"text": f"t{i}", "done": False} for i in range(dispatch.MAX_STORY_TODOS + 1)]
    s = assess_suitability(_issue(1, type="story", todos=big), closed_numbers=set())
    assert not s.suitable and "feature-tung" in s.reason


def test_suitability_allows_small_story():
    s = assess_suitability(_issue(1, type="story"), closed_numbers=set())
    assert s.suitable


def test_suitability_skips_closed():
    s = assess_suitability(_issue(1, state="closed"), closed_numbers=set())
    assert not s.suitable


# --- urval -----------------------------------------------------------------


def test_select_skips_held_issue_then_picks_free():
    held = _issue(10)
    free = _issue(11)
    issue, why = select_next_issue(
        [held, free], closed_numbers=set(), is_claimable=lambda n: n != 10
    )
    assert issue["number"] == 11


def test_select_reports_all_held():
    issue, why = select_next_issue(
        [_issue(10)], closed_numbers=set(), is_claimable=lambda n: False
    )
    assert issue is None and "claimade" in why


def test_select_no_suitable():
    issue, why = select_next_issue(
        [_issue(10, todos=[], acceptance_criteria=[])],
        closed_numbers=set(),
        is_claimable=lambda n: True,
    )
    assert issue is None and "ingen lämplig" in why


# --- crawl_once: grindar, lease, eval, kill-switch -------------------------


def test_crawl_no_work():
    res = crawl_once(**_base_kwargs(FakeSessions(), candidates_fn=lambda: []))
    assert res.status == "no-work"


def test_crawl_claim_denied_does_not_claim():
    claimed = []
    res = crawl_once(
        **_base_kwargs(
            FakeSessions(),
            approve=lambda a, c: a != ACTION_CLAIM,
            claim_fn=lambda n, o: claimed.append(n) or {"claimed": True},
        )
    )
    assert res.status == "denied" and not claimed


def test_crawl_blocked_when_claim_held_by_other():
    res = crawl_once(**_base_kwargs(FakeSessions(), claim_fn=lambda n, o: {"claimed": False, "owner": "X"}))
    assert res.status == "blocked" and "redan claimad" in res.detail


def test_crawl_proceeds_when_redis_unavailable_failopen():
    released = []
    res = crawl_once(
        **_base_kwargs(
            FakeSessions(),
            claim_fn=lambda n, o: {"claimed": False, "reason": "redis-unavailable"},
            release_fn=lambda n, o: released.append(n) or {"released": True},
        )
    )
    # Lease degraderad → kör hela vägen (ran), och INGET release (inget att släppa).
    assert res.status == "ran" and not released


def test_crawl_releases_lease_always():
    released = []
    res = crawl_once(
        **_base_kwargs(FakeSessions(), release_fn=lambda n, o: released.append(n) or {"released": True})
    )
    assert released == [10] and res.status == "ran"


def test_crawl_ran_marks_session_done_on_eval_pass():
    sessions = FakeSessions()
    res = crawl_once(**_base_kwargs(sessions))
    assert res.status == "ran"
    assert sessions.store[res.session_id]["status"] == "done"


def test_crawl_eval_fail_leaves_session_running():
    sessions = FakeSessions()
    res = crawl_once(
        **_base_kwargs(
            sessions,
            eval_fn=lambda s, o: {"status": "ok", "all_pass": False, "passed": 1, "total": 2},
        )
    )
    assert res.status == "ran" and "eval-grind" in res.detail
    assert sessions.store[res.session_id]["status"] == "running"


def test_crawl_opens_draft_pr_when_wired_and_approved():
    sessions = FakeSessions()
    res = crawl_once(
        **_base_kwargs(sessions, open_pr_fn=lambda issue, outcome: {"number": 77, "draft": True})
    )
    assert res.status == "ran" and res.pr["number"] == 77


def test_crawl_killswitch_before_claim_releases_nothing():
    released = []
    res = crawl_once(
        **_base_kwargs(
            FakeSessions(),
            should_abort=lambda: True,
            release_fn=lambda n, o: released.append(n) or {"released": True},
        )
    )
    assert res.status == "denied" and not released


def test_crawl_write_mode_commits_and_opens_draft_pr():
    sessions = FakeSessions()
    seen = {}
    res = crawl_once(
        **_base_kwargs(
            sessions,
            worktree_fn=lambda n: {"path": f"/wt/{n}", "branch": f"dispatch/issue-{n}"},
            commit_fn=lambda path, msg: True,
            cleanup_fn=lambda path: seen.__setitem__("cleaned", path),
            run_pass=lambda **k: seen.update(k) or {"result": "klart", "metrics": {"turns": 4}},
            open_pr_fn=lambda issue, outcome: {"number": 88, "draft": True, "branch": outcome["worktree"]["branch"]},
        )
    )
    assert res.status == "ran" and res.pr["number"] == 88
    assert seen["allow_writes"] is True and seen["cwd"] == "/wt/10"  # skrev i worktree
    assert seen["cleaned"] == "/wt/10"  # worktree städat


def test_crawl_write_mode_no_changes_skips_pr():
    pr_calls = []
    res = crawl_once(
        **_base_kwargs(
            FakeSessions(),
            worktree_fn=lambda n: {"path": f"/wt/{n}", "branch": f"b-{n}"},
            commit_fn=lambda path, msg: False,  # passet ändrade inget
            cleanup_fn=lambda path: None,
            open_pr_fn=lambda issue, outcome: pr_calls.append(1) or {"number": 1},
        )
    )
    assert res.status == "ran" and "inga ändringar" in res.detail and not pr_calls


def test_crawl_write_mode_cleans_worktree_on_pass_crash():
    cleaned = []

    def boom(**k):
        raise RuntimeError("sdk nere")

    res = crawl_once(
        **_base_kwargs(
            FakeSessions(),
            worktree_fn=lambda n: {"path": f"/wt/{n}", "branch": f"b-{n}"},
            commit_fn=lambda p, m: True,
            cleanup_fn=lambda path: cleaned.append(path),
            run_pass=boom,
        )
    )
    assert res.status == "error" and cleaned == ["/wt/10"]


def test_crawl_blocked_when_no_role_resolves():
    ran = []
    res = crawl_once(
        **_base_kwargs(
            FakeSessions(),
            role_fn=lambda slug, itype: None,  # routing gav ingen roll (t.ex. #95)
            run_pass=lambda **k: ran.append(1) or {"result": "x"},
        )
    )
    assert res.status == "blocked" and "ingen roll" in res.detail
    assert not ran  # inget pass kördes


def test_crawl_no_role_releases_lease():
    released = []
    crawl_once(
        **_base_kwargs(
            FakeSessions(),
            role_fn=lambda slug, itype: None,
            release_fn=lambda n, o: released.append(n) or {"released": True},
        )
    )
    assert released == [10]


def test_crawl_empty_pass_not_marked_done():
    sessions = FakeSessions()
    res = crawl_once(
        **_base_kwargs(sessions, run_pass=lambda **k: {"result": "", "metrics": {"turns": 0}})
    )
    assert res.status == "ran" and "tomt pass" in res.detail
    assert sessions.store[res.session_id]["status"] == "running"  # ej done


def test_reduce_events_falls_back_to_text_blocks():
    events = [
        ("session", "sid-1"),
        ("text", "förslag: "),
        ("text", "ändra X"),
        ("metrics", {"turns": 2}),
        ("result", ""),  # tom result → ska falla tillbaka på text-blocken
    ]
    out = _reduce_events(events)
    assert out["result"] == "förslag: \nändra X"
    assert out["agent_session_id"] == "sid-1" and out["metrics"]["turns"] == 2


def test_reduce_events_prefers_nonempty_result():
    events = [("text", "rådata"), ("result", "slutligt svar")]
    assert _reduce_events(events)["result"] == "slutligt svar"


def test_reduce_events_raises_on_error():
    try:
        _reduce_events([("error", "sdk nere")])
        assert False, "skulle kastat"
    except RuntimeError as exc:
        assert "sdk nere" in str(exc)


def test_crawl_pass_crash_releases_lease():
    released = []

    def boom(**k):
        raise RuntimeError("sdk nere")

    res = crawl_once(
        **_base_kwargs(
            FakeSessions(),
            run_pass=boom,
            release_fn=lambda n, o: released.append(n) or {"released": True},
        )
    )
    assert res.status == "error" and released == [10]


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
