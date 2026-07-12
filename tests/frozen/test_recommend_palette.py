"""Fryst (2026-07-12): statusradens palett måste härledas ur session_store.SESSION_TYPE_STYLE.

Bröts ut ur tests/test_session_identity.py när agentur-lagret frystes — recommend.py bor i
lab/frozen/. Resten av den filen testar session_store (levande) och kör fortfarande i CI.
Detta test körs inte (pytest.ini exkluderar tests/frozen/); det finns kvar som beviset som gör
lagret väckbart. Se lab/frozen/FROZEN.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import session_store as ss  # noqa: E402

from lab.frozen import recommend  # noqa: E402


def test_recommend_palette_derives_from_single_source():
    # The statusline colors/icons must equal the session_store source of truth.
    assert recommend.SESSION_COLORS == {
        t: s["ansi"] for t, s in ss.SESSION_TYPE_STYLE.items()
    }
    assert recommend.SESSION_ICONS["delivery"] == "🟢"
    # ANSI values unchanged by the dedup (regression guard).
    assert recommend.SESSION_COLORS["definition"] == "38;5;208"
    assert recommend.SESSION_COLORS["retro"] == "90"
