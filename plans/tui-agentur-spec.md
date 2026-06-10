# Spec: TUI-agentur & nodfokuserad Claude

**Status:** utkast för granskning · 2026-06-10
**Beslut från Rikard:** router i agent-hosten + ny TUI-specialistagent · hela node.md som kontext · skrivåtgärder, fylligare nodsidor, snabbkommandon, sessionsstart + rekommendationer från TUI.

## Mål
Göra C-läget i TUI:n till ett riktigt agentur-gränssnitt: nodfokuserade svar med full nodkontext, rätt agentprofil per fråga, skrivåtgärder efter bekräftelse, och möjlighet att starta rekommenderade sessionstyper i nya flikar direkt från TUI:n.

## Delar

### 0. Bugfix: issues config error (förutsättning, liten)
`sources.py:open_issues_for_slug` fallerar med `IssuesConfigError` för att `GITHUB_REPO`/`CNS_GITHUB_TOKEN` inte är satta i TUI:ns process. `Project-CNS/scripts/recommend.py:43-53` har redan en `.env`-läsare.
**Åtgärd:** bryt ut .env-läsningen till en delad helper (eller kopiera mönstret) och anropa den vid TUI-start i `app.py`, innan sources/issues_client används. Felraden i detaljpanelen behålls som graceful degrade.

### 1. Agentur i agent-hosten (router + profiler)
- `agent_host.py` får en **profil-laddare**: läser agentprofiler från `cns-tui/.claude/agents/*.md` (frontmatter + systemprompt-text) och en lättvikts-router med samma nyckelordslogik som `scripts/router.py` — återanvänd routerns nyckelordstabell, importera/extrahera den istället för att duplicera.
- Vald profils text läggs ovanpå `build_seed()`-basen. Default när inget matchar: den nya TUI-specialisten.
- AgentScreen visar vald agent i titeln (t.ex. "🤖 ide-agent · noden foo") så routningen är synlig.

### 2. Ny agent: `tui-agenten` (TUI-specialist)
Ny profil i `cns-tui/.claude/agents/tui-agenten.md`:
- Specialist på Cortxt-nodmodellen *sedd från TUI:n*: svarar nodfokuserat, känner till TUI:ns vyer/tangenter, föreslår nästa åtgärd (idé/issue/session) i termer av vad TUI:n kan göra.
- Defaultagent i C-läget; router skickar vidare till t.ex. ide-agent/wiki-skribent vid tydliga nyckelord.
- **Verifiering enligt guardrail:** kontrollera att filen faktiskt finns på disk efter skapande.

### 3. Full nodkontext i seeden
`build_seed(slug)` utökas: läs hela `nodes/<slug>/node.md` (frontmatter + sektioner, via befintlig parser i datalagret) + öppna idéer + öppna issues in i systemprompten. Verktygen behålls så Claude kan slå upp grannar (`part_of`/`feeds`/`depends_on`) vid jämförande frågor.
Storleksgräns: trunkera sektioner > ~2k tecken per sektion med markering, så seeden inte sväller.

### 4. Skrivåtgärder med bekräftelse
- `can_use_tool()`-callbacken öppnas selektivt: skrivverktyg (`capture_idea`, `create_issue`, `add_todo`, uppdatera nodsektion) tillåts **efter bekräftelse i UI:t** — AgentScreen visar "Claude vill: skapa idé '…' — [J]a/[N]ej".
- Nya MCP-verktyg i `build_cns_server()` som wrappa befintliga datalager-funktioner (scripts/-lagret, inte heta cns.py — enligt etablerad isolering).
- Skrivningar som rör node.md går via samma väg som övrig AI-skrivning (GitHub API-vägen är backendens ansvar; lokalt i TUI:n skriver vi till arbetskopian och visar git-status). **Öppen fråga 1 nedan.**

### 5. Fylligare nodsidor
- Detaljpanelen får en sektion "Innehåll" som visar nodens faktiska node.md-sektioner (rubriker + första stycke) — ren rendering, ingen AI, löser "tunna nodsidor" direkt.
- Tangent **`B`** ("berika"): tui-agenten genererar en sammanfattning av noden (innehåll, aktivitet, relationer, luckor) som visas i panelen och cachas per nod under sessionen.

### 6. Snabbkommandon på nod
I AgentScreen: siffertangenter/lista med fördefinierade prompts innan man skriver fritt:
`1` Sammanfatta noden · `2` Vad är nästa steg? · `3` Hitta luckor · `4` Föreslå idéer.
Definieras som konstanter, lätta att utöka.

### 7. Sessionsstart + rekommendationer från TUI
- Tangent **`S`**: öppnar `SessionScreen` som kör `recommend.py --json` och listar rekommendationer (typ, titel, motivation) + de fyra sessionstyperna som manuellt val.
- Enter på ett val startar ny Windows Terminal-flik enligt /flik-mönstret:
  `Start-Process wt -ArgumentList '-w 0 nt -d "<rätt mapp>" powershell -NoExit -ExecutionPolicy Bypass -Command claude "/session <typ>"'`
  Mapp väljs per sessionstyp (bygg → rätt worktree, triage/brainstorm → Project-CNS). **Öppen fråga 2.**
- Statusraden i TUI:n visar topp-rekommendationen ("Rek: triage — 29 idéer i inkorgen") via `recommend.py --statusline`, uppdaterad vid start + refresh.

## Beslut (Rikard 2026-06-10)
1. **Nodskrivningar:** lokalt + push via GitHub API-vägen (git_ops-mönstret), efter extra bekräftelse.
2. **Permission-läge för flik-sessioner:** alltid default — Rikard togglar själv.
3. **Router:** egen liten tabell — tui-agenten default + 3–4 utvalda (ide-agent, wiki-skribent, github-agent).

## Etappindelning (förslag)
- **Etapp A (snabb nytta):** 0 + 3 + 5a (innehållssektion) + 6
- **Etapp B:** 1 + 2 (agentur + tui-agenten)
- **Etapp C:** 4 (skrivåtgärder)
- **Etapp D:** 7 (sessioner + rekommendationer)
