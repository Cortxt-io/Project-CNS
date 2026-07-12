"""Session visual identity + auto-names (#41): single-source palette and naming."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import session_store as ss  # noqa: E402

# test_recommend_palette_derives_from_single_source flyttades till tests/frozen/ när agentur-lagret
# frystes (2026-07-12) — recommend.py bor i lab/frozen/. SESSION_TYPE_STYLE-enkällan testas här.

WHEN = datetime(2026, 6, 14, 9, 0, 0)


def test_auto_name_format():
    assert ss.auto_session_name("triage", when=WHEN, count=3) == "Triage #3 – 14 jun"


def test_auto_name_canonicalizes_legacy_type():
    # legacy "bygg" → "delivery"
    assert ss.auto_session_name("bygg", when=WHEN, count=1) == "Delivery #1 – 14 jun"


def test_auto_name_falls_back_when_type_missing():
    assert ss.auto_session_name(None, when=WHEN, count=1) == "Session #1 – 14 jun"


def test_type_style_known_and_legacy():
    assert ss.type_style("delivery")["rich"] == "green"
    assert ss.type_style("bygg")["icon"] == "🟢"  # legacy alias resolves
    assert ss.type_style("nope") == {}
    assert ss.type_style(None) == {}


def test_start_session_auto_names_when_summary_blank(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "SESSIONS_DIR", tmp_path / "sessions")
    s = ss.start_session(session_type="triage", summary="   ")
    assert s["summary"].startswith("Triage #1 – ")
    # An explicit summary is preserved.
    s2 = ss.start_session(session_type="triage", summary="real summary")
    assert s2["summary"] == "real summary"
