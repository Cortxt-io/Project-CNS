"""Verifiering av observabilitetsmetriker i session_store (issue #58).

``is_phantom``/``elapsed_seconds`` testas rent; ``record_metrics`` mot en temp-
katalog (ingen riktig exports/sessions rörs). Körs fristående
(``python tests/test_session_metrics.py``) ELLER under pytest. Exit ≠ 0 vid fel.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import session_store as ss  # noqa: E402


def test_is_phantom() -> None:
    running = {"status": "running", "metrics": {"tokens_in": 4000, "tokens_out": 2000, "artifacts": []}}
    assert ss.is_phantom(running) is True                                   # 6000 > tröskel, inga artefakter
    assert ss.is_phantom({**running, "metrics": {"tokens_in": 4000, "tokens_out": 2000, "artifacts": ["#42"]}}) is False
    assert ss.is_phantom({**running, "status": "done"}) is False            # done flaggas aldrig
    assert ss.is_phantom({"status": "running", "metrics": {"tokens_in": 100, "tokens_out": 0, "artifacts": []}}) is False
    assert ss.is_phantom({"status": "running"}) is False                    # inga metrics → ej fantom (gammal post)


def test_elapsed_seconds() -> None:
    assert ss.elapsed_seconds({"created_at": "2026-06-11T10:00:00", "updated_at": "2026-06-11T10:01:30"}) == 90.0
    assert ss.elapsed_seconds({"created_at": "x", "updated_at": "y"}) is None


def test_record_metrics() -> None:
    orig_dir = ss.SESSIONS_DIR
    with tempfile.TemporaryDirectory() as d:
        ss.SESSIONS_DIR = Path(d)
        try:
            sess = ss.start_session(link_kind="issue", link_ref="58", session_type="delivery")
            sid = sess["id"]
            assert sess["metrics"] == ss._new_metrics()                     # nystart = tomma metriker
            ss.record_metrics(sid, tools=["Read", "Edit"], tokens_in=3000, tokens_out=1000)
            ss.record_metrics(sid, tools=["Read"], tokens_in=2000, tokens_out=500)   # Read dedupas
            m = ss.get_session(sid)["metrics"]
            assert m["tool_calls"] == 3                                      # 2 + 1
            assert sorted(m["tools_seen"]) == ["Edit", "Read"]              # unika verktyg
            assert m["tokens_in"] == 5000 and m["tokens_out"] == 1500
            assert ss.is_phantom(ss.get_session(sid)) is True               # 6500 tokens, inga artefakter
            ss.record_metrics(sid, artifact="PR #62")
            assert ss.is_phantom(ss.get_session(sid)) is False              # artefakt → framsteg, ej fantom
        finally:
            ss.SESSIONS_DIR = orig_dir


if __name__ == "__main__":
    test_is_phantom()
    test_elapsed_seconds()
    test_record_metrics()
    print("OK — session_store-metrics: alla fall gröna")
