"""Tester för C1-härledningen: matriscell → families, override-union, fallback."""
from __future__ import annotations

from scripts import tool_families as tf

_MATRIS = {
    "cells": {
        "Engineering|ic": {"tool_families": ["issues", "prs"]},
        "Engineering|lead": {"tool_families": ["issues", "prs", "actions"]},
        "Produkt|lead": {"tool_families": ["ideas", "issues", "quests"]},
        "Ledning|exec": {"tool_families": ["sessions", "quests", "projects"]},
    }
}


def test_derive_level():
    assert tf.derive_level({"department": "Ledning"}) == "exec"
    assert tf.derive_level({"department": "Engineering", "lead": True}) == "lead"
    assert tf.derive_level({"department": "Engineering", "lead": False}) == "ic"
    assert tf.derive_level({"department": "Engineering"}) == "ic"


def test_families_for_cell():
    assert tf.families_for_cell("Engineering", "ic", _MATRIS) == ["issues", "prs"]
    assert tf.families_for_cell("Saknas", "ic", _MATRIS) == []


_BASE = list(tf.BASELINE_FAMILIES)  # ("sessions", "ideas") — universell, prependas alltid


def test_baseline_families_always_present():
    # Tom roll utan cell → bara baslinjen
    assert tf.effective_tools({"department": "Okänd", "tools_override": []}, matris=_MATRIS) == _BASE


def test_effective_tools_unions_baseline_cell_and_override():
    role = {"department": "Engineering", "lead": False, "tools_override": ["cortxt_create_issue", "mcp__github__x"]}
    out = tf.effective_tools(role, matris=_MATRIS)
    # baslinje först, sedan cellens families, sedan override; dubbletter bort
    assert out == _BASE + ["issues", "prs", "cortxt_create_issue", "mcp__github__x"]


def test_effective_tools_dedupes():
    # 'ideas' (baslinje) + 'issues' (cell) ska inte dubbleras av override
    role = {"department": "Produkt", "lead": True, "tools_override": ["issues", "ideas", "cortxt_capture_idea"]}
    out = tf.effective_tools(role, matris=_MATRIS)
    assert out == _BASE + ["issues", "quests", "cortxt_capture_idea"]


def test_missing_cell_falls_back_to_baseline_plus_override():
    role = {"department": "Okänd", "lead": False, "tools_override": ["cortxt_get_issue"]}
    assert tf.effective_tools(role, matris=_MATRIS) == _BASE + ["cortxt_get_issue"]


def test_exec_uses_ledning_cell():
    role = {"department": "Ledning", "tools_override": []}
    assert tf.effective_tools(role, matris=_MATRIS) == _BASE + ["quests", "projects"]
