# Spec (GRANSKAD): Nodmodell-teardown → katalog-fil + ADR-noter

> Beslut Rikard 2026-06-12. Ersätter/omtolkar riktningen i `node-model-evolution-spec.md` och
> `node-schema-lock-spec.md`: den additiva IDP-evolutionen byggde delvis **commodity** som GitHub
> Projects/Linear redan äger. Detta pass **river** node.md-blanketten istället för att utöka den.

## Bakgrund — fyra read-only-sonder (2026-06-12)

- **Sond 1 (färskhet):** Alla 31 noder skapade i klump 06-07/08, ingen rörd 06-11 trots tunga
  byggpass → noderna är en **stilla parallellkopia** av verkligheten.
- **Sond 2 (graf):** Endast **4 riktiga `depends_on`** + en handfull `feeds`; `part_of` = ett träd →
  den unika grafen ryms i **EN fil**; 31 blanketter var överbygge.
- **Sond 3 (routing):** `role_for_node` läser **bara `type` + `domain`** ur node.md → routing behöver
  bara en `slug → {type,domain}`-tabell.
- **Sond 4 (prosa):** Tunn (50–270 ord/nod) men rymmer äkta **beslutskunskap utan annan hemvist**
  (ADR-lager) som måste räddas.

**Rotorsak:** node.md är en hand-underhållen parallellkopia av verkligheten istället för en härledd
vy. Tre av fyra blockers (underhåll, passar-inte, stilla) är samma duplicering.

## Beslut

Riv `nodes/<slug>/node.md` (31-blanketten). Ersätt med:
1. **`catalog.yaml`** (repo-rot) — systemkatalog + arkitekturgraf + routing-tabell i en fil.
2. **`decisions/<slug>.md`** — glesa ADR-noter, bara där varaktig beslutskunskap finns.

Delegera `status`/`stage`/arbete/risk till GitHub Projects/Linear. Behåll dispatch + `role_for_node`
orört (de läser nya källan via samma seam). GitHub är fortsatt sanning; `catalog.yaml` committas och
driver `nodes.json` precis som idag — **`nodes.json`-schemat hålls oförändrat** så dashboarden/Railway
inte bryts.

## Målbild

### 1. `catalog.yaml`
```yaml
systems:
  agent-studio:
    title: Agent Studio
    summary: Interaktivt studio för att skapa/konfigurera agenter via /agent-studio.
    part_of: interface
    type: tool          # driver agent-routing (role_for_node)
    domain: cortxt
    feeds: [cns-mcp]
    depends_on: [cns-mcp, local-ai]
  cns-core:
    title: CNS Core
    summary: CLI, parser, validator, exportörer — substratet.
    part_of: infrastructure
    type: cli
    domain: cortxt
    feeds: []
    depends_on: []
  # ... 29 till
```
- **Överlever:** `slug` (nyckel), `title`, `summary`, `part_of`, `feeds`, `depends_on`, `type`,
  `domain`. `kind` härleds som idag ur `part_of`-struktur, lagras ej. (`url_repo` flyttas in om värdefullt.)
- **Dör:** `status`, `stage`, `risks[]`, `primary/secondary_audience`, samtliga legacy (`mvp_stage`,
  `cost_sek`, `value_sek`, `roi_percent`, `family`, `layer`, `pipeline`), `tags`, `current_slice`.

### 2. `decisions/<slug>.md`
Endast för system med faktisk beslutsprosa (idag ~3–5). Fri markdown, ingen mall, ingen frontmatter.
Avsaknad av fil = systemet har ingen ADR-kunskap, vilket är meningen.

### 3. Delegeras till board (GitHub Projects rekommenderat)
`status`/`stage` → custom field. Arbete/risk → issues. "Härnäst" → sparad board-vy.

## Migreringssteg

**Steg 0 — Generera katalogen (mekaniskt, engångs).** `scripts/migrate_to_catalog.py` läser
`nodes/*/node.md` via `md_parser.read_all_nodes()`, plockar överlevande fält → `catalog.yaml`.
Extraherar substantiella `## Anteckningar` (>40 ord) → `decisions/<slug>.md`. Manuell granskning efteråt.

**Steg 1 — Repointa läsarna.** Ny `scripts/catalog.py` med `load_catalog()`. **Behåll
`read_all_nodes()` / `read_node(slug)` som tunna wrappers** som returnerar samma dict-form ur katalogen
→ konsumenterna (`json_exporter.py`, `app/tools/projects.py`, `scripts/tui/data.py`, `analyst.py`,
`portfolio_brief.py`, `recommend.py`) ändras inte. `export_json` behåller `nodes.json`-schema; agent-/
edge-härledning (#82/#84) kvar, node-delen kommer nu ur katalogen.

**Steg 2 — Repointa routing.** `agent_roles.role_for_node` läser `type`/`domain` ur `load_catalog()`.
`dispatch.py` orörd (litar på seamet).

**Steg 3 — Validering + schema.** `schemas/node_schema.json` → `schemas/catalog_schema.json`
(enums ur `enums.json`; `part_of`/`feeds`/`depends_on`-referenser måste finnas; cykelkoll i `part_of`).
`enums.json` behåller `types`/`domains`, tar bort/avmärker `statuses`/`stages`/`mvp_stages`/
`risk_categories`. `validator.py` validerar katalogen; `cns validate` mot hela filen.

**Steg 4 — Riv det döda.** Ta bort `nodes/*/node.md`-trädet (efter verifierad dashboard), kind-medvetna
sektionsmallar + `new_node_template` + risk-/legacy-schema i `md_parser.py`, `scripts/quest_manager.py`.
`cns.py` `new/update/show/list` mot katalogen (prosa-`update` → redigera `decisions/<slug>.md`).

**Steg 5 — Delegera status till board (deferbart).** `status`-custom-field på GitHub Projects, mappa
systemen. Kärnvärdet landar i steg 0–4.

**Steg 6 — Dokumentation.** Uppdatera `Project-CNS/CLAUDE.md` + workspace-`CLAUDE.md` i samma ändring.

## Filer som rörs

| Fil | Ändring |
|---|---|
| `catalog.yaml`, `decisions/*.md` | Nya — källan |
| `scripts/catalog.py`, `scripts/migrate_to_catalog.py` | Nya |
| `scripts/md_parser.py` | wrappers; ta bort mallar/template |
| `scripts/json_exporter.py` | Läs katalog; behåll nodes.json-schema |
| `scripts/agent_roles.py` | `role_for_node` läser katalog |
| `scripts/validator.py`, `schemas/` | Validera katalog |
| `cns.py`, `scripts/tui/data.py`, `app/tools/projects.py` | Mot katalog (via wrappers) |
| `scripts/quest_manager.py`, `nodes/` | Raderas |
| båda `CLAUDE.md` | Uppdateras |

## Verifiering

1. Steg 0: `catalog.yaml` har 31 system; diff mot stickprov (agent-studio, cns-core).
2. Steg 1: `cns export json` ger `nodes.json` likvärdigt med nuvarande node-del; `python -m scripts.tui` ritar trädet.
3. Steg 2: `tests/test_dispatch.py` grönt; `role_for_node('agent-studio','story')` = samma roll som före.
4. Steg 3: `cns validate` passerar; avsiktligt trasig `part_of`-referens fångas.
5. Steg 4: Full testsvit grön; dashboarden ritar grafen utan node.md på disk.
6. Steg 5: Sätt en systemstatus på boarden; dispatch (läser ej status) opåverkad.

## Avgränsning / risk

- **Dashboard-kontrakt:** `nodes.json`-schema oförändrat → cortxt-repot rörs ej i steg 0–4.
- **Sessions/btw/idéer:** ortogonala, rörs ej.
- **Krock med #77 (`integrations`-fält):** `plans/integrations-field-spec.md` antar att fältet bor i
  `node.md`-frontmatter. Den ytan avvecklas här. **`integrations` ska bli ett katalog-fält** (per system
  under `catalog.yaml`, med `deploy`/`sources`-delning) — inkluderas i `catalog_schema.json` (steg 3).
  #77 depends-on katalogen (steg 1), och #78 (Vercel-adapter)/#79 (modell-router) bygger ovanpå.
  Kontext: `docs/cortxt-kontrollplan-arkitektur.md`.
- **Ärlig flagga:** mest av den värdefulla prosan (sond 4) handlar om att bygga CNS självt. Den riktiga
  produktkunskapen (Shopify-venture, kundprodukter) finns knappt i systemet — teardownen gör det
  billigare att fånga den men löser inte att den saknas. Det är nästa, viktigare arbete.
