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

## Env för extern server (GitHub-MCP)

`config/mcp_servers.json` → `github`: sätt **antingen** `GITHUB_MCP_COMMAND` (lokal stdio-binär,
t.ex. `github-mcp-server`) **eller** `GITHUB_MCP_URL` (fjärr-http). Token via `GITHUB_MCP_TOKEN`
(skickas som `Authorization: Bearer …` för http, eller som `GITHUB_PERSONAL_ACCESS_TOKEN` i
stdio-env). Secrets läggs i `.env`/`gh secret`, aldrig i klartext.

## Vidare arbete (epic "MCP-router & agent-verktygsåtkomst")

1. ~~Config-router + register + build_options-rewire + tester~~ (denna skiva).
2. Koppla en riktig GitHub-MCP (stdio-binär eller remote) + env-secret-flöde + live-pass.
3. Bemanna fler discipliner så routningsmålen finns (per-roll verktygsåtkomst i bredd).
4. `mcp-gateway`-processen: design-spike (Plan B, central auth/allowlist/proxy).
5. Gradvis migrering av agent-pass till GitHub-MCP där det slår handrullat.
