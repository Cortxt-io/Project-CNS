"""Verifiering av agent-guardrails (scripts/agent_guardrails.py, issue #60).

Ren logik — ingen agent-host/SDK behövs. Körs fristående
(``python tests/test_agent_guardrails.py``) ELLER under pytest.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.agent_guardrails import Guardrails  # noqa: E402


def test_repeat_block() -> None:
    g = Guardrails(max_turns=100, token_budget=10**9, max_repeats=3)
    for _ in range(3):
        assert g.check("Read", {"f": "x"})[0] is True       # 3 identiska tillåts
    allow, reason = g.check("Read", {"f": "x"})              # 4:e nekas
    assert allow is False and "upprepat" in reason
    # Annat anrop påverkas inte:
    assert g.check("Read", {"f": "annat"})[0] is True


def test_turn_cap() -> None:
    g = Guardrails(max_turns=2, token_budget=10**9, max_repeats=100)
    assert g.check("a")[0] is True
    assert g.check("b")[0] is True
    allow, reason = g.check("c")
    assert allow is False and "turn" in reason


def test_token_cap() -> None:
    g = Guardrails(max_turns=100, token_budget=100, max_repeats=100)
    assert g.check("a", tokens=60)[0] is True
    allow, reason = g.check("b", tokens=50)                  # 110 > 100
    assert allow is False and "token" in reason


def test_allow_and_snapshot() -> None:
    g = Guardrails()
    assert g.check("a", {"x": 1}, tokens=10)[0] is True
    assert g.check("b", tokens=5)[0] is True
    assert g.snapshot() == {"turns": 2, "tokens": 15, "distinct_calls": 2}


if __name__ == "__main__":
    test_repeat_block()
    test_turn_cap()
    test_token_cap()
    test_allow_and_snapshot()
    print("OK — agent_guardrails: alla fall gröna")
