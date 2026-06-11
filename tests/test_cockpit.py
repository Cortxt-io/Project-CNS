"""Verifiering av orienteringsytans komposition (scripts/tui/data.cockpit_state).

Patchar session_store / recommend / sources så ingen disk/Redis/GitHub behövs.
Körs fristående (``python tests/test_cockpit.py``) ELLER under pytest.

Testar att de fyra blocken (var du slutade · igång · härnäst · i fokus) komponeras
rätt, att fokus faller tillbaka på aktiv sessions link, och att vyn degraderar tyst
när källorna är tomma/onåbara (idea-7548a67a / epic #8).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import recommend, session_store  # noqa: E402
from scripts.tui import data, sources  # noqa: E402


def _patch(**overrides):
    """Sätt attribut på rätt modul; returnera en restore-funktion."""
    originals = {}
    for dotted, value in overrides.items():
        mod_name, attr = dotted.rsplit(".", 1)
        mod = {"ss": session_store, "rec": recommend, "src": sources}[mod_name]
        originals[(mod, attr)] = getattr(mod, attr)
        setattr(mod, attr, value)

    def restore():
        for (mod, attr), val in originals.items():
            setattr(mod, attr, val)

    return restore


def test_cockpit_composes() -> None:
    done = [{"summary": "byggde X", "link": {"kind": "issue", "ref": "44"}, "type": "bygg", "updated_at": "2026-06-11T16:00:00"}]
    running = [{"summary": "kör triage", "type": "triage", "link": None, "metrics": {}}]
    restore = _patch(
        **{
            "ss.list_sessions": lambda status=None, link_ref=None: done if status == "done" else running,
            "ss.get_active": lambda: {"type": "triage", "session_id": "session-x"},
            "ss.get_focus": lambda: {"kind": "node", "ref": "cns-core"},
            "ss.is_phantom": lambda s: False,
            "ss.elapsed_seconds": lambda s: 125.0,
            "rec.recommend": lambda state=None: [{"type": "bygg", "title": "Bygg quest #8", "motivation": "väntar", "score": 50}],
            "src.open_issues_for_slug": lambda slug: (None, [{"number": 39, "title": "Triage-verktyg"}]),
        }
    )
    try:
        c = data.cockpit_state()
        assert c["last_done"]["summary"] == "byggde X"
        assert c["last_done"]["type"] == "bygg"
        assert len(c["running"]) == 1 and c["running"][0]["type"] == "triage"
        assert c["active"]["type"] == "triage"
        assert len(c["recommendations"]) == 1 and c["recommendations"][0]["type"] == "bygg"
        assert c["focus"]["ref"] == "cns-core" and c["focus"]["kind"] == "node"
        assert c["focus"]["issues"][0]["number"] == 39
    finally:
        restore()


def test_focus_fallback_to_active_link() -> None:
    # Ingen explicit fokus → härled ur aktiva sessionens link.
    restore = _patch(
        **{
            "ss.list_sessions": lambda status=None, link_ref=None: [],
            "ss.get_active": lambda: {"type": "bygg", "session_id": "session-y"},
            "ss.get_focus": lambda: None,
            "ss.get_session": lambda sid: {"link": {"kind": "quest", "ref": "8"}},
            "ss.is_phantom": lambda s: False,
            "ss.elapsed_seconds": lambda s: None,
            "rec.recommend": lambda state=None: [],
            "src.open_issues_for_slug": lambda slug: (None, []),
        }
    )
    try:
        c = data.cockpit_state()
        assert c["focus"]["ref"] == "8" and c["focus"]["kind"] == "quest"
        # quest-fokus → ingen issue-uppslagning (bara node slår open_issues_for_slug)
        assert c["focus"]["issues"] == []
    finally:
        restore()


def test_cockpit_degrades_silently() -> None:
    def boom(*a, **k):
        raise RuntimeError("källa nere")

    restore = _patch(
        **{
            "ss.list_sessions": boom,
            "ss.get_active": boom,
            "ss.get_focus": boom,
            "rec.recommend": boom,
            "src.open_issues_for_slug": boom,
        }
    )
    try:
        c = data.cockpit_state()  # får inte kasta
        assert c["last_done"] is None
        assert c["running"] == []
        assert c["recommendations"] == []
        assert c["focus"] is None
        assert "reachable" in c["freshness"]
    finally:
        restore()


if __name__ == "__main__":
    test_cockpit_composes()
    test_focus_fallback_to_active_link()
    test_cockpit_degrades_silently()
    print("OK — cockpit_state: komposition + fokus-fallback + tyst degradering gröna")
