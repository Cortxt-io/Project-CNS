"""Tester för intent-renamen (branch-standard) + bakåtkompat-aliaset.

Gamla intent-namn (brainstorm/spec/bygg/verktygsladan) ska kanoniseras till de nya
(discovery/definition/delivery/enablement) på både skriv och läs, så gammal sessionsdata
och gamla markörer fortsätter funka.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from scripts import session_store as ss


def test_canonical_maps_old_to_new():
    assert ss.canonical_session_type("brainstorm") == "discovery"
    assert ss.canonical_session_type("spec") == "definition"
    assert ss.canonical_session_type("bygg") == "delivery"
    assert ss.canonical_session_type("verktygsladan") == "enablement"


def test_canonical_passthrough_and_none():
    # Nya namn + okända lämnas orörda; None → None.
    assert ss.canonical_session_type("discovery") == "discovery"
    assert ss.canonical_session_type("review") == "review"
    assert ss.canonical_session_type(None) is None


def test_valid_session_types_are_the_new_set():
    assert ss.VALID_SESSION_TYPES == {
        "discovery", "definition", "delivery", "triage", "review", "enablement", "retro",
    }


def test_validation_accepts_old_alias_and_stores_canonical():
    with tempfile.TemporaryDirectory() as d:
        ss.SESSIONS_DIR = Path(d)
        # Gammalt namn ska INTE höja (det aliasas), och lagras kanoniskt.
        sess = ss.start_session(link_kind="issue", link_ref="1", session_type="bygg")
        assert sess["type"] == "delivery"


def test_get_active_canonicalizes_old_marker(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "ACTIVE_FILE", tmp_path / "active.json")
    (tmp_path / "active.json").write_text('{"type": "brainstorm", "session_id": "s1"}', encoding="utf-8")
    assert ss.get_active()["type"] == "discovery"
