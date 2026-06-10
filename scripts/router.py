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
#
# MODEL_TIER (modell per aktiv agent) och DEPARTMENT (avdelning per slug) GENERERAS av
# scripts/gen_agentur.py ur agent-frontmatter. Vi importerar dem; faller tillbaka till
# tomma dictar om registret saknas (router är crash-proof och får aldrig dö på import).
try:
    from scripts.agent_registry import MODEL_TIER, DEPARTMENT  # genererad
except Exception:
    MODEL_TIER: dict[str, str] = {}
    DEPARTMENT: dict[str, str] = {}

ROUTING_RULES: list[tuple[str, str, str]] = [
    # Bemanning — aktivera en roster-roll, rekrytering/onboarding (hr-chef äger)
    (
        r"\b(bemanna|bemanning|aktivera (?:roll|agent|en roll)|rekrytera|onboard"
        r"|fyll rollen|g[oö]r rollen k[oö]rbar)\b",
        "hr-chef",
        "bemanning/aktivering av roll",
    ),
    # Org Design — strukturens korrekthet (disciplin vs produktområde, manifest, konsekvens)
    (
        r"\b(org.?struktur|organisationsstruktur|org.?arkitekt|avdelning(?:ar|en)?|chapter"
        r"|sub.?department|roll.?konsekvens|manifest|omorganisera|validate.?org|taxonomi"
        r"|org.?underh[aå]ll|bemanningsbeh|bemanningsmatris|arketyp)\b",
        "org-arkitekt",
        "org-struktur/konsekvens/underhåll",
    ),
    # Agile Coach — team topologies, squads, arbetssätt
    (
        r"\b(team.?topolog|squad|arbetss[aä]tt|ceremoni|hur (?:teamen|vi) jobbar"
        r"|s[aä]tt ihop (?:ett )?team|agile.?coach)\b",
        "agile-coach",
        "team topologies/arbetssätt",
    ),
    # Stabschef — operating model, strategisk koherens
    (
        r"\b(operating model|stabschef|chief of staff|koherens|h[aä]nger ihop"
        r"|hur (?:[aä]r vi|ska vi vara) organiserade|organisationsmodell)\b",
        "stabschef",
        "operating model/koherens",
    ),
    # Ekonomi/kostnad — alltid ekonomichef
    (
        r"\b(kostnad(?:er)?|kostar|token[sr]?|budget|faktur[ae]?|pris|dyr[at]?"
        r"|billig[at]?|estimat|uppskattning|r[aä]kna ut vad|hur mycket)",
        "ekonomichef",
        "kostnadsuppskattning",
    ),
    # Ideas/brainstorming/product
    (
        r"\b(brainstorm|ny? id[eé]|produktid[eé]|vision|product.?owner|roadmap"
        r"|prioriter(?:a|ingar?)|vilka features?|vad ska vi bygga)\b",
        "produktchef",
        "idé/produkt",
    ),
    # Wiki-skrivning
    (
        r"\b(skriv (?:en |upp |till )?wiki|wiki.?sida|dokumentera (?:det|detta|hur)"
        r"|memory.?card|runbook|skapa dokumentation)\b",
        "teknisk-skribent",
        "wiki/dokumentation",
    ),
    # Research/utredning
    (
        r"\b(research|forsk(?:a|ning)|utreda?|unders[oö]k(?:a|ning)?|j[aä]mf[oö]r"
        r"|hitta (?:alternativ|l[oö]sning|open.?source)|rapport om|studera)\b",
        "forskningsledare",
        "research/utredning",
    ),
    # QA — teststrategi, kvalitetsgrindar, testtäckning (qa-lead koordinerar disciplinen)
    (
        r"\b(qa\b|qa.?lead|teststrategi|testt[aä]ckning|testautomation|test.?coverage"
        r"|coverage|kvalitetsgrind|kvalitetss[aä]kr(?:a|ing)|regressionstest|enhetstest"
        r"|e2e.?test|testplan)\b",
        "qa-lead",
        "QA/teststrategi/kvalitetsgrind",
    ),
    # GitHub-operations: PRs, issues, CI, deploy
    (
        r"\b(pull.?request|[oö]ppen pr|granska pr|merg[ae]?|github.?issue|milestone"
        r"|workflow.?run|ci\b|cd\b|github.?actions|deploy(?:a|ment)?|railway|vercel"
        r"|release\b|git push|git merge)\b",
        "devops-ingenjor",
        "GitHub/deploy",
    ),
    # Städning och refaktorering
    (
        r"\b(st[aä]da|rens(?:a|ning)|refaktor(?:era|ering)|dead.?code|cleanup"
        r"|ta bort (?:gammal|oanv[aä]nd|obsolet)|unused import|duplikat|konsolidera)\b",
        "underhallsingenjor",
        "städning/refaktorering",
    ),
    # HR: agent-management, teamstruktur
    (
        r"\b(ny agent|skapa agent|agent.?fil|hr\b|rekryter|teamstruktur"
        r"|agentprofil|agent.?definition|vilka agenter)\b",
        "hr-chef",
        "HR/agenthantering",
    ),
    # Frontend/UI
    (
        r"\b(react|vite|tsx?|tailwind|css\b|styled.?component|ui.?komponent"
        r"|frontend|layout|design.?system|responsiv|dashboard.?komponent)\b",
        "frontend-utvecklare",
        "frontend/UI",
    ),
    # Backend/server/MCP
    (
        r"\b(flask|mcp\b|mcp.?server|mcp.?verktyg|asgi|uvicorn|fastapi"
        r"|server\.py|api.?endpoint|webhook|backend|http.?handler)\b",
        "backend-utvecklare",
        "backend/server/MCP",
    ),
    # Scripts och automation
    (
        r"\b(script(?:et)?|hook(?:en)?|automation|automatisera?|schemalägg"
        r"|cron\b|batch|pipeline\b|dash\.py|agent_host)\b",
        "plattformsingenjor",
        "scripts/automation",
    ),
    # Uppfinnaren — teknisk design och skissning (innan operativ-chef exekverar)
    (
        r"\b(uppfinn(?:a|aren?|ing)|teknisk skiss|designa l[oö]sning|arkitektera"
        r"|hur ska vi bygga|v[aä]lj approach|skissa (?:l[oö]sning|arkitektur|design))\b",
        "losningsarkitekt",
        "teknisk design/skiss",
    ),
    # Planering och orchestration (multi-step, komplex)
    (
        r"\b(planera|sprint|kvartal|q[1-4]\b|orchestr(?:era|ation)|koordinera"
        r"|delegera|parallell|multi.?agent|sessionsplan|vad ska vi g[oö]ra)\b",
        "operativ-chef",
        "planering/orchestration",
    ),
    # Enkla lookups/statuskontroller → lagesanalytiker (Haiku)
    (
        r"\b(visa (?:mig |upp )?(?:[oö]ppna|alla|senaste)|lista (?:issues?|quests?|sessioner|noder|id[eé]er)"
        r"|vad [aä]r [oö]ppet|status p[aå]|hur m[aå]nga|finns det n[aå]gra)\b",
        "lagesanalytiker",
        "enkel lookup/status",
    ),
    # Session-arkitekten — designa session-träd och planera arbetsstruktur
    (
        r"\b(session.?arkitekt|designa sessions?|session.?plan|session.?tr[aä]d"
        r"|planera sessions?|dela upp i sessions?|sessions.?struktur|arkitektera arbete)\b",
        "programledare",
        "session-design/arkitektur",
    ),
    # Dirigenten — sessionkedning och daemon-övervakning
    (
        r"\b(dirig(?:era|enten?)|kedj(?:a|ning)|n[aä]sta session|vakt(?:a|ar)|daemon"
        r"|h[aä]ngande session|sessionskedjning|starta n[aä]sta)\b",
        "sessionskoordinator",
        "sessionskedning/daemon",
    ),
    # Tränaren — förbättra agentdefinitioner och systemprompter
    (
        r"\b(tr[aä]n(?:a|aren?|ing)|f[oö]rb[aä]ttra (?:agent|prompt)|systemsprompt"
        r"|agentprestanda|diagnostisera agent|prompt.?patch|agent.?kvalitet)\b",
        "kompetensutvecklare",
        "agentträning/promptförbättring",
    ),
    # TUI-agent — terminal-cockpit och dash.py
    (
        r"\b(tui\b|dash\.py|terminal.?(?:cockpit|dashboard|[oö]verblick)"
        r"|rich\b.*(?:table|panel|layout)|scripts/tui)\b",
        "terminal-utvecklare",
        "TUI/terminal-dashboard",
    ),
    # Fullstack — när ändringen spänner över både backend och frontend
    (
        r"\b(fullstack|b[aå]de (?:backend och frontend|frontend och backend)"
        r"|hela stacken|api.?(?:och|\\+).?ui|end.?to.?end.?feature)\b",
        "fullstack-utvecklare",
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
    "spec": "definitionsläge — @produktchef sätter vad/varför + acceptanskriterier, @losningsarkitekt skissar hur + risker; ingen kod, output = granskningsbar spec som bygg-passet exekverar mot",
    "bygg": "exekveringsläge — spec först, hela agenturen via operativ-chef, egen branch",
    "triage": "bokföringsläge — resolva/promota/klustra idéer proaktivt, rör ingen kod",
    "review": "granskningsläge — read-first, konvergera slutsatser, fråga före main-merge",
    "verktygsladan": "verktygslådeläge — kalla @hr-chef före ny agent, @kompetensutvecklare för promptförbättring, ingen produktionsdeploy",
    "retro": "retroläge — granska agenturens prestanda (ej produkt); kalla @ekonomichef + @hr-chef + @kompetensutvecklare, read-first, fånga åtgärder som idéer",
}

# Signaler på att prompten hör hemma i en ANNAN sessionstyp än den aktiva.
# Regelbaserat (ingen LLM, inga tokens); Claude bekräftar misstänkt byte med
# väljaren och forkar ett barn-pass — byter aldrig tyst.
TYPE_SIGNALS: dict[str, str] = {
    "bygg": r"\b(nu bygger vi|implementera|skriv koden|b[oö]rja koda|godk[aä]nd spec|k[oö]r p[aå] planen)\b",
    "brainstorm": r"\b(brainstorm|ny id[eé]|t[aä]nka h[oö]gt|spåna|vad ska vi bygga|riktningsfr[aå]ga)\b",
    "spec": r"\b(spec(?:a|ificera|en|.?f[oö]rst)?|definiera kravet|acceptanskriterier|hur ska vi bygga|skissa l[oö]sningen)\b",
    "triage": r"\b(triagera|st[aä]da inkorgen|resolva id[eé]er|rensa id[eé]er|g[aå] igenom id[eé]erna)\b",
    "review": r"\b(granska (?:pr|branch|koden)|konvergera|merga slutsatser|review.?session)\b",
    "verktygsladan": r"\b(verktygsl[aå]d(?:an?)|ny agent|skill|hook|smedjan|agent.?studio|skills.?studio)\b",
    "retro": r"\b(retro|retrospektiv|hur (?:gick|presterade) (?:vi|agenturen)|utv[aä]rdera arbetss[aä]ttet|agenturens prestanda)\b",
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
