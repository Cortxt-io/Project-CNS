"""Tester för phase_derive — fasen HÄRLEDS ur stegen, den handredigeras inte.

Den bärande regeln: ett steg som inte kan avgöras returnerar None — ALDRIG en gissning.
En härledare som gissar är värre än ingen härledare, för då litar man på den.
"""
from __future__ import annotations

import pytest

from lab.scripts import phase_derive as pd


RECIPE = {
    "phases": [
        {"key": "spec", "title": "Spec", "reached_when": "has_repo", "steps": [
            {"key": "repo", "check": "derived:has_repo"},
            {"key": "kill-criteria", "check": "derived:has_kill_criteria"},
        ], "gate": {"requires": ["repo", "kill-criteria"]}},
        {"key": "mvp", "title": "MVP", "reached_when": "has_tests", "steps": [
            {"key": "core-flow", "check": "manual"},
            {"key": "has-tests", "check": "derived:has_tests"},
        ], "gate": {"requires": ["core-flow", "has-tests"]}},
        {"key": "live", "title": "Live", "reached_when": "has_live_url", "steps": [
            {"key": "own-domain", "check": "derived:has_live_url"},
        ], "gate": {"requires": ["own-domain"]}},
    ]
}


# -- check_step: mätning, aldrig gissning ------------------------------------

def test_derived_step_reads_its_signal():
    step = {"key": "repo", "check": "derived:has_repo"}
    assert pd.check_step(step, signals={"has_repo": True}, checked=set()) is True
    assert pd.check_step(step, signals={"has_repo": False}, checked=set()) is False


def test_unmeasurable_signal_is_unknown_not_false():
    """Signalen saknas → None. Att returnera False vore en lögn: vi VET inte."""
    step = {"key": "repo", "check": "derived:has_repo"}
    assert pd.check_step(step, signals={}, checked=set()) is None


def test_manual_step_reads_the_checkbox():
    step = {"key": "core-flow", "check": "manual"}
    assert pd.check_step(step, signals={}, checked={"core-flow"}) is True
    assert pd.check_step(step, signals={}, checked=set()) is False


def test_unknown_check_language_is_unknown_not_a_crash():
    step = {"key": "x", "check": "sometimes:maybe"}
    assert pd.check_step(step, signals={}, checked=set()) is None


# -- gates -------------------------------------------------------------------

def test_gate_is_open_when_every_required_step_is_green():
    status = {"repo": True, "kill-criteria": True}
    assert pd.gate_open(RECIPE["phases"][0], status) is True


def test_gate_is_shut_when_a_step_is_red():
    status = {"repo": True, "kill-criteria": False}
    assert pd.gate_open(RECIPE["phases"][0], status) is False


def test_unknown_step_does_not_open_a_gate():
    """Okänt är inte grönt. En grind öppnas på bevis, inte på frånvaro av bevis."""
    status = {"repo": True, "kill-criteria": None}
    assert pd.gate_open(RECIPE["phases"][0], status) is False


# -- derive_phase ------------------------------------------------------------

def test_phase_is_where_the_build_provably_reached():
    """Fasen är BEVIS, inte kryss. Har den en live-URL är den live — punkt."""
    signals = {"has_repo": True, "has_tests": True, "has_live_url": True}
    assert pd.derive_phase(RECIPE, signals=signals, checked=set())["phase"] == "live"


def test_first_phase_when_nothing_exists_yet():
    assert pd.derive_phase(RECIPE, signals={"has_repo": False}, checked=set())["phase"] == "spec"


def test_you_can_be_live_without_having_passed_the_gates_behind_you():
    """DIAGNOSEN, inte en bugg: vibe-kodat är precis detta — levererat, aldrig grindat.

    orgkomp ligger i produktion men har ingen marknadskarta. Systemet ska SÄGA det,
    inte låtsas att projektet står kvar i discovery.
    """
    signals = {"has_repo": True, "has_tests": True, "has_live_url": True,
               "has_kill_criteria": False}
    result = pd.derive_phase(RECIPE, signals=signals, checked=set())

    assert result["phase"] == "live"                    # verkligheten vinner över kryssen
    assert "spec" in result["gates_skipped"]            # men skulden syns
    assert "mvp" in result["gates_skipped"]             # core-flow aldrig kryssad


def test_a_clean_run_has_no_skipped_gates():
    signals = {"has_repo": True, "has_kill_criteria": True,
               "has_tests": True, "has_live_url": True}
    result = pd.derive_phase(RECIPE, signals=signals, checked={"core-flow"})
    assert result["gates_skipped"] == []


def test_an_unmeasured_gate_is_not_an_accusation():
    """Vi vet inte om spec-grinden passerades → den hamnar i unknown, inte i skipped.

    Att beskylla någon för att ha hoppat över en grind vi aldrig mätte vore samma lögn
    som att gissa ett steg.
    """
    signals = {"has_repo": True, "has_tests": True, "has_live_url": True}
    # has_kill_criteria saknas helt → spec-grindens krav är OKÄNT, inte rött
    result = pd.derive_phase(RECIPE, signals=signals, checked={"core-flow"})

    assert "spec" in result["gates_unknown"]
    assert "spec" not in result["gates_skipped"]


def test_result_carries_every_step_status_for_the_app():
    signals = {"has_repo": True, "has_kill_criteria": False}
    result = pd.derive_phase(RECIPE, signals=signals, checked=set())
    assert result["steps"]["repo"] is True
    assert result["steps"]["kill-criteria"] is False
    assert result["steps"]["has-tests"] is None      # signalen saknas → okänt


def test_the_open_gate_names_what_is_missing():
    """Appen ska kunna säga VAD som stoppar — inte bara att något gör det."""
    signals = {"has_repo": True, "has_kill_criteria": False}
    result = pd.derive_phase(RECIPE, signals=signals, checked=set())
    assert result["gate"]["phase"] == "spec"
    assert result["gate"]["blocked_by"] == ["kill-criteria"]


# -- motsägelser: härlett vs deklarerat --------------------------------------

def test_stale_gate_decision_against_a_moved_reality_is_flagged():
    """Härledd fas säger live, men grindbeslutet är fyra månader gammalt → titta på det."""
    assert pd.contradiction(phase="live", gate_decision="go", gate_age_days=120) is not None


def test_fresh_gate_decision_is_no_contradiction():
    assert pd.contradiction(phase="live", gate_decision="go", gate_age_days=5) is None


def test_a_killed_venture_that_keeps_shipping_is_the_loudest_contradiction():
    """Grinden sa kill — men verkligheten deployar. Något stämmer inte, och det är inte koden."""
    msg = pd.contradiction(phase="live", gate_decision="kill", gate_age_days=10)
    assert msg is not None and "kill" in msg.lower()
