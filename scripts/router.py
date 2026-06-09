"""UserPromptSubmit hook — klassificerar prompt och injicerar routing-beslut.

Snabb regex-baserad klassificering, ingen LLM, ingen nätverkskall.
Tyst om prompten är för kort (konversationell) eller om ingen regel matchar.
Crash-proof: exit 0 alltid.

Registrering (arbetsytans .claude/settings.json):
  "UserPromptSubmit": [{"hooks": [{"type": "command",
    "command": "python .../router.py", "async": false, "timeout": 5}]}]
"""

from __future__ import annotations

import json
import re
import sys

# (mönster, agent-slug, beskrivning) — prioritetsordning, första träff vinner.
# Mer specifika mönster längre upp än generella.
# Tips: `re.search` körs på `.lower()` → alla mönster i lowercase, ingen IGNORECASE-flag nödvändig.
ROUTING_RULES: list[tuple[str, str, str]] = [
    # Ekonomi/kostnad — alltid ekonomen
    (
        r"\b(kostnad(?:er)?|kostar|token[sr]?|budget|faktur[ae]?|pris|dyr[at]?"
        r"|billig[at]?|estimat|uppskattning|r[aä]kna ut vad|hur mycket)",
        "ekonomen",
        "kostnadsuppskattning",
    ),
    # Ideas/brainstorming/product
    (
        r"\b(brainstorm|ny? id[eé]|produktid[eé]|vision|product.?owner|roadmap"
        r"|prioriter(?:a|ingar?)|vilka features?|vad ska vi bygga)\b",
        "ide-agent",
        "idé/produkt",
    ),
    # Wiki-skrivning
    (
        r"\b(skriv (?:en |upp |till )?wiki|wiki.?sida|dokumentera (?:det|detta|hur)"
        r"|memory.?card|runbook|skapa dokumentation)\b",
        "wiki-skribent",
        "wiki/dokumentation",
    ),
    # Research/utredning
    (
        r"\b(research|forsk(?:a|ning)|utreda?|unders[oö]k(?:a|ning)?|j[aä]mf[oö]r"
        r"|hitta (?:alternativ|l[oö]sning|open.?source)|rapport om|studera)\b",
        "research-agent",
        "research/utredning",
    ),
    # GitHub-operations: PRs, issues, CI, deploy
    (
        r"\b(pull.?request|[oö]ppen pr|granska pr|merg[ae]?|github.?issue|milestone"
        r"|workflow.?run|ci\b|cd\b|github.?actions|deploy(?:a|ment)?|railway|vercel"
        r"|release\b|git push|git merge)\b",
        "github-agent",
        "GitHub/deploy",
    ),
    # Städning och refaktorering
    (
        r"\b(st[aä]da|rens(?:a|ning)|refaktor(?:era|ering)|dead.?code|cleanup"
        r"|ta bort (?:gammal|oanv[aä]nd|obsolet)|unused import|duplikat|konsolidera)\b",
        "stadaren",
        "städning/refaktorering",
    ),
    # HR: agent-management, teamstruktur
    (
        r"\b(ny agent|skapa agent|agent.?fil|hr\b|rekryter|teamstruktur"
        r"|agentprofil|agent.?definition|vilka agenter)\b",
        "hr-chefen",
        "HR/agenthantering",
    ),
    # Frontend/UI
    (
        r"\b(react|vite|tsx?|tailwind|css\b|styled.?component|ui.?komponent"
        r"|frontend|layout|design.?system|responsiv|dashboard.?komponent)\b",
        "frontend-agent",
        "frontend/UI",
    ),
    # Backend/server/MCP
    (
        r"\b(flask|mcp\b|mcp.?server|mcp.?verktyg|asgi|uvicorn|fastapi"
        r"|server\.py|api.?endpoint|webhook|backend|http.?handler)\b",
        "backend-agent",
        "backend/server/MCP",
    ),
    # Scripts och automation
    (
        r"\b(script(?:et)?|hook(?:en)?|automation|automatisera?|schemalägg"
        r"|cron\b|batch|pipeline\b|dash\.py|agent_host)\b",
        "scripts-agent",
        "scripts/automation",
    ),
    # Planering och orchestration (multi-step, komplex)
    (
        r"\b(planera|sprint|kvartal|q[1-4]\b|orchestr(?:era|ation)|koordinera"
        r"|delegera|parallell|multi.?agent|sessionsplan|vad ska vi g[oö]ra)\b",
        "teamleader",
        "planering/orchestration",
    ),
]

# Prompts kortare än detta är troligen konversationella frågor (tack, ok, ja, etc.)
MIN_PROMPT_LEN = 10


def classify(prompt: str) -> tuple[str | None, str | None]:
    stripped = prompt.strip()
    if len(stripped) < MIN_PROMPT_LEN:
        return None, None
    lower = stripped.lower()
    for pattern, agent, reason in ROUTING_RULES:
        if re.search(pattern, lower):
            return agent, reason
    return None, None


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        payload = json.loads(raw)
        prompt: str = (
            payload.get("prompt")
            or payload.get("message")
            or payload.get("userMessage")
            or ""
        )
        if not prompt:
            return

        agent, reason = classify(str(prompt))
        if not agent:
            return

        print(f"[ROUTING] @{agent} → {reason}")

    except Exception:
        # Crash-proof: hooken ska aldrig blockera en prompt
        pass


if __name__ == "__main__":
    main()
