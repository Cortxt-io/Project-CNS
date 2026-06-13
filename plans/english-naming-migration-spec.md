# Spec: English naming migration — agent slugs + skills

**Status:** utkast för granskning · 2026-06-13 · ingen kod/rename utförd
**Berör:** `.claude/agents/*.md`, `.claude/org/{manifest.json,bemanning_matris.json,roster/*.md}`,
`scripts/router.py`, `catalog.yaml`, regenererade `AGENTUR.md`/`exports/agents.json`/`exports/nodes.json`
**Bakgrund:** [[engelsk-namnmigrering-pending]] · språkpolicy: artefakter engelska, chatt/decisions svenska

> Spec-först (arbetsregel). **Mappningen (§2) kräver Rikards godkännande innan exekvering** —
> det är ett namnval, inte härledbart. Allt annat följer mekaniskt av mappningen.

## 1. Varför + omfång
Svensk-namngivna artefakter bryter språkpolicyn. Rikard flaggade `/org-underhall`. Omfång v1:
**agent-slugs (25) + 2 skills**. Departments (`Drift`/`Ekonomi`/`Kommunikation`/`Produkt`/`Ledning`/
`R&D`) är också svenska och sitter i matris-nycklar (`Drift|ic`) — **deferras till v2** (egen
churn, separat beslut). Display-labels (`"Produktchef"`) — se [FRÅGA C].

**194 filer refererar slugs**, men bara källorna nedan handredigeras; historik lämnas, genererat regenereras.

## 2. Föreslagen mappning (slug → slug) — [FRÅGA A: godkänn/justera]
| Svenska | Engelska | | Svenska | Engelska |
|---|---|---|---|---|
| backend-utvecklare | backend-developer | | operativ-chef | coo |
| frontend-utvecklare | frontend-developer | | teknisk-direktor | cto |
| fullstack-utvecklare | fullstack-developer | | stabschef | chief-of-staff |
| devops-ingenjor | devops-engineer | | produktchef | product-lead |
| integrationsutvecklare | integration-developer | | losningsarkitekt | solution-architect |
| terminal-utvecklare | terminal-developer | | programledare | program-lead |
| plattformsingenjor | platform-engineer | | sessionskoordinator | session-coordinator |
| plattformschef | platform-lead | | org-arkitekt | org-architect |
| driftchef | operations-lead | | hr-chef | people-lead |
| ekonomichef | finance-lead | | kompetensutvecklare | learning-developer |
| forskningsledare | research-lead | | lagesanalytiker | situation-analyst |
| kommunikationschef | communications-lead | | teknisk-skribent | technical-writer |
| | | | underhallsingenjor | maintenance-engineer |

Redan engelska (orörda): `agile-coach`, `qa-lead`.

**Skills:** `bemanna` → `staff-role` · `org-underhall` → `org-maintenance` [FRÅGA B].

## 3. Migreringsordning (mekanisk, efter godkänd mappning)
1. **manifest.json** — byt slug i varje tupel (sanningskällan).
2. **Agent-filer** — `git mv .claude/agents/<sv>.md <en>.md` + sätt `name:` i frontmatter.
3. **Roster-filer** — `git mv .claude/org/roster/<sv>-N.md <en>-N.md` + `name:`.
4. **router.py** — byt slug i `ROUTING_RULES` (mål-slug per regel).
5. **bemanning_matris.json** — `reporting_targets`-värden.
6. **catalog.yaml** — `owner_agent`-värden.
7. **Skills** — `git mv .claude/skills/<sv>/ <en>/` + uppdatera ev. `SKILL.md`-namn + referenser i router/docs.
8. **Regenerera** — `python -m scripts.gen_agentur` (→ AGENTUR.md + agents.json) · `cns export` (→ nodes.json).
9. **Docs** — `CLAUDE.md`/`AGENTUR.md`-referenser, `decisions/`, denna spec.

Driv via en **mappnings-dict + skript** (ett `sed`-liknande pass per källtyp) så inget glapp uppstår;
verifiera med `cns agent-tools <ny-slug>` + `validate_org`.

## 4. Lämnas medvetet (skrivs INTE om)
`exports/sessions/*.json`, `exports/ideas/*.json`, `exports/btw/*.json` — historiska poster; gamla
slugs där är korrekt (de refererar vad som var sant då). Att skriva om historik vore fel.

## 5. Risker
- **Routing-brott:** en missad slug i `router.py`/`role_for_node` → agent hittas ej. Mitigera: efter
  migreringen, assert att varje `ROUTING_RULES`-mål finns som agent-fil; kör ett dispatch-pass.
- **validate_org:** manifest↔roster-täckning måste hålla efter rename (samma slug på båda sidor).
- **catalog `owner_agent`:** validator har mjuk owner_agent-koll → byt i samma pass.
- **Delvis migrering:** gör allt-eller-inget per slug i EN PR; ingen halv-migrering på main.
- **Historik-länkar:** sessioner/idéer länkar gamla slugs — acceptabelt (read-only data), men
  `cns session`-vyer visar gamla namn för gamla poster.

## 6. Verifiering
- `validate_org` grön · `cns agent-tools <ny-slug>` för 3 roller · ett `python -m scripts.dispatch`
  read-first-pass routar till en omdöpt roll · `git grep -E "<gamla-slugs>"` ger 0 träffar utanför
  `exports/{sessions,ideas,btw}` · full `pytest`.

## 7. Öppna frågor
- **[FRÅGA A]** Godkänn/justera slug-mappningen (§2). C-suite: `coo`/`cto`/`chief-of-staff` ok, eller `operations-chief`/`technical-director`?
- **[FRÅGA B]** Skill-namn: `staff-role`/`org-maintenance` ok?
- **[FRÅGA C]** Display-labels i manifest (`"Produktchef"`) — engelska nu, eller lämna (visningsprosa)?
- **[FRÅGA D]** Departments (v2) — separat migrering senare, eller ta med nu?
- **[FRÅGA E]** En stor PR (allt-eller-inget) eller skivat per avdelning?
