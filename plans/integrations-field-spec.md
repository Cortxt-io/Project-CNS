# Spec: Per-nod `integrations`-fält — skilj drift (deploy) från källor (sources) [#77]

> Spec-pass 2026-06-11 (session b14c794b). **Granskningsutkast — ingen kod.** Bygger på
> `docs/cortxt-kontrollplan-arkitektur.md` (öppet byggsteg 1) och följer EXAKT samma additiva
> mönster som type/domain/owner_agent (#45/#47/#48). **Foundational: blockerar Vercel-adaptern (#78).**
>
> **REVIDERAD 2026-06-12 — fältet bor i `catalog.yaml`, INTE i node.md-frontmatter.** Nodmodell-
> teardownen (epic #11, `plans/nodmodell-teardown-spec.md`) river node.md-blanketten och flyttar alla
> systemfält till `catalog.yaml`. `integrations` ska därför bli ett **katalog-fält** per system.
> **#77 depends-on #98** (katalog-läsaren). Mönstret nedan (enums + mjuk validering + export) är
> oförändrat — bara *ytan* fältet bor på byter från node.md-frontmatter till `catalog.yaml`-posten.
> Läs `validator.py`/`json_exporter.py`-referenserna som "mot katalogen" efter steg 1–3 i teardownen.

## Kontext / varför
Nodmodellen saknar helt ett strukturerat sätt att uttrycka en nods externa integrationer.
Deploy-info ligger idag utspridd i `url_live`/summary/brödtext (cns-vault-app→Railway,
cortxt-dashboard-app→Vercel, cns-mcp→Railway). Det blockerar Vercel-driftsadaptern (#78) och
Shopify-källor: adaptern behöver veta *vilka noder den äger* och *var de kör*. Knyter till minnet
`integration-ryggrad-vs-ekrar`.

## Kärndistinktion (det fältet ska bära)
| Under-nyckel | Innebörd | CNS-roll | Exempel |
|---|---|---|---|
| `deploy` | **var noden kör** (driftslager) | CNS **agerar** — deployer, pollar status (#78) | `vercel`, `railway` |
| `sources` | **vad noden konsumerar i runtime** | CNS **bär bara konfig vidare** (passivt) | `shopify:store-x` |

**Varken git eller GitHub modelleras som en source.** Skilj lagren (idea-369ef21a):
- **Datan/sanningen lever i `git`** (node.md — commits/historik; host-portabelt: GitLab/Bitbucket funkar).
- **Arbetsmodellen körs på `GitHub`** idag (issues/quests/PR/Actions/Contents-API — GitHub-specifikt, ej bara git).
Inget av dessa är en "source" i integrations-mening — de är ryggraden/substratet CNS lever i, inte en extern
integration noden konsumerar. Att lista dem vore att degradera ryggraden till en eker. (Host-agnosticism =
abstrahera GitHubs arbetsyta bakom adapter → fångat som idea-369ef21a, ej i scope här.)

## Fältform (additivt, valfritt, fallback på system utan det)
Bor under systemets post i `catalog.yaml` (bredvid type/domain/feeds/depends_on):
```yaml
systems:
  cns-vault-app:
    # ... title/summary/part_of/type/domain ...
    integrations:
      deploy: [railway]               # lista av deploy-target-slugs (enum deploy_targets)
      sources: [shopify:store-x]      # lista av "<type>:<instans>"-strängar (type ur enum source_types)
```
- Hela `integrations` valfritt; ett system utan det validerar och exporteras oförändrat.
- `deploy`: platt lista av target-slugs. `sources`: platt lista av `type:instans`-strängar (instansdelen
  fri text, type-delen valideras mot enum). **Öppen fråga A (se nedan):** platt sträng vs strukturerat objekt.
- `catalog.yaml` är vanlig nästlad YAML — `load_catalog()` läser det oförändrat, ingen parser-ändring krävs.

## Del 1 — enums.json (enkälla; konsumeras av validator.py + JS cns-schema)
Lägg två enums (ordning ej semantisk; växbara additivt):
```json
"deploy_targets": ["vercel", "railway", "cloudflare-pages", "netlify", "github-pages", "fly", "render"],
"source_types":   ["shopify", "stripe", "slack", "linear", "notion", "google-sheets"]
```
Härledda ur faktiska/planerade integrationer (Railway+Vercel live idag; Shopify = shopify-venture-domänen).

## Del 2 — validator.py (mjuk validering, WARN ej ERROR — som #47/#75)
I `validate_node` (returnerar `(errors, warnings)`), efter type/domain-blocket:
- Ladda `VALID_DEPLOY_TARGETS`/`VALID_SOURCE_TYPES` ur enums (`_ENUMS.get(...)`, tom set = hoppa).
- Om `integrations` är dict:
  - `deploy`: för varje target ej i `VALID_DEPLOY_TARGETS` → WARN `"Unknown deploy target '<x>'"`.
  - `sources`: split på första `:`, validera type-delen mot `VALID_SOURCE_TYPES` → WARN om okänt.
- En nod utan `integrations` ger ingen anmärkning (fallback). Aldrig ERROR — additivt.

## Del 3 — json_exporter.py (additivt på v3.0 som landade i #84)
- Lägg `"integrations": meta.get("integrations") or {}` i per-nod-payloaden (bredvid type/domain/owner_agent).
- Versionsbump valfri (v3.1) — eller behåll 3.0 eftersom det är rent additivt; dashboarden fallbackar på tomt objekt.
- **(Senare, ej v1):** härled integrations-edges (`NODE --deploys_to--> vercel`, `NODE --consumes--> shopify`)
  i `_derive_*_edges`-stil så dashboarden kan rita driftberoenden. Parkeras tills #78 behöver dem.

## Del 4 — Backfill (i `catalog.yaml`, ett system i taget)
Fyll `integrations.deploy` på de system där driften är uppenbar (ur dagens url_live/text):
`cns-vault-app`→`[railway]`, `cns-mcp`→`[railway]`, `cortxt-dashboard-app`→`[vercel]` (ev. `cloudflare-pages`),
`cortxt-landing`→`[github-pages]`. `sources` lämnas tom tills Shopify-noder finns. Dispatchbar till flottan.

## Del 5 — JS cns-schema
Regenerera `cortxt/packages/cns-schema` ur enums.json (`generate.mjs`) så `deploy_targets`/`source_types`
propagerar till dashboarden. Samma steg som types/domains (cortxt #3).

## Öppna frågor (besvaras i granskning, före kod)
- **A. Platt sträng vs strukturerat objekt.** `deploy: [vercel]` är enkelt men bär ingen instans-/URL-info.
  `deploy: [{target: vercel, url: ...}]` bär mer men är tyngre och dubblar `url_live`. **Rek:** börja platt
  (target-slugs); strukturera bara om #78 visar att adaptern behöver per-instans-konfig i node.md (annars
  bor instansdata hos adaptern, inte i noden).
- **B. Relation till `url_live`/`url_repo`.** `url_live` finns redan. Ska `integrations.deploy` ersätta det,
  komplettera, eller härledas? **Rek:** komplettera (behåll url_live för bakåtkomp); integrations bär *target-typen*,
  url_live bär *adressen*. Ev. konsolidering är ett eget senare steg.
- **C. Edges nu eller senare?** **Rek:** senare (Del 3-noten) — v1 bär bara fältet; edges när #78 behöver dem.

## Migreringsväg (additiv, bryt inte dashboarden)
1. enums.json: `deploy_targets` + `source_types`. 2. validator.py: mjuk WARN. 3. json_exporter: exportera fältet.
4. JS cns-schema regenerera. 5. Backfill deploy på de ~4 uppenbara noderna. (6. senare: edges + #78 Vercel-adapter.)

## Verifiering (när byggd)
- Ett system utan `integrations` validerar och exporteras oförändrat (fallback).
- `cns validate` WARN:ar (ej ERROR) på okänt deploy-target/source-type i katalogen.
- `nodes.json` innehåller `integrations` per system; dashboarden bryts ej på tomt objekt.
- Backfillade system: `cns validate` 0 ERROR; `integrations.deploy` syns i exporten.
- `.claude/` läses ej (oförändrat — fältet bor i `catalog.yaml`).

## Avgränsning
- Ingen Vercel-adapter (#78), ingen deploy-logik — bara datastrukturen + validering + export.
- Inga integrations-edges i v1 (parkerat till #78). Ingen url_live-konsolidering nu.
- GitHub modelleras aldrig som source (ryggrad, ej eker).
