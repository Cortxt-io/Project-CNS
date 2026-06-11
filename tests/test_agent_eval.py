"""Verifiering av eval-grinden (scripts/agent_eval.py, issue #57).

Pure-delar (parse/build/verdict) + evaluate() med injicerad domare — ingen API.
Körs fristående (``python tests/test_agent_eval.py``) ELLER under pytest.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import agent_eval as ae  # noqa: E402

SAMPLE = """---
name: x
---
# X

## Eval-kriterier
- Presenterar alltid routing-motiveringen
- Eskalerar bara genuint strategiska beslut

## Nästa sektion
- inte ett kriterium
"""


def test_parse_criteria() -> None:
    assert ae._parse_criteria(SAMPLE) == [
        "Presenterar alltid routing-motiveringen",
        "Eskalerar bara genuint strategiska beslut",
    ]
    assert ae._parse_criteria("# Ingen sektion alls") == []


def test_build_eval_prompt() -> None:
    p = ae.build_eval_prompt(["A", "B"], "min output")
    assert "1. A" in p and "2. B" in p and "min output" in p and "JSON" in p


def test_parse_verdict() -> None:
    ok = ae.parse_verdict('{"results":[{"criterion":1,"verdict":"pass"},{"criterion":2,"verdict":"fail"}],"passed":1,"total":2}')
    assert ok["status"] == "ok" and ok["passed"] == 1 and ok["total"] == 2 and ok["all_pass"] is False
    wrapped = ae.parse_verdict('skräp före {"results":[{"verdict":"pass"}],"total":1} skräp efter')
    assert wrapped["all_pass"] is True
    assert ae.parse_verdict("inte json")["status"] == "error"


def test_evaluate_injected_judge() -> None:
    fake = lambda _p: '{"results":[{"criterion":1,"verdict":"pass"},{"criterion":2,"verdict":"pass"}],"passed":2,"total":2}'
    orig = ae.load_eval_criteria
    ae.load_eval_criteria = lambda slug: ["A", "B"]   # isolera från .claude/agents
    try:
        r = ae.evaluate("x", "output", judge_fn=fake)
        assert r["status"] == "ok" and r["all_pass"] is True and r["agent"] == "x"
        ae.load_eval_criteria = lambda slug: []        # inga kriterier → skip
        assert ae.evaluate("x", "o", judge_fn=fake)["status"] == "skipped"
    finally:
        ae.load_eval_criteria = orig


if __name__ == "__main__":
    test_parse_criteria()
    test_build_eval_prompt()
    test_parse_verdict()
    test_evaluate_injected_judge()
    print("OK — agent_eval: alla fall gröna")
