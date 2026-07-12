"""Control Tower (#43): the dra-loop link derivation + markup helpers.

Pure-function coverage only — the interactive OptionList / start-session flow is
exercised manually in the TUI. Imports textual via scripts.tui.app.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.tui import app  # noqa: E402


def test_rec_link_quest():
    assert app._rec_link({"refs": ["quest #8"]}) == ("quest", "8")


def test_rec_link_issue():
    assert app._rec_link({"refs": ["#39"]}) == ("issue", "39")


def test_rec_link_idea():
    assert app._rec_link({"refs": ["idea-af21a2f0"]}) == ("idea", "idea-af21a2f0")


def test_rec_link_empty_and_unknown():
    assert app._rec_link({"refs": []}) == (None, None)
    assert app._rec_link({}) == (None, None)
    assert app._rec_link({"refs": ["something else"]}) == (None, None)


def test_top_markup_ends_before_actionable_harnast():
    # "Härnäst" header stays (it precedes the OptionList); the recs themselves don't.
    out = app._overview_top_markup({"recommendations": [{"type": "delivery", "title": "X"}]})
    assert "Härnäst" in out
    assert "Var du slutade" in out


def test_focus_markup_empty_safe():
    out = app._overview_focus_markup({})
    assert "I fokus" in out
    assert "Enter startar" in out
