"""Verifiering av orienteringsradens fokus-härledning (scripts/recommend.py).

Testar ``_focus_label`` — hur den aktiva sessionens ``link`` blir en läsbar
fokus-etikett i statusraden (orienteringsyta, idea-7548a67a). Patchar
``session_store.get_session`` så ingen disk/Redis behövs.

Körs fristående (``python tests/test_recommend_statusline.py``) ELLER under
pytest om det finns. Exit ≠ 0 om något fall fallerar.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import recommend, session_store  # noqa: E402

# _focus_label gör `from scripts.session_store import get_session` vid varje
# anrop, så att patcha attributet på modulen räcker.
_SESSIONS = {
    "s-node": {"link": {"kind": "node", "ref": "cns-core"}},
    "s-quest": {"link": {"kind": "quest", "ref": "8"}},
    "s-issue": {"link": {"kind": "issue", "ref": "39"}},
    "s-idea": {"link": {"kind": "idea", "ref": "abc123"}},
    "s-nolink": {"link": None},
}


def test_focus_label() -> None:
    orig = session_store.get_session
    session_store.get_session = lambda sid: _SESSIONS.get(sid)
    try:
        assert recommend._focus_label("s-node") == "cns-core"
        assert recommend._focus_label("s-quest") == "quest #8"
        assert recommend._focus_label("s-issue") == "#39"
        assert recommend._focus_label("s-idea") == "idé abc123"
        # Inget att visa → None (degraderar tyst, bryter inte statusraden):
        assert recommend._focus_label("s-nolink") is None
        assert recommend._focus_label(None) is None
        assert recommend._focus_label("saknas") is None
    finally:
        session_store.get_session = orig


def test_colored() -> None:
    # Känd typ → ANSI-wrappad; okänd/None → oförändrad (statusraden bryts ej).
    assert recommend._colored("triage", "triage") == "\033[33mtriage\033[0m"
    assert recommend._colored("delivery", "delivery") == "\033[32mdelivery\033[0m"
    assert recommend._colored("x", None) == "x"
    assert recommend._colored("x", "okänd-typ") == "x"


def test_context_pct() -> None:
    assert recommend._context_pct({"context_window": {"used_percentage": 82.5}}) == 82.5
    assert recommend._context_pct({"context_window": {"used_percentage": None}}) is None  # tidigt/efter compact
    assert recommend._context_pct({}) is None
    assert recommend._context_pct(None) is None


def test_compact_segment() -> None:
    # Över tröskel → /compact-signal; under/None → inget (statusraden bryts ej).
    assert recommend._compact_segment(80) == "\033[33m⚠ kontext 80% → /compact\033[0m"
    assert recommend._compact_segment(recommend.CONTEXT_COMPACT_THRESHOLD) is not None  # gräns inkluderad
    assert recommend._compact_segment(50) is None
    assert recommend._compact_segment(None) is None


if __name__ == "__main__":
    test_focus_label()
    test_colored()
    test_context_pct()
    test_compact_segment()
    print("OK — _focus_label + _colored + _context_pct + _compact_segment: alla fall gröna")
