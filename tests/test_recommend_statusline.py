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


if __name__ == "__main__":
    test_focus_label()
    print("OK — _focus_label: alla fall gröna")
