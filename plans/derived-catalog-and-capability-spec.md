# Spec: Härledd katalog + kapabilitet som routningsdrivande axel

> **Status:** utkast för granskning (spec först — ingen kod förrän godkänd).
> **Datum:** 2026-06-12 · **Ägare:** Rikard + losningsarkitekt/backend-utvecklare.
> **Föregås av:** tre research-rundor om agentur-taxonomi (axlar, run-typer, nod-ontologi).
> **Öppna frågor besvarade (Rikard 2026-06-12) — markeras `✅ BESLUT` inline.**

## 1. Problem (varför)

`catalog.yaml` är idag **32 handunderhållna noder som inte speglar verkligheten**. Agenturens
dispatch-loop routar mot den (`role_for_node` → `route(node.type, …)`), så när kartan ljuger blir
routningen fel. Två konkreta symptom:

1. **Grupperings-attrapper:** `pipeline-intern`, `pipeline-extern`, `pipeline-review` är inte system
   — de finns bara för att `part_of` tål *en* förälder, så de uppfanns som pseudo-noder för att
   gruppera. (Det enda faktiska "smell" research-rundan hittade.)
2. **Verkligheten saknas:** den körande driften — Railway-tjänster, Redis, Vercel-deploys, GitHub
   Actions, MCP-servrar, de ~90 agenterna i rostret — finns inte som noder. 32 poster är en
   *delkarta någon ritade en gång*, inte territoriet.

Detta är **samma lärdom som node.md-teardownen** (epic #11): node.md var "en stilla handunderhållen
parallellkopia av verkligheten". `catalog.yaml` ärvde samma öde. **En handritad karta driver alltid
isär.** Fixen är inte att handredigera 32 → 50 (ljuger igen nästa vecka) utan att **härleda kartan ur
den körande verkligheten och annotera semantik ovanpå.**

Parallellt: **kapabilitet/skills är osynligt för routningen.** Disciplin (`node.type → discipline`)
är enda signalen som väljer agent. Agentens `## Tillåtna verktyg` parsas men styr bara MCP-montering
(MCP-routern, PR #126), inte *vem som väljs*. Skills i `.claude/skills/` syns inte alls för routern.

**Måttstock genom hela specen:** *gör axeln något en agent navigerar dagligen, eller är den bara
korrekt och ligger still?* Skillnaden mellan en målning och en motor. Allt nedan ska klara det testet
— annars hör det till "elegans, deferras" (§6).

## 2. Princip: härlett vs annoterat

Dela varje nod i två lager med olika sanningskälla och olika underhåll:

| Lager | Sanningskälla | Underhåll | Exempel-fält |
|-------|---------------|-----------|--------------|
| **Härlett** | den körande verkligheten / koden | maskin, regenereras | existens, `type` (delvis), `depends_on` (ur imports), `part_of` (ur repo-/mappstruktur), drift-endpoints |
| **Annoterat** | mänskligt omdöme | hand, glest | `summary`, `domain`, `owner_agent`, arkitekturroll, `tags` |

Samma split som teardownen gjorde (katalog-struktur + glesa `decisions/`): strukturen härleds,
*meningen* annoteras. En människa skriver aldrig om vad en maskin kan se; en maskin gissar aldrig
det bara en människa vet.

## 3. Del A — Härledd katalog

### 3.1 Sanningskällor (v1 → senare)
- **v1 (i repot, gratis att läsa):** git-repo-/mappstruktur, `.mcp.json` (MCP-servrar),
  `exports/agents.json` (agentflottan), package-manifest (`requirements*.txt`,
  `cortxt/**/package.json`) + import-graf (`depends_on`).
- **Senare (kräver extern åtkomst/credentials):** Railway-tjänster, Vercel-deploys, GitHub Actions
  (workflow-inventering via `actions`-verktyget), Redis. Dessa är **drift-ytor** — adapter-mönstret
  hör till "ekrarna" ([[integration-ryggrad-vs-ekrar]]), så de läggs efter v1.

> ✅ **BESLUT A1:** **Repo-interna källor i v1** (repo-struktur + `.mcp.json` + `agents.json` +
> manifests). Drift-ytorna görs **efterhand** som ekrar (se 3.1b) — och föregås av en liten
> **research-spike** som kartlägger exakt vad varje drift-källa kräver (API/credential), så de
> ligger som redo backlog i stället för bortglömda.

### 3.1b Drift-källor (planerad uppföljning efter v1, kräver var sin research-spike)
| Drift-källa | Vad den tillför katalogen | Vad som krävs (kartläggs i spike) |
|-------------|---------------------------|-----------------------------------|
| **Railway** | körande backend-tjänster + deras status | Railway API-token / GraphQL; vilka tjänster ↔ vilka noder |
| **Vercel** | dashboard/landing-deploys + domäner | Vercel API-token; projekt↔nod-mappning |
| **GitHub Actions** | workflows som körande "pipelines" | redan åtkomligt via `actions`-verktyget (OAuth) — billigast först |
| **Redis** | lease/eventstream som infra-nod | `REDIS_URL`; mest en statisk infra-nod, låg prioritet |

Ordning: GitHub Actions först (redan auth:at), sedan Railway, sedan Vercel, sist Redis.

### 3.2 Mekanik (förslag)
- `scripts/derive_catalog.py` läser sanningskällorna → skriver `catalog.derived.yaml` (struktur:
  slug, type, part_of, depends_on, källa-per-fält).
- Handannotering bor i `catalog.annotations.yaml` (slug → {summary, domain, owner_agent, tags,
  arkitekturroll}). Glest — bara där en människa tillför mening.
- `scripts/catalog.py:load_catalog()` **mergar** härlett + annoterat → samma
  `(meta, sections)`-form (rad 40/137/187). Konsumenter (`json_exporter`, `tui`, `role_for_node`,
  `derive_kind`) är **oförändrade** — merge sker under befintligt seam.
- **Drift-detektering:** `cns validate` varnar när (a) en annoterad slug saknar härledd motsvarighet
  (nod borttagen i verkligheten men kvar i annoteringen), eller (b) en härledd nod saknar annotering
  (ny verklighet, väntar på mening).

> ✅ **BESLUT A2:** **CI direkt** (GitHub Action på push regenererar `catalog.derived.yaml`). Detta
> funkar redan i v1 *just för att* A1 = repo-interna källor — de är åtkomliga inne i en Action när
> den checkar ut repot, inga hemligheter behövs. `cns derive` finns ändå som lokalt kommando för
> snabb iteration. När drift-källor (3.1b) tillkommer får Action:en motsvarande secrets.
> (CI = "Continuous Integration": ett automatiskt workflow som kör vid varje push, inget manuellt.)

> ✅ **BESLUT A3:** **Hård övergång — men med en synlig diff-grind.** Härledningen genererar
> `catalog.derived.yaml`, **visar en diff mot nuvarande `catalog.yaml`** (vad försvann/ändrades/
> tillkom), och först därefter ersätts den gamla. Brott i dashboarden/konsumenter är *acceptabelt
> och förväntat* — det är en signal på gammalt som ändå ska byggas om (Rikard) — men brottet ska
> vara **synligt i diffen, inte tyst**. Ingen lång parallell-period; en ren skärning som du ser.

### 3.3 Pipeline-attrapperna
Ersätt `pipeline-intern/extern/review` med **`tags`** på berörda noder (t.ex.
`tags: [pipeline, intern]`). Det ger flera grupperingar utan att uppfinna "system" och löser
`part_of`-enförälder-begränsningen som skapade dem. `part_of` reserveras för äkta nesting.

> ✅ **BESLUT A4:** **Pensionera `kind`.** `type` bär den semantiska lasten; `kind` kodar bara
> trädposition (ontologiskt tunn). Konsekvens: `derive_kind` tas bort och dess konsumenter rörs
> (`json_exporter`, `schemas/`, `tui`, ev. dashboard-fält som visar kind). Hanteras som en del av
> A3:s hårda skärning, med diffen som säkerhet — en konsument som bryts på saknat `kind` är just
> en sådan "signal på gammalt".

## 4. Del B — Kapabilitet/skills som routningsdrivande axel

### 4.1 Mål
Gör **kapabilitet** till en förstklassig signal så `route()`/`role_for_node` kan välja agent på
*vad den kan*, inte bara disciplin. En issue/nod som kräver kapabilitet X → en agent som har X;
**fallback till disciplin** (bakåtkompatibelt, befintliga pass bryts inte).

Kapabilitet = unionen av en agents **skills** (`.claude/skills/`) och **MCP-verktyg/servrar**
(`## Tillåtna verktyg`, redan parsat av `agent_roles._parse_tools`, redan använt av `mcp_router`).

### 4.2 Koppling till befintligt
- **MCP-routern** (`scripts/mcp_router.py:resolve`) monterar redan servrar/verktyg per roll — Del B
  återanvänder samma verktygslista som *routnings*-signal, inte bara monterings-signal.
- **#117 capability-capture** (öppen): när ett pass upptäcker en saknad skill/MCP fångas behovet som
  idé (`capability:skill`/`capability:mcp`). Del B ger den fångsten en hemvist: kapabilitets-gapet
  blir synligt i agent-modellen.

### 4.3 Designval (besvarade)
> ✅ **BESLUT B1:** **Härled kapabilitet** ur agentens `## Tillåtna verktyg` (redan parsat av
> `mcp_router`) + dess listade skills. Ingen ny handlista — kapabilitet blir ett *projektivt index*
> över verktyg+skills, konsekvent med Del A:s härled-filosofi.

> ✅ **BESLUT B2:** **Härlett + valfri override (skalbart).** Default: härled en issues/nods
> kapabilitetskrav ur `node.type` + integrationsfält (#77). En valfri label (`needs:<kapabilitet>`)
> kan överstyra när det behövs. Disciplin är fallback. (Rikard lutar hit, vill bygga skalbart —
> härlett-först minimerar manuell taggning men låter en label finkalibrera.)

> ✅ **BESLUT B3:** **Härledd = ingen egen sanning.** Eftersom B1 = härledd är kapabilitet ett
> index, inte en parallell taxonomi — samma anti-drift-garanti som den härledda katalogen. Inga
> manuella tillägg ovanpå (det skulle återinföra driften).

## 5. Hur dispatch läser det (seamet orört)

```
dispatch.py
  → role_for_node(slug, issue_type)
      → read härledd+annoterad katalog (nod finns? type? tags?)
      → route(node.type, issue_type, domain)        # disciplin (som idag)
      → + kapabilitetsmatchning (Del B)              # NYTT: filtrera/ranka squad på kapabilitet
      → load_role(vald agent)
```

`role_for_node`-seamet **utåt är oförändrat** — dispatch-loopen vet fortfarande inget om filformen
eller härledningen. Det är hela poängen: CNS kan byggas om (igen) utan att röra loopen, precis som
idag ([[koppla-ej-mot-foranderligt]]).

## 6. Utanför scope (elegans — deferras tills den bevisat gör något)
- **Run-axeln:** dela `typ` i intent/mode/autonomi (researchen visade att de 7 "typerna" i koden
  egentligen är *lägen* som klumpar tre ortogonala saker). Internt nyttigt men inte akut.
  **Skärpning (när det görs):** `mode` och `autonomi` ska inte återuppfinnas som mjuk `[SESSION: …]`-
  prompttext — de duplicerar Claudes *hårda* grindar (plan mode = read-only, permission modes =
  skrivrätt, `can_use_tool`). En mjuk uppmaning bredvid en hård grind kolliderar, och harnesset
  vinner (vi demonstrerade det: CNS-typen `spec` kördes i praktiken via plan mode). Ren upplösning:
  **intent är CNS:s (brainstorm/spec/triage/retro/review), och CNS-intenten *väljer* harness-läget**
  (spec/brainstorm/triage → read-only, bygg → write/acceptEdits) i stället för att beskriva det i
  text. Då komponerar de: CNS säger *vad*, harnesset håller *hur mycket* — med en riktig grind.
  **Not (stations↔intents — föreningen kommer först):** run-sekvensen är redan modellerad TVÅ gånger
  under olika namn — routnings-`flows[issue_type]` talar *station*-språk (discovery/definition/
  delivery/review/retro) medan sessionsmarkören talar *intent*-språk (brainstorm/spec/bygg/review/
  retro). De matchar bara på review/retro (discovery≈brainstorm, definition≈spec, delivery≈bygg;
  triage/verktygsladan saknar station). Run-axel-arbetet ska **förena de två vokabulärerna till en**
  innan något läggs till. Då kan en spec *härleda* sitt arbetsflöde ur `flows[issue_type]` (inte
  handskriva det — annotera bara avvikelser), parallellt med ägarskaps-härledningen i §9. Och: **lägen
  (mode) ska INTE utökas i CNS** — de ägs av harnesset och är medvetet få; det enda expanderbara är
  intent, och först efter föreningen.
- **Work-axeln:** `initiative` som bet-relation istället för trädtopp ("OKR-misstaget"). GitHub-
  milestones funkar idag.
- **Memory som explicit axel:** researchen är tydlig — minne är *infrastruktur* axlarna kopplar till,
  inte en produktaxel. De 4 lagren stannar som de är.
- **Faktisk implementation** av §3–§4 (efter att denna spec godkänts).

## 7. Verifiering (när det väl byggs)
1. `cns derive` (eller CI) genererar `catalog.derived.yaml` som inkluderar verkligheten v1 saknar
   (MCP-servrar, agentflottan, repo-struktur) — fler än 32 noder, och inga pipeline-attrapper.
2. `load_catalog()` returnerar samma `(meta, sections)`-form → `json_exporter`/`tui`/`role_for_node`
   gröna utan ändring (regressionssäkring).
3. `cns validate` flaggar drift härlett↔annoterat.
4. `role_for_node` på en nod med kapabilitetskrav väljer en agent som *har* kapabiliteten; saknas den
   → fallback till disciplin (ingen regression i befintliga pass).
5. Full testsvit grön; CLAUDE.md uppdateras i samma ändring som arkitekturen landar.

## 8. Risker
- **Härledning utan credentials** (A2) — om CI inte når drift-ytor blir kartan delvis. Mitigering:
  v1 läser bara repo-interna källor; drift adderas som ekrar senare.
- **Över-härledning** — att tvinga in semantik (domain/owner) i härledningen ger gissningar.
  Mitigering: hård gräns härlett/annoterat (§2).
- **Taxonomi-spiral** — Del B kan bli ännu en handlista. Mitigering: härled kapabilitet (B1), gör den
  till ett index, inte en sanning.

## 9. Ägarskap — vilka agenter som är inkopplade

Specen drivs som en **`spec`-session** (definitionsläget mellan triage och bygg) av spec-paret
**produktchef** (vad/varför + acceptanskriterier) + **losningsarkitekt** (hur/risker + teknisk form).
**org-arkitekt** äger axel-beslutet (3 vs 4 axlar, agent som explicit axel) eftersom det rör org-/
agentur-strukturen.

| Del / fråga | Inkopplad ägare | Varför |
|-------------|-----------------|--------|
| Spec-drivning, scope, acceptanskriterier | **produktchef** + **losningsarkitekt** | formellt spec-par (CNS-typ `spec`) |
| Axel-modellen (3→4, agent explicit, run-axel) | **org-arkitekt** | äger agentur-/org-strukturen |
| Del A — `derive_catalog`, `load_catalog`-merge, datamodell | **backend-utvecklare** | äger `catalog.py`/`scripts/` |
| Del A — sanningskällor (`.mcp.json`, drift-adaptrar, GitHub-ytor) | **integrationsutvecklare** | äger integrationsytan/ekrarna |
| Del B — kapabilitet/skills som routningssignal | **backend-utvecklare** + **integrationsutvecklare** | routning (`route`/`mcp_router`) + verktygs-/skill-källor |
| Deferred run-axel (intent/mode/autonomi, harness-delegering) | **sessionskoordinator** | äger sessionsflödet + typdetektering |
| Bemanning om run-/kapabilitetsmodell ändrar roster | **hr-chef** + **kompetensutvecklare** | verktygslåde-läget (ny agent / promptkvalitet) |

**Öppna frågor → ägare:** A1/A2 (källor, när) → backend- + integrationsutvecklare · A3 (migration) →
backend-utvecklare + losningsarkitekt · A4 (pensionera `kind`) → org-arkitekt + backend-utvecklare ·
B1–B3 (kapabilitetsmodell) → losningsarkitekt + integrationsutvecklare.

**Inkopplingspunkt:** detta är den brainstorm→spec-övergång som aldrig triggades — att köra specen
SOM en `spec`-session med ovan roller *är* att gå in i spec-läget. Föregående beslut (Rikards
leanings på A1–A4) noteras separat och löses av respektive ägare.
