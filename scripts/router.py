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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # körbar som fil (hooken anropar absolut sökväg)
    sys.path.insert(0, str(ROOT))

# (mönster, agent-slug, beskrivning) — prioritetsordning, första träff vinner.
# Mer specifika mönster längre upp än generella.
# Tips: `re.search` körs på `.lower()` → alla mönster i lowercase, ingen IGNORECASE-flag nödvändig.
# Modell-tier per agent-slug. Haiku för mekaniska uppgifter, Sonnet för omdöme, Opus för strategi.
MODEL_TIER: dict[str, str] = {
    "ekonomen": "claude-haiku-4-5",
    "ide-agent": "claude-haiku-4-5",
    "github-agent": "claude-haiku-4-5",
    "kontext-agent": "claude-haiku-4-5",
    "wiki-skribent": "claude-sonnet-4-6",
    "research-agent": "claude-sonnet-4-6",
    "backend-agent": "claude-sonnet-4-6",
    "frontend-agent": "claude-sonnet-4-6",
    "scripts-agent": "claude-sonnet-4-6",
    "stadaren": "claude-sonnet-4-6",
    "hr-chefen": "claude-sonnet-4-6",
    "tui-agent": "claude-sonnet-4-6",
    "fullstack-agent": "claude-sonnet-4-6",
    "tranaren": "claude-sonnet-4-6",
    "teamleader": "claude-opus-4-8",
    "dirigenten": "claude-haiku-4-5",
    "session-arkitekten": "claude-sonnet-4-6",
    "uppfinnaren": "claude-sonnet-4-6",
}

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
    # Uppfinnaren — teknisk design och skissning (innan teamleader exekverar)
    (
        r"\b(uppfinn(?:a|aren?|ing)|teknisk skiss|designa l[oö]sning|arkitektera"
        r"|hur ska vi bygga|v[aä]lj approach|skissa (?:l[oö]sning|arkitektur|design))\b",
        "uppfinnaren",
        "teknisk design/skiss",
    ),
    # Planering och orchestration (multi-step, komplex)
    (
        r"\b(planera|sprint|kvartal|q[1-4]\b|orchestr(?:era|ation)|koordinera"
        r"|delegera|parallell|multi.?agent|sessionsplan|vad ska vi g[oö]ra)\b",
        "teamleader",
        "planering/orchestration",
    ),
    # Enkla lookups/statuskontroller → kontext-agent (Haiku)
    (
        r"\b(visa (?:mig |upp )?(?:[oö]ppna|alla|senaste)|lista (?:issues?|quests?|sessioner|noder|id[eé]er)"
        r"|vad [aä]r [oö]ppet|status p[aå]|hur m[aå]nga|finns det n[aå]gra)\b",
        "kontext-agent",
        "enkel lookup/status",
    ),
    # Session-arkitekten — designa session-träd och planera arbetsstruktur
    (
        r"\b(session.?arkitekt|designa sessions?|session.?plan|session.?tr[aä]d"
        r"|planera sessions?|dela upp i sessions?|sessions.?struktur|arkitektera arbete)\b",
        "session-arkitekten",
        "session-design/arkitektur",
    ),
    # Dirigenten — sessionkedning och daemon-övervakning
    (
        r"\b(dirig(?:era|enten?)|kedj(?:a|ning)|n[aä]sta session|vakt(?:a|ar)|daemon"
        r"|h[aä]ngande session|sessionskedjning|starta n[aä]sta)\b",
        "dirigenten",
        "sessionskedning/daemon",
    ),
    # Tränaren — förbättra agentdefinitioner och systemprompter
    (
        r"\b(tr[aä]n(?:a|aren?|ing)|f[oö]rb[aä]ttra (?:agent|prompt)|systemsprompt"
        r"|agentprestanda|diagnostisera agent|prompt.?patch|agent.?kvalitet)\b",
        "tranaren",
        "agentträning/promptförbättring",
    ),
    # TUI-agent — terminal-cockpit och dash.py
    (
        r"\b(tui\b|dash\.py|terminal.?(?:cockpit|dashboard|[oö]verblick)"
        r"|rich\b.*(?:table|panel|layout)|scripts/tui)\b",
        "tui-agent",
        "TUI/terminal-dashboard",
    ),
    # Fullstack — när ändringen spänner över både backend och frontend
    (
        r"\b(fullstack|b[aå]de (?:backend och frontend|frontend och backend)"
        r"|hela stacken|api.?(?:och|\\+).?ui|end.?to.?end.?feature)\b",
        "fullstack-agent",
        "fullstack/hela stacken",
    ),
]

# Prompts kortare än detta är troligen konversationella frågor (tack, ok, ja, etc.)
MIN_PROMPT_LEN = 10

# --- Sessionstyper (profiler i sessions/profiles/<typ>.md) -----------------
# Direktiv som injiceras per prompt när en typ är aktiv (exports/active_session.json,
# satt av /session-skillen). Håller agenturen i rätt läge hela passet.
TYPE_DIRECTIVES: dict[str, str] = {
    "brainstorm": "dialogläge — följdfrågor i text, fånga idéer, exekvera INTE",
    "bygg": "exekveringsläge — spec först, hela agenturen via teamleader, egen branch",
    "triage": "bokföringsläge — resolva/promota/klustra idéer proaktivt, rör ingen kod",
    "review": "granskningsläge — read-first, konvergera slutsatser, fråga före main-merge",
    "verktygsladan": "verktygslådeläge — kalla @hr-chefen före ny agent, @tränaren för promptförbättring, ingen produktionsdeploy",
}

# Signaler på att prompten hör hemma i en ANNAN sessionstyp än den aktiva.
# Regelbaserat (ingen LLM, inga tokens); Claude bekräftar misstänkt byte med
# väljaren och forkar ett barn-pass — byter aldrig tyst.
TYPE_SIGNALS: dict[str, str] = {
    "bygg": r"\b(nu bygger vi|implementera|skriv koden|b[oö]rja koda|godk[aä]nd spec|k[oö]r p[aå] planen)\b",
    "brainstorm": r"\b(brainstorm|ny id[eé]|t[aä]nka h[oö]gt|spåna|vad ska vi bygga|riktningsfr[aå]ga)\b",
    "triage": r"\b(triagera|st[aä]da inkorgen|resolva id[eé]er|rensa id[eé]er|g[aå] igenom id[eé]erna)\b",
    "review": r"\b(granska (?:pr|branch|koden)|konvergera|merga slutsatser|review.?session)\b",
    "verktygsladan": r"\b(verktygsl[aå]d(?:an?)|ny agent|skill|hook|smedjan|agent.?studio|skills.?studio)\b",
}


def _active_type() -> str | None:
    try:
        from scripts.session_store import get_active

        state = get_active()
        return (state or {}).get("type")
    except Exception:
        return None


def session_lines(prompt_lower: str) -> list[str]:
    """[SESSION]-direktiv + ev. typbytes-flagga för aktiv sessionstyp."""
    active = _active_type()
    if not active or active not in TYPE_DIRECTIVES:
        return []
    lines = [f"[SESSION: {active} — {TYPE_DIRECTIVES[active]}]"]
    for other, pattern in TYPE_SIGNALS.items():
        if other != active and re.search(pattern, prompt_lower):
            lines.append(
                f"[SESSION-SKIFTE?] {active} → {other} — bekräfta med väljaren; "
                f"vid ja: markera passet done och forka ett {other}-pass (/session {other})"
            )
            break
    return lines


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
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stdin, "reconfigure"):
            # utf-8-sig: Windows-konsoler defaultar till cp1252 och PowerShell-pipar
            # med BOM \u2014 annars blir payloaden ol\u00e4sbar och hooken tyst.
            sys.stdin.reconfigure(encoding="utf-8-sig")
        raw = sys.stdin.read().lstrip("\ufeff")
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

        for line in session_lines(str(prompt).lower()):
            print(line)

        agent, reason = classify(str(prompt))
        if not agent:
            return

        model = MODEL_TIER.get(agent, "claude-sonnet-4-6")
        print(f"[ROUTING] @{agent} → {reason}")
        print(f"[MODEL: {model}] — spawna subagent med denna modell, kör inte inline i Sonnet")

        # Skriv aktiv routing till sidfil så statusraden kan visa modell + agent
        try:
            routing_file = ROOT / "exports" / "active_routing.json"
            routing_file.parent.mkdir(exist_ok=True)
            routing_file.write_text(
                json.dumps({"model": model, "agent": agent, "reason": reason}),
                encoding="utf-8",
            )
        except Exception:
            pass

    except Exception:
        # Crash-proof: hooken ska aldrig blockera en prompt
        pass


if __name__ == "__main__":
    main()
