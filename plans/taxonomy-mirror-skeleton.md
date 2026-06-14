# Spegel-skelett: kanonisk taxonomi → projektion per plattform (PARKERAD)

**Status:** parkerad 2026-06-14 — väntar på att git/GitHub-fundamentet landar (`decisions/git-github-grund.md`),
särskilt org-setup, eftersom GitHub-adaptern riktar mot org-level Projects v2.

## Context
Rikard blir "yr" i GitHub-milestones: ser `Initiative: Agentur`/`Integrations` utan att kunna filtrera. Roten är att
CNS-taxonomin inte speglas rent utåt — initiativ-lagret läcker som textprefix (`issues_client.py:551-562`) och tre namn
betyder samma sak (Milestone = quest = epic). CNS HAR en rik kanonisk taxonomi; problemet är projektionen, inte modellen.
Mål: CNS äger originalet i mitten; varje plattform (GitHub nu; Linear/Vercel förberedda) får en partiell spegel.
Mönster: Canonical Data Model + Anti-Corruption Layer (Hohpe/Woolf, Evans), à la Backstage/Unito.

## Låsta beslut
1. **GitHub förblir källan till sanning** — lyft inte ut lagring, gör projektionen explicit.
2. **Tvåvägs på systemnivå, single-writer per fält** — data flödar åt båda håll men varje fält har EN skrivare
   (CNS äger struktur→ut; GitHub äger PR/merge→in; Linear äger planering/sprint→in; Vercel äger deploy→in).
   Tabellen bär `direction`+`field_owner` per fält. Samma-fält-tvåvägs (last-write-wins) UTESLUTET.
3. **Initiativ = single-select-fält på org-level Project v2** (ej textprefix/label). Regex-parsing som läs-fallback.
4. **GitHub-org invävd** — org-Projects v2 = cross-repo mirror-yta; Teams = ägarskaps-axel (ej taxonomi).
5. **No-op förstaklassens** — deklareras explicit, ej spridda null-checks.
6. **Scope** = bakåt-till-front i tre faser; kontrolltorn-vyn knyts till epic #8 (`plans/control-tower-spec.md`).

## Kanonisk modell (kodifieras, ändras ej)
```
initiative   (valfri toppnivå)            → org-Project single-select-fält  [idag = textprefix]
  └─ epic     = quest = GitHub Milestone   → milestone (per-repo lagring) + org-Project-vy (cross-repo)
       └─ story = GitHub Issue             → issue + label type:<v>, additem i org-Project
            └─ sub-task = todo             → task-list-checkbox i body
  (sprint)    valfri tidsbox under epic    → org-Project Iteration-fält
```

## Org-topologi som påverkar GitHub-adaptern
- Org-Project v2 håller issues/PRs från ALLA repon → cross-repo-hierarkins hem + kontrolltornets GitHub-sida.
  Items via GraphQL `addProjectV2ItemById`; fält via `updateProjectV2ItemFieldValue`.
- Initiativ = single-select (max 50 alt). Epic = Milestone som LAGRING (wirad modell rörs ej) + org-Project-vy.
  (Alt: epic=issue+sub-issues — dokumenterat, EJ valt, vore omskrivning.)
- Sprint = Iteration-fält; **defensiv write** (läs-bygg-skriv) pga API-bugg som annars tappar tilldelningar.
- Teams = ägarskap (`owner_agent`→Team), aldrig taxonomi.
- API: ProjectV2 GraphQL (delvis REST sedan 2025-09); `project`-scope; cacha opaka node-IDs; rate limit 5000 p/h.

## Fas 1 — Backend-fundament
- **1a. NY `scripts/work_taxonomy.py`** — enkälla (frozen dataclasses, mönster `tools/registry.py:24-61`): `LAYERS`
  (initiative→epic→story→todo), `ISSUE_TYPES`. Re-exportera `VALID_ISSUE_TYPES`/`DEFAULT_ISSUE_TYPE`; `issues_client.py:42-44`
  importerar därifrån (noll beteendeändring).
- **1b. NY `scripts/projections.py`** — deklarativ tabell `Projection(canonical, platform, native, mechanism, direction,
  field_owner, note)`; `native=None`→no-op. GitHub formaliserar dagens beteende + org-ytan; Linear/Vercel deklarerade EJ
  byggda (`mechanism=None`). Getter + kapabilitetskoll, ingen motor.
- **1c. NY `scripts/gh_project_sync.py`** — org-Project GraphQL-spegling (add_item/set_field, cacha node-IDs, defensiv
  iteration-write). Bygg på befintlig `scripts/tools/gh_project_core.py`.
- **1d. Migrera initiativ-prefix → org-Project-fält** (additivt): `create_milestone` behåller textrad + sätter fält;
  `_normalize_milestone` läser fält först, annars `parse_initiative` (fallback). Engångs-backfill separat.
- **1e. Vercel- + Team-fält på noder** (inert): valfritt `vercel_project_id` i `catalog.yaml`+`catalog_schema.json`;
  `owner_agent`→Team deklareras i tabellen.

**Sprint-acceptanstest:** lägg "sprint" = endast DATA i de två nya filerna (LAYERS-rad + projektion-rad/plattform:
GitHub→Iteration, Linear→Cycle, Vercel utelämnas/no-op). Ingen kärnändring för att DEKLARERA. Faktisk sprint-nivå rör
sedan json_exporter/health/recommend/`/api/`-endpoint — listas, byggs ej i skelettet.

## Fas 2 — API-yta för arbetshierarkin
Utöka `/api/quests` (el. ny `/api/initiatives`) i `app/server.py` att gruppera epics per initiativ via org-Project-fältet
(cross-repo); returnera trädet initiative→epic→story additivt (bryt ej `useProjects.js`).

## Fas 3 — Kontrolltorn-vy (epic #8)
Vy som visar arbetshierarkin (ej nodgrafen), grupperbar per initiativ. Bygg i cortxt-dashboard eller TUI:ts
`OverviewScreen`. **Frontend-kontrakt-vakt:** `kind`-enum (4 ställen), `LANE_ORDER`-slugs (`ContainerGraphCanvas.jsx:46`),
`part_of`-nesting, svenska sektionsnamn (`zoneSections.js`) — uppdatera i samma ändring som projektionen.

## Avgränsning
- Bygger EJ faktisk Linear/Vercel-synk (deklareras). Linear kräver extern MCP/OAuth (PR #135).
- Bygger EJ hävstångsvyn. **Flagga:** `depends_on`/`feeds` (nodgraf) är osäker/gammal axel — hävstång ska ej vila på
  den blint; eget beslut senare.
- Skriver EJ om kärnlogik (dispatch/agentur — `role_for_node`-seamet orört).

## Verifiering
- `tests/test_work_taxonomy.py`: bakåtkompat på issue-typer; `Layer.parent`-referensintegritet.
- `tests/test_projections.py` (grön lampa): sprint-fixtur → `projection("sprint","github").mechanism=="iteration_field"`,
  `("sprint","linear").native=="Cycle"` med `mechanism is None`, `("sprint","vercel") is None`; varje GitHub-projektion
  `native is not None`; varje canonical i LAYERS.
- Initiativ-migrering: `_normalize_milestone` med gammal textrad OCH org-Project-fältkälla → båda ger rätt initiativ.
- Befintliga `issues_client`-tester oförändrade (regressionsskydd för import-flytt).
