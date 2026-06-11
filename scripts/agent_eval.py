"""Eval-grind (issue #57): bedöm en sessions OUTPUT mot agentens Eval-kriterier.

Kompletterar ``validate_agent.py`` (som validerar agentfilens STRUKTUR) — detta
bedömer KVALITETEN på vad agenten faktiskt producerade, via en LLM-domare. Det är
fundamentet för tillit före autonomi (research: bygg evals FÖRE autonomi).

Plan A-tooling: läser ``.claude/agents`` precis som validate_agent/gen_agentur.
Produktkod (``app/``) importerar aldrig detta. Domaren körs på Haiku (mekanisk
bedömning, Ekonomen-principen) och är injicerbar så logiken kan testas utan API.

Kör: ``python scripts/agent_eval.py <agent-slug>`` med sessionens output på stdin.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / ".claude" / "agents"
ROSTER_DIR = ROOT / ".claude" / "org" / "roster"

JUDGE_MODEL = "claude-haiku-4-5"


def _agent_file(slug: str) -> Path | None:
    for d in (AGENTS_DIR, ROSTER_DIR):
        p = d / f"{slug}.md"
        if p.exists():
            return p
    return None


def _parse_criteria(text: str) -> list[str]:
    """Plocka '- '-rader under '## Eval-kriterier' fram till nästa '## '."""
    out: list[str] = []
    in_section = False
    for line in text.splitlines():
        if re.match(r"^##\s+Eval-kriterier", line.strip()):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.strip().startswith("- "):
            out.append(line.strip()[2:].strip())
    return out


def load_eval_criteria(slug: str) -> list[str]:
    """Bullet-kriterierna ur agentens '## Eval-kriterier'-sektion ([] om saknas)."""
    p = _agent_file(slug)
    return _parse_criteria(p.read_text(encoding="utf-8")) if p else []


def build_eval_prompt(criteria: list[str], session_output: str) -> str:
    """Domar-prompt: bedöm output mot varje kriterium, svara strukturerat (JSON)."""
    crit = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(criteria))
    return (
        "Du är en STRÄNG evaluator. Bedöm om arbetspassets OUTPUT uppfyller varje "
        "eval-kriterium. Var skeptisk; default till \"fail\" vid tvivel.\n\n"
        f"## Eval-kriterier\n{crit}\n\n"
        f"## Output att bedöma\n{session_output}\n\n"
        'Svara ENBART med JSON: {"results":[{"criterion":<n>,"verdict":"pass|fail",'
        '"why":"..."}],"passed":<antal pass>,"total":<antal kriterier>}'
    )


def parse_verdict(judge_text: str) -> dict:
    """Tolka domarens JSON-svar robust (status=error vid otolkbart)."""
    try:
        match = re.search(r"\{.*\}", judge_text, re.S)
        data = json.loads(match.group(0) if match else judge_text)
        results = data.get("results", [])
        passed = sum(1 for r in results if r.get("verdict") == "pass")
        total = len(results) or int(data.get("total", 0))
        return {
            "status": "ok",
            "passed": passed,
            "total": total,
            "all_pass": total > 0 and passed == total,
            "results": results,
        }
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}


def evaluate(
    slug: str,
    session_output: str,
    *,
    judge_fn: Callable[[str], str] | None = None,
) -> dict:
    """Kör eval-grinden: ladda kriterier → domar-prompt → bedöm → tolka.

    ``judge_fn(prompt) -> str`` injiceras (default = riktig Haiku-domare). Returnerar
    ``status=skipped`` om inga kriterier finns eller ingen domare/API-nyckel.
    """
    criteria = load_eval_criteria(slug)
    if not criteria:
        return {"status": "skipped", "reason": f"inga eval-kriterier för {slug}", "agent": slug}
    if judge_fn is None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            return {"status": "skipped", "reason": "ANTHROPIC_API_KEY saknas", "agent": slug}
        judge_fn = _default_judge
    try:
        verdict = parse_verdict(judge_fn(build_eval_prompt(criteria, session_output)))
    except Exception as exc:
        return {"status": "error", "reason": str(exc), "agent": slug}
    return {**verdict, "agent": slug, "criteria": criteria}


def _default_judge(prompt: str) -> str:
    """Riktig LLM-domare via Anthropic (Haiku). Kastar om nyckel/paket saknas."""
    import anthropic  # lazy — valfritt beroende

    resp = anthropic.Anthropic().messages.create(
        model=JUDGE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not argv:
        print("Användning: python scripts/agent_eval.py <agent-slug>  (output på stdin)")
        return 2
    output = sys.stdin.read() if not sys.stdin.isatty() else ""
    result = evaluate(argv[0], output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
