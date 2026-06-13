# Spec: Agenturens verktygsåtkomst — stäng universum-B-luckan

**Status:** utkast för granskning · 2026-06-13 · ingen kod skriven
**Berör:** `scripts/tui/agent_host.py`, `scripts/mcp_router.py`, `config/mcp_servers.json`,
`scripts/agent_roles.py`, `.claude/agents/*.md`, `.claude/org/bemanning_matris.json`
**Föregås av:** `decisions/mcp-router.md` (config-routern), `plans/agentur-routing-spec.md`

> Spec-först (arbetsregel): öppna frågor ligger som **[FRÅGA n]** och måste besvaras
> innan implementation. Inget byggs förrän Rikard kvitterar.

---

## 1. Problemet, sant formulerat

Agenturens agenter har **två skilda verktygsuniversum** och kör på det lilla:

| | Universum A (externt) | Universum B (agenturens lokala pass) |
|---|---|---|
| **Vem** | Rikard + Claude Code via `.mcp.json` → Railway | dispatch-loop + `agent_host` (in-process SDK) |
| **Verktyg** | hela `cortxt_*`-sviten (~50): issues, PR, quests, wiki, idéer, sessioner, workflows | **4 läs-verktyg**: `list_nodes`, `get_node`, `list_ideas`, `list_open_issues` |
| **Var** | `app/tools/*` (FastMCP `@mcp.tool`) | `agent_host._build_cns_tools` (SDK `@tool`) |
| **Skriva** | ja (server-token) | nej (read-first; `Write/Edit/Bash` bara i skrivläge) |

**Luckan:** rollerna deklarerar redan rika verktyg i `## Tillåtna verktyg`
(backend-utvecklaren: `cortxt_create_issue`, `cortxt_create_pr`, …; produktchefen:
`cortxt_capture_idea`, `cortxt_promote_idea_to_issue`, …). Men universum B
**implementerar dem inte** — de mappar mot ingenting lokalt. En lokal agent som
"får" skapa en issue kan ändå inte, för verktyget finns bara på Railway.

Detta är inte ett rollfyllnadsproblem (rollerna är ifyllda, 0 `TODO` kvar). Det är
ett **implementations- och namnglappsproblem** i universum B.

### Vad som INTE är problemet (avgränsning)
- Routern fungerar (`resolve()` monterar per roll, fail-open, testad).
- Rollerna är ifyllda och refererar matriscell-baslinje.
- `bemanning_matris.json` har redan `tool_families` per cell (19 celler).
- GitHub/Redis-ryggraden och `.mcp.json` (universum A) rörs inte.

---

## 2. Tre namnytor som inte stämmer överens

Samma logiska verktyg heter olika på tre ställen — det måste förenas:

| Yta | Namn på "skapa issue" |
|-----|----------------------|
| Rollens `## Tillåtna verktyg` | `cortxt_create_issue` (bart) |
| Universum A (Railway via `.mcp.json`) | `mcp__project-cns__cortxt_create_issue` |
| Universum B (lokal in-process) | `mcp__cns__create_issue` (om wire:at) |

Routern matchar rollens bara namn mot `provides`-prefix (`cns`-servern provider
`["mcp__cns__", "cortxt_"]`), så **prefix-matchningen funkar redan** för båda. Men
`allowed_tools` som skickas till SDK:n måste vara det **faktiska exponerade namnet**
(`mcp__cns__<tool>`), och idag lägger `resolve()` bara på de 4 hårdkodade
`CNS_TOOL_NAMES` — inte rollens deklarerade verktyg. **[FRÅGA 1]** nedan löser detta.

---

## 3. Designval (de enda manuella besluten kvar)

### Val A — Hur når universum B de rika verktygen?

Tre vägar (din tidigare fråga, nu i exakt form):

1. **Wire:a in en kurerad delmängd lokalt** (re-wrappa `scripts/`-datalager som
   SDK `@tool`, precis som de 4 befintliga). Ingen OAuth, ingen nätverkshopp,
   read-first-grindarna gäller. Mest i linje med befintligt mönster.
2. **Spegla hela sviten** lokalt (~50 wrappers). Maximal kapacitet, men dubbel
   underhållsbörda (varje verktyg finns då i `app/tools/` *och* `agent_host`) och
   större kontext/attackyta per pass.
3. **Peka lokala agenter mot Railway-MCP** via routern (`cortxt` som `http`-server i
   `config/mcp_servers.json` mot `/mcp`). Universum A och B konvergerar — en koppling
   i stället för N wrappers. Men kräver OAuth-token-flöde lokalt och nätverksberoende
   i varje pass (bryter "lokalt-först" för agenturen).

> **Rekommendation:** **Väg 1** (kurerad lokal delmängd). Den matchar det bevisade
> mönstret, undviker OAuth, behåller agenturen lokalt-först, och du betalar bara för
> de verktyg agenterna faktiskt behöver. Väg 3 är rätt *senare*, som en del av
> `mcp-gateway`-noden — inte nu.

**[FRÅGA A]** Godkänner du väg 1, eller vill du ha väg 3 direkt?

### Val B — Vilken kurerad delmängd? (om väg 1)

Kandidat-baslinje, härledd ur vad rollerna redan deklarerar + read-first-principen:

**Läs (säkra, alla roller):** `list_nodes`, `get_node`, `list_ideas`,
`list_open_issues`, `get_issue`, `list_quests`, `get_quest`, `list_prs`, `get_pr`,
`list_wiki_pages`, `read_wiki_page` *(de 4 första finns redan)*

**Skriv/handling (bakom skrivläge + roll-gate):** `create_issue`, `close_issue`,
`add_todo`, `check_todo`, `capture_idea`, `promote_idea_to_issue`, `create_pr`,
`set_pr_reviewers`, `start_session`, `mark_session_done`, `write_wiki_page`

**[FRÅGA B]** Är den här delmängden rätt? För smal / för bred? Något att stryka?

### Val C — Avskaffa manuell tilldelning (din kärnfråga: "tilldela manuellt hela tiden?")

Rollerna är ifyllda för hand idag. För att slippa underhålla 27 listor framåt finns
ett **härlednings-seam** redan halvbyggt:

```
Roll (.md frontmatter: department + sub_department + lead)
   │  nivå härleds: exec=Ledning · lead=lead:true · ic=övriga (matrisens egen regel)
   ▼
bemanning_matris.cells[department|nivå].tool_families   ← REDAN ifylld (19 celler)
   │  family → verktygsnamn (NY liten mappningstabell, en gång)
   ▼
rollens effektiva verktyg (baslinje)  +  ev. per-roll-override i .md
   ▼
routern monterar (oförändrad)
```

Två lägen att välja mellan:

- **C1 — Härled baslinje, tillåt override.** `agent_roles` slår upp rollens cell och
  ger `tool_families`-baslinjen automatiskt; en roll som behöver avvika listar extra
  verktyg i `## Tillåtna verktyg` (som idag). Ny roll i en bemannad cell = noll
  manuellt arbete. Befintliga handskrivna listor blir override (bakåtkompatibelt).
- **C2 — Lämna som är** (handskrivna listor). Enkelt nu, men varje ny roll och varje
  verktygsändring blir manuell — exakt det du oroar dig för.

> **Rekommendation:** **C1.** Det är samma härlednings-princip som `kind` (härleds ur
> `part_of`, lagras ej) och `role_for_node`-seamet. Matrisen blir enkällan; rollfilen
> bär bara avvikelser. Löser "manuellt hela tiden" på riktigt.

**[FRÅGA C]** C1 eller C2? Och om C1: ska befintliga handskrivna listor (a) bli rena
override ovanpå cell-baslinjen, eller (b) migreras bort så cellen är enda källan?

---

## 4. Implementationsskiss (om väg 1 + C1 godkänns)

Additivt, i lager, varje steg testbart och bakåtkompatibelt:

1. **`agent_host`: utöka in-process-servern.** Lägg de kurerade verktygen (Val B) som
   `@tool`-wrappers över `scripts/`-datalagret (`issues_client`, `idea_inbox`,
   `prs_client`, `wiki`, `session_store`) — samma mönster som de 4 befintliga.
   Skriv-verktyg gatas bakom `allow_writes` i `can_use_tool`. Namnge `mcp__cns__<tool>`
   så de matchar rollernas `cortxt_`-prefix via routern. **[FRÅGA 1]** Ska
   `resolve()` lägga på rollens *deklarerade* verktygsnamn (mappade till
   `mcp__cns__*`) i `allowed_tools`, i stället för dagens fasta `CNS_TOOL_NAMES`?
2. **Namnmappning.** En tabell `cortxt_<x>` ↔ `mcp__cns__<x>` så rollens deklaration,
   universum A och universum B refererar samma logiska verktyg. **[FRÅGA 2]** Bör de
   lokala verktygen helt enkelt heta `mcp__cns__cortxt_<x>` så mappningen blir
   identitet (mindre glapp), trots längre namn?
3. **`tool_families` → verktyg.** Liten dict (`families.json` eller i `agent_roles`):
   `"issues" → [list_open_issues, get_issue, create_issue, close_issue, add_todo,
   check_todo]`, `"ideas" → [capture_idea, list_ideas, promote_idea_to_issue]`, osv.
   Enkälla för C1-härledningen.
4. **`agent_roles`: härled baslinje (C1).** `parse_agent` slår upp cellen via
   `(department, härledd nivå)`, expanderar `tool_families`, unionar med ev. override
   i `## Tillåtna verktyg`. Degraderar till bara override om cell saknas (bakåtkompat).
5. **Tester.** `test_agent_roles` (härledning + override-union + saknad cell),
   `test_mcp_router` (rollens verktyg → korrekt `allowed_tools`), `agent_host`
   (skriv-gate nekar skrivverktyg i läsläge). Inga nät/SDK-beroenden i testerna.
6. **Diagnostik.** Utöka `cns mcp-servers` eller ny `cns agent-tools <roll>` som visar
   en rolls effektiva verktyg (härledd baslinje + override) — så du *ser* utfallet
   utan att köra ett pass.

---

## 5. Konsekvenser / risker

- **Skrivande lokala agenter blir mer kapabla.** En dispatch-agent kan då skapa
  issues/idéer själv. Detta interagerar med autonomi-tröskeln (`classify_risk`):
  skrivverktyg ≠ self-merge. Tröskeln rör fortfarande filer i PR, inte MCP-verktyg —
  men värt att hålla ögonen på att en agent inte "skapar arbete" okontrollerat.
  **[FRÅGA 3]** Ska skriv-verktyg (create_issue m.fl.) kräva samma `approve`-callback
  som dispatch redan har för muterande steg?
- **Dubbel definition (väg 1).** Verktyg finns i `app/tools/` (universum A) och
  `agent_host` (universum B). Mildras av att båda är tunna wrappers över samma
  `scripts/`-datalager — logiken finns på ett ställe. **[FRÅGA 4]** Värt att lyfta
  wrapper-genereringen till en delad helper senare, eller acceptera duplicering nu?
- **Kontext-kostnad.** Fler verktyg = fler tool-scheman i varje pass prompt. Kurerad
  delmängd (Val B) håller detta nere; C1-härledning ger bara rollen dess cells verktyg,
  inte allt.

---

## 6. Vad detta INTE löser (medvetet uppskjutet)

- `mcp-gateway`-processen (central auth/allowlist/proxy) — Plan B, senare.
- Externa ekrar (Linear/Vercel/Shopify-adaptrar, #77/#78) — toppen av kedjan, väntar.
- git-mcp docs-grounding — separat, billig, oberoende vinst (en rad i registret).
- Autonomi-tröskelns uppluckring — kräver evaler först, eget spår.

---

## 7. Öppna frågor — sammanfattning (besvara innan kod)

- **[FRÅGA A]** Väg 1 (kurerad lokal) eller väg 3 (Railway-koppling)?
- **[FRÅGA B]** Är den kurerade delmängden (§3 Val B) rätt?
- **[FRÅGA C]** C1 (härled baslinje + override) eller C2 (handskrivet)? Om C1: override
  ovanpå cell, eller migrera bort handskrivet?
- **[FRÅGA 1]** Ska `resolve()` lägga rollens deklarerade verktyg i `allowed_tools`?
- **[FRÅGA 2]** Lokala namn = `mcp__cns__cortxt_<x>` (identitetsmappning)?
- **[FRÅGA 3]** Skriv-verktyg bakom `approve`-callback?
- **[FRÅGA 4]** Delad wrapper-helper nu eller acceptera duplicering?
