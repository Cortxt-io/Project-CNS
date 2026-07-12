"""Fas-checklistan: den härledda fasen renderad IN i venture-noten.

Fasen härleds — men härledd får inte betyda osynlig. Rikard kan inte se på rak arm vilken fas
något är i, och en sanning ingen ser styr ingenting. Så vi lagrar den inte (det vore en andra
sanning som driver isär) — vi *projicerar* den, mellan markörer, så den kan räknas om utan att
röra prosan runt omkring.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab.scripts.phase_board import BEGIN, END, inject, render_block  # noqa: E402

RECIPE = {
    "phases": [
        {"key": "mvp", "title": "MVP", "steps": [
            {"key": "core-flow", "title": "Kärnflödet funkar", "check": "manual"},
            {"key": "deployed", "title": "Deployad", "check": "derived:has_deploy"},
        ], "gate": {"title": "MVP → Live", "question": "Håller den?"}},
    ]
}

DERIVED = {
    "phase": "mvp",
    "title": "MVP",
    "steps": {"core-flow": False, "deployed": True},
    "gate": {"phase": "mvp", "title": "MVP → Live", "question": "Håller den?",
             "blocked_by": ["core-flow"]},
    "gates_skipped": ["discovery"],
    "gates_unknown": [],
}


def test_the_derived_phase_is_shown_at_a_glance():
    out = render_block(RECIPE, DERIVED, {})
    assert "MVP" in out


def test_a_measured_step_is_ticked_and_a_manual_one_is_a_box():
    """Maskinen mäter det den kan; kryssrutan är där den behöver dina ögon."""
    out = render_block(RECIPE, DERIVED, {})
    assert "- [x] Deployad" in out
    assert "- [ ] Kärnflödet funkar" in out


def test_skipped_gates_are_named_not_hidden():
    """En venture som hoppat över grindar har byggts utan att någon frågat om den borde finnas."""
    out = render_block(RECIPE, DERIVED, {})
    assert "discovery" in out


def test_a_missing_gate_decision_is_called_out():
    out = render_block(RECIPE, DERIVED, {"gate_decision": None})
    assert "gate_decision" in out


def test_a_written_gate_decision_is_shown_instead():
    out = render_block(RECIPE, DERIVED, {"gate_decision": "hold", "gate_date": "2026-07-12"})
    assert "hold" in out


# -- injektion: generera om utan att röra människans prosa ---------------------

def test_the_block_is_appended_when_absent():
    """Blocket bär sina egna markörer (render_block äger dem) — inject bara placerar det."""
    note = "---\ntype: venture\n---\n\n# bkfinans\n\nMin prosa.\n"
    block = f"{BEGIN}\ninnehåll\n{END}"

    out = inject(note, block)

    assert "Min prosa." in out          # människans prosa överlever
    assert BEGIN in out and "innehåll" in out


def test_regenerating_replaces_only_the_block():
    """Prosan runt omkring är människans. Generatorn får aldrig äta den."""
    note = f"# x\n\nFöre.\n\n{BEGIN}\ngammalt\n{END}\n\nEfter.\n"

    out = inject(note, f"{BEGIN}\nnytt\n{END}")

    assert "Före." in out and "Efter." in out
    assert "gammalt" not in out and "nytt" in out
    assert out.count(BEGIN) == 1
