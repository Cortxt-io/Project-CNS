# MCP-router & agent-verktygsåtkomst

**Status:** beslutad 2026-06-12 · config-router-skivan landad, gateway deferrad
**Berör:** `scripts/mcp_router.py`, `config/mcp_servers.json`, `scripts/tui/agent_host.py`,
noderna `cns-mcp` och `mcp-gateway`.

## Problem

Agenturens agenter får sina verktyg via Claude Agent SDK i `scripts/tui/agent_host.py`.
Tidigare monterade `build_options` en **hårdkodad** serveruppsättning — bara den in-process
CNS-servern (+ ev. web) — och `allowed_tools` var en fast lista. Rollens `## Tillåtna verktyg`
*parsades* (`agent_roles._parse_tools`) men styrde aldrig vilka servrar/verktyg agenten fick.
Följd: en agent kunde aldrig nå en **extern** MCP-server (GitHub-MCP m.fl.), oavsett roll.

Det blir en blockerare när vi börjar konsumera ekosystemets MCP-servrar. I dag använder
agenturen handrullade verktygslager (CNS:s egna GitHub-REST-klienter); när GitHub-MCP m.fl.
kommer in behöver olika agenter olika serveruppsättningar. Det fanns ingen mekanism för det.

## Tre lager (skilj dem åt)

1. **CNS-som-server** (`app/mcp_server.py`, 19 `cortxt_*`-verktyg på Railway). De handrullade
   GitHub-klienterna (`issues_client`, `prs_client`, `git_ops`, `gh_projects`, `actions`,
   `wiki`) bor här. De kodar CNS:s **egen arbetsmodell** (issues-som-quests m.m.) — de är inte
   bara "obsoleta GitHub-wrappers" och byts inte ut rakt av.
2. **Agenter-som-klienter** (`agent_host.py`). Här satt luckan. Här bor routern nu.
3. **Routern** — avgör vilka MCP-servrar + verktyg ett pass får.

Obsolescensen Rikard pekade på gäller **agent-åtkomst** (lager 2), inte server-interna (lager 1).

## Beslut

### Seamet är rollens `## Tillåtna verktyg`
Routern utgår från rollens deklarerade verktyg — **inte** från nodfilformen eller hårdkodade
listor. Rollmodellen är det stabila gränssnittet; CNS-datamodellen kan byggas om utan att röra
routningen. (Samma princip som `role_for_node`-seamet i dispatch-loopen.)

### Routern växer i två steg
- **(a) Config-router — NU.** Ett serverregister (`config/mcp_servers.json`) + per-pass-montering
  i `scripts/mcp_router.py:resolve()`. För varje server i registret: montera den om den är
  `always` (baseline: `cns`, `web`) eller om någon av rollens verktyg matchar dess `provides`-
  prefix. In-process-servrar (`sdk`-kind) byggs via injicerade builders (håller modulen SDK-fri
  och testbar); externa servrar (`stdio`/`http`) byggs ur env och **hoppas tyst över med en
  warning om de inte är konfigurerade** (fail-open — ett saknat GitHub-MCP får aldrig stjälpa
  ett pass som klarar sig på CNS-verktygen). `.mcp.json` förblir routern för *externa* klienter
  (Claude Code mot Railway); `mcp_router` är routern för *agenturens egna lokala pass*.
- **(b) Gateway-process — SENARE.** Den inritade `mcp-gateway`-noden (`depends_on: cns-mcp`)
  byggs som en separat proxy framför många uppströmsservrar, med central auth + allowlist, när
  Plan B-agenter når många servrar. Designas som spike; byggs inte nu. Tills dess är
  config-routern tillräcklig.

### CNS:s GitHub-klienter rivs inte
Agent-pass pekas **gradvis** mot GitHub-MCP där det är bättre än det handrullade. Server-interna
(lager 1) migreras separat och först när det bevisat lönar sig — inte som en del av router-bygget.

## Konsekvens / verifierat

- `resolve(role_for_node('cns-mcp')['tools'])` monterar `github` (med `GITHUB_MCP_COMMAND`/
  `GITHUB_MCP_URL` satt); backend-rollen får det inte. `cns` är alltid med; läsverktyg är baseline.
- Rollösa pass faller tillbaka på CNS-verktygen (bakåtkompatibelt).
- `tests/test_mcp_router.py` täcker monteringen, fail-open och fallbacken (ren, ingen SDK).

## Registret (fler servrar) + diagnostik

`config/mcp_servers.json` listar servrarna agenturen KAN nå. Utöver baseline `cns`/`web` finns
externa, env-gatade servrar — i dag `github` (stdio/http), `vercel` (http), `railway` (http).
Varje server bär en **`capability`**-token (Del B): en agent vars kapabilitet matchar serverns
`provides`-prefix får den monterad. Lägg till en ny server = en post här, ingen kod.

**Diagnostik:** `cns mcp-servers` listar alla servrar + om de är konfigurerade (env satt) och vad
som saknas. `sdk`-servrar är alltid tillgängliga (in-process); externa gatas på env, fail-open.

## Env per extern server (secrets i `.env`/`gh secret`, aldrig i klartext)

| Server | URL (http) | eller binär (stdio) | Token |
|--------|------------|---------------------|-------|
| `github` | `GITHUB_MCP_URL` | `GITHUB_MCP_COMMAND` | `GITHUB_MCP_TOKEN` (→ `GITHUB_PERSONAL_ACCESS_TOKEN` i stdio) |
| `vercel` | `VERCEL_MCP_URL` | — | `VERCEL_MCP_TOKEN` |
| `railway` | `RAILWAY_MCP_URL` | — | `RAILWAY_MCP_TOKEN` |

Token skickas som `Authorization: Bearer …` för http-servrar. När en servers env är satt monterar
routern den automatiskt för agenter med matchande kapabilitet — annars hoppas den tyst över.

> **`.mcp.json` (vad Claude Code/”vi” når) vs `config/mcp_servers.json` (vad agenturen når):** två
> skilda routrar. För att ge den interaktiva sessionen åtkomst till en extern server läggs den i
> `.mcp.json`; för att ge *agenturens pass* åtkomst räcker registret + env ovan.

## Vidare arbete (epic "MCP-router & agent-verktygsåtkomst")

1. ~~Config-router + register + build_options-rewire + tester~~ (denna skiva).
2. Koppla en riktig GitHub-MCP (stdio-binär eller remote) + env-secret-flöde + live-pass.
3. Bemanna fler discipliner så routningsmålen finns (per-roll verktygsåtkomst i bredd).
4. `mcp-gateway`-processen: design-spike (Plan B, central auth/allowlist/proxy + Anthropics progressive disclosure).
5. Gradvis migrering av agent-pass till GitHub-MCP där det slår handrullat.

## Tillägg 2026-06-13 — verktygskonsolidering + C1-härledning

**Problemet bakom problemet:** routern fungerade, men (a) agenturens lokala universum
implementerade bara 4 läs-verktyg medan rollerna deklarerade rika `cortxt_*` som bara fanns
på Railway, och (b) de 46 connector-verktygen var granulära (research: prestanda faller
skarpt >~20 verktyg/pass; de flesta MCP-servrar har ≤4). Rikard valde att konsolidera **båda**
universum.

**Beslut:**
- **10 feta verktyg** (`cortxt_<domän>` med `action`-param) ersätter 46 granulära, i båda
  universum. **Enkälla = `scripts/tools/registry.py`** (taxonomi); logik transport-fritt i
  `scripts/tools/<domän>_core.py`. Lagret bor i `scripts/` så server + lokala pass importerar
  nedåt (ingen `scripts→app`-koppling för kärnan).
- **Bakåtkompat (Fas α/β/γ):** de 43 gamla namnen lever som alias (`app/tools/_aliases.py`,
  bevarad signatur → samma kärna) så claude.ai-connectorn inte bryts. Sunset (ta bort
  `register_aliases`) när användningen tystnat.
- **Read-first flyttar till action-nivå:** ett fett verktyg blandar läs/skriv per action, så
  `agent_host._deny_unlisted` grindar på `tool_input["action"]` mot `registry`-läs-actions.
- **Routern symmetrisk:** sdk-grenen översätter rollens tokens → lokala feta namn via
  `sdk_role_resolver`+`registry.local_names_for`; baseline = läs-kärna (`project`/`issue`/`idea`).
- **C1 — slut på manuellt:** `scripts/tool_families.py:effective_tools` härleder rollens verktyg
  ur `bemanning_matris.json` (cell `tool_families` via `(department, nivå)`); `## Tillåtna verktyg`
  blir override. Ny roll i en bemannad cell ärver verktyg utan handlistning.

**Öppet (kvar):** `gh_projects`/`leases`/`linear` saknas som families i matrisen → override-only
tills cellerna ev. utökas. Verifierat: `tests/test_tool_core.py`, `test_tool_aliases.py`,
`test_tool_families.py`, `test_agent_host_tools.py`, utökad `test_mcp_router.py` (159 gröna).

> **Arkitektavvikelse från specen:** kärnan lades i `scripts/tools/` (inte `app/tools/core/`)
> för att hålla importriktningen nedåt — både `app/` och `scripts/tui/agent_host` delar den.
