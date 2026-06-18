"""Verifiering av eval-grinden (scripts/agent_eval.py, issue #57).

Pure-delar (parse/build/verdict) + evaluate() med injicerad domare — ingen API.
Körs fristående (``python tests/test_agent_eval.py``) ELLER under pytest.
"""
from __future__ import annotations

import os
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
    assert "## Kontext" not in p  # ingen kontext = ingen kontextsektion


def test_build_eval_prompt_with_context() -> None:
    """#124: dispatch-kontext ramar domaren så processkriterier inte felaktigt failar."""
    p = ae.build_eval_prompt(["A"], "out", context="dispatchern skapar PR efteråt")
    assert "## Kontext" in p and "dispatchern skapar PR efteråt" in p


def test_evaluate_threads_context() -> None:
    """evaluate(context=...) ska skicka kontexten till domaren."""
    seen = {}
    fake = lambda prompt: seen.update(p=prompt) or '{"results":[{"verdict":"pass"}],"total":1}'
    orig = ae.load_eval_criteria
    ae.load_eval_criteria = lambda slug: ["A"]
    try:
        ae.evaluate("x", "out", judge_fn=fake, context="LOOPEN äger PR-skapandet")
        assert "LOOPEN äger PR-skapandet" in seen["p"]
    finally:
        ae.load_eval_criteria = orig


def test_parse_verdict() -> None:
    ok = ae.parse_verdict('{"results":[{"criterion":1,"verdict":"pass"},{"criterion":2,"verdict":"fail"}],"passed":1,"total":2}')
    assert ok["status"] == "ok" and ok["passed"] == 1 and ok["total"] == 2 and ok["all_pass"] is False
    wrapped = ae.parse_verdict('skräp före {"results":[{"verdict":"pass"}],"total":1} skräp efter')
    assert wrapped["all_pass"] is True
    assert ae.parse_verdict("inte json")["status"] == "error"


def test_parse_verdict_invalid_escape() -> None:
    """#122: domar-JSON med ogiltig escape (regex/sökväg) ska saneras, ej bli error."""
    bad = r'{"results":[{"criterion":1,"verdict":"pass","why":"regex \s i app\dir"}],"total":1}'
    r = ae.parse_verdict(bad)
    assert r["status"] == "ok" and r["all_pass"] is True and r["total"] == 1
    # giltig JSON med riktiga escapes rörs inte
    good = ae.parse_verdict('{"results":[{"verdict":"pass","why":"rad1\\nrad2"}],"total":1}')
    assert good["status"] == "ok" and good["all_pass"] is True


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


def test_evaluate_fallback_to_sdk() -> None:
    """#112B: utan ANTHROPIC_API_KEY ska eval falla tillbaka på SDK-domaren (login),
    och bara hoppa om VARKEN nyckel ELLER SDK finns."""
    orig = (ae.load_eval_criteria, ae._sdk_available, ae._sdk_judge)
    saved_key = os.environ.pop("ANTHROPIC_API_KEY", None)
    ae.load_eval_criteria = lambda slug: ["A"]
    try:
        # SDK finns → använd _sdk_judge (ingen nyckel)
        ae._sdk_available = lambda: True
        ae._sdk_judge = lambda p: '{"results":[{"verdict":"pass"}],"total":1}'
        assert ae.evaluate("x", "o")["all_pass"] is True
        # varken nyckel eller SDK → skipped "ingen domare"
        ae._sdk_available = lambda: False
        r = ae.evaluate("x", "o")
        assert r["status"] == "skipped" and "domare" in r["reason"]
    finally:
        ae.load_eval_criteria, ae._sdk_available, ae._sdk_judge = orig
        if saved_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved_key


if __name__ == "__main__":
    test_parse_criteria()
    test_build_eval_prompt()
    test_build_eval_prompt_with_context()
    test_evaluate_threads_context()
    test_parse_verdict()
    test_parse_verdict_invalid_escape()
    test_evaluate_injected_judge()
    test_evaluate_fallback_to_sdk()
    print("OK — agent_eval: alla fall gröna")
