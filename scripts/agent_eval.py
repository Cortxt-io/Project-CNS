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


# Bakåtstreck som INTE inleder en giltig JSON-escape (\" \\ \/ \b \f \n \r \t \uXXXX).
# Domaren skriver ibland sökvägar (app\tools) eller regex (\s) i fri JSON-text → ogiltig
# escape → json.loads kastar. Vi dubblar dem bara vid parse-fel (giltig JSON rörs ej). (#122)
_INVALID_JSON_ESCAPE = re.compile(r'\\(?![\\"/bfnrtu])')


def _sanitize_json_escapes(s: str) -> str:
    """Dubbla ogiltiga JSON-escape-bakåtstreck så ``json.loads`` inte kastar."""
    return _INVALID_JSON_ESCAPE.sub(r"\\\\", s)


def parse_verdict(judge_text: str) -> dict:
    """Tolka domarens JSON-svar robust (status=error vid otolkbart).

    Domarens fria JSON-text kan innehålla ogiltiga escapes (sökvägar/regex). Vi
    försöker först råparsa; först VID FEL saneras escapes och vi gör ett nytt försök,
    så giltig JSON aldrig rörs. (#122)
    """
    try:
        match = re.search(r"\{.*\}", judge_text, re.S)
        raw = match.group(0) if match else judge_text
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = json.loads(_sanitize_json_escapes(raw))
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
        # Fallback-kedja (#112): API-nyckel → Claude-login/SDK → hoppa. Så eval kan KÖRA
        # utan separat ANTHROPIC_API_KEY (autonom dispatch kör på din Claude Code-login).
        if os.getenv("ANTHROPIC_API_KEY"):
            judge_fn = _default_judge
        elif _sdk_available():
            judge_fn = _sdk_judge
        else:
            return {"status": "skipped", "reason": "ingen domare (API-nyckel/SDK saknas)", "agent": slug}
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


def _sdk_available() -> bool:
    """True om Claude Agent SDK + ``claude``-CLI finns (domaren kan köra på login utan nyckel)."""
    import shutil

    try:
        import claude_agent_sdk  # noqa: F401
    except Exception:
        return False
    return shutil.which("claude") is not None


def _sdk_judge(prompt: str) -> str:
    """LLM-domare via Claude Agent SDK (din Claude Code-login) — INGEN ANTHROPIC_API_KEY.

    Speglar mönstret i ``scripts/tui/agent_host.run_turn``: connect → query → samla
    ``AssistantMessage``/``TextBlock``-text. Read-only domare (inga verktyg). Kör Haiku
    (``JUDGE_MODEL``, Ekonomen-principen). Kastar vid SDK-/CLI-fel → ``evaluate`` fångar
    som ``status=error`` (vilket eval-gaten behandlar som ej-grön → eskalering).
    """
    import asyncio

    async def _run() -> str:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ClaudeSDKClient,
            TextBlock,
        )

        options = ClaudeAgentOptions(
            system_prompt="Du är en STRÄNG evaluator. Svara ENBART med begärd JSON.",
            permission_mode="default",
            model=JUDGE_MODEL,
        )
        client = ClaudeSDKClient(options=options)
        chunks: list[str] = []
        try:
            await client.connect()
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            chunks.append(block.text)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
        return "".join(chunks)

    return asyncio.run(_run())


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
