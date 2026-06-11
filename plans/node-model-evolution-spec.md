# Rapport + spec-utkast: Nodmodellens efterträdare

> Riktad research 2026-06-11 (session-90ce28af), 4 spår × Sonnet, primärkälle-belagd. Syntes nedan.
> **Granskningsutkast — ingen kod.** Svarar på Rikards diagnos: "nodmodellen som vi har den idag är
> en nybörjarställning och hänger efter; hur gör större produktbolag?"

## Kärnslutsats

Nodmodellen är **inte fel — den är ofullständig på tre precisa sätt**, och mogen praxis (Backstage,
C4, IDP:er, Team Topologies/DDD) pekar på exakt tre tillägg. Och det viktigaste: nästan allt är
**additiv evolution av det som finns** (node.md + agent-frontmatter + `node:`-labels på issues),
**inte en ombyggnad**. Din nybörjar-känsla stämmer — den platta `kind`-modellen *är* tunn — men
fixen är att växa den mot en IDP/sociotekniskt-graf-modell, inte att kasta den.

## De tre luckorna (och vad branschen gör)

### Lucka 1 — Typningen är för tunn (Backstage + C4)
CNS: `kind: component|system|framework` som "emergerar ur part_of". Mogen praxis skiljer på **kind**
(grov klass) + **type** (precisering) + **lifecycle/stage** (explicit, inte emergerad) + **owner**.
- **Backstage:** 7 kinds (Component/System/**Domain**/API/Resource/Group/User), var och en med
  `spec.type` (website/service/library…) och `lifecycle` (experimental→production→deprecated).
- **C4:** Person / Software System / Container / Component — fyra elementtyper som möjliggör zoom.
- **Adoptera för CNS:** lägg `type` under varje `kind`; gör `stage` semantiskt definierad; inför
  `domain` som ny toppnivå; skilj `feeds` (dataflöde) från `provides/consumesApi` (kontrakt).
- **Skippa för CNS:** full Group/User-hierarki (solo/agent-org) → ersätt med ett `owner`-fält.

### Lucka 2 — Grafen modellerar BARA arkitektur, inte agenturen och arbetet (Team Topologies/DDD)
Detta är den stora. Din 88-roller-agentur och ditt arbete (initiativ→epic→story) lever **helt
utanför** nodgrafen. Mogen praxis modellerar de tre lagren som **EN korsad sociotekniska graf**:
- **Ägarskap är en RELATION, inte ett fält** (Backstage `ownerOf`, DDD bounded-context-ägare).
- **En agentroll = ett "Group"-objekt** med kanter till de noder den äger/bidrar till.
- **Arbete länkas till komponent** via explicit kant (`node:<slug>`-labels finns redan — men som
  svag tagg, inte traverserbar kant).
- **Conway/Inverse Conway gäller även AI-agenter** (Team Topologies jan-2025, McKinsey "agentic
  organization"): agentstrukturen bör spegla önskad arkitektur, annars driver den mot inkoherens.

### Lucka 3 — Noder är en stilla ögonblicksbild, inte levande (IDP:er + C4 living-architecture)
CNS uppdaterar noder bara när en agent aktivt skriver. Port/Cortex/OpsLevel håller kataloger
levande via: **pull-synk från primärkällor** (inte manuell skrivning) + **owner som tvingande fält**
+ **scorecards** (mätbara krav med konsekvens). Stale data syns som failade checks.
- **Adoptera för CNS:** GitHub Actions som vid push skriver *beräknade* frontmatter-fält
  (`last_commit`, `open_issues`, `ci_status`, `last_reviewed`); en `health_score`-check; staleness-
  flagga (issue om nod orörd > N dagar). Agenten behöver inte veta — datan är alltid färsk.

## Visualiseringen (C4 zoom — svarar på "hänger efter")

Problemet med dagens ReactFlow-graf är att **en enda platt vy blir rörig**. C4/Structurizr löser det
med **en modell, flera vyer per zoom-nivå** — och CNS:s `part_of` ÄR redan containment-hierarkin:
- **L1 System Context:** noder utan `part_of` (toppsystem) + externa aktörer.
- **L2 Container:** expandera en vald nod → dess `part_of`-barn.
- **L3 Component:** barnbarn.
- Plus de nya lagren ger vyer som: *"vad äger agent X?"*, *"vilket arbete riktar sig mot nod Y?"*,
  *"hur mycket aktivt arbete per komponent?"*
- Implementeras som **filter på befintlig data**, inte nya diagram. (Ev. generera Structurizr-DSL ur
  node.md som komplement.)

## Föreslaget målschema (additivt — inga nya filformat)

```
NODE (befintlig)   slug, title, kind, stage, part_of, feeds, depends_on
  + type           # NY: precisering under kind (api-service, data-pipeline, frontend, mcp-server…)
  + domain         # NY: affärskontext-grupp (valfri toppnivå)
  + owner_agent    # NY: primärt ägarskap → kant till AGENT
  + c4_level       # NY: system|container|component (driver zoom)
  + (beräknade)    # last_commit, open_issues, ci_status, last_reviewed, health_score — via CI

AGENT (ny entitet, genereras ur .claude/agents/*.md frontmatter)
  slug, title, department, squad  → owns/contributes_to → NODE ; assigned_to → ISSUE

QUEST/EPIC, ISSUE/STORY, INITIATIVE (befintliga, GitHub)
  node:<slug>-labels traverseras till kanter: QUEST --targets--> NODE, ISSUE --addresses--> NODE
```

Kant-familjen (korsar lager):
```
NODE  --part_of/feeds/depends-->  NODE     (befintligt)
AGENT --owns/contributes_to-->    NODE     (NY — gör agenturen synlig)
AGENT --assigned_to-->            ISSUE    (NY)
QUEST --targets-->                NODE     (NY — gör arbetet synligt)
ISSUE --addresses-->             NODE      (NY)
```

`json_exporter.py` exporterar en utvidgad `nodes.json` med alla tre entitetsklasser + kanter;
dashboarden ritar org + system + arbete i samma graf, filtrerbart per zoom-nivå och lager.

## Migreringsväg (additiv, en bit i taget — bryt inte dashboarden)

1. **Schema:** lägg `type`/`domain`/`owner_agent`/`c4_level` som *valfria* fält (fallback på gamla). 
2. **Agent-entiteter:** exportera `.claude/agents/*.md`-frontmatter som grafnoder.
3. **Arbets-kanter:** traversera befintliga `node:<slug>`-labels på issues/milestones till kanter.
4. **Levande lager:** GitHub Actions skriver beräknade fält + scorecard-check vid push.
5. **Zoom-vy:** dashboard-filter per `c4_level` (drill-down på `part_of`).

## Öppna beslut (för nästa spec-pass)

1. Inför `domain` som ny toppnivå över system — ja/nej?
2. `owner_agent` på noder: ska agenter vara förstklassiga grafentiteter nu, eller fält först?
3. Bygga zoom-vyn i nuvarande ReactFlow, eller generera Structurizr-DSL som separat vy?
4. Scorecard/health: minimalt CI-check nu, eller vänta tills schemat satt sig?

## Avgränsning
Detta är riktning + målschema, inte byggspec. Nästa steg: ett spec-pass som låser schema-tillägget
och första migrerings-issuen (rimligen under epic #7 "Work-modell & taxonomi" eller ett nytt
initiativ "Modell-evolution"). Källor i sessionens research-rapporter (Backstage, c4model.com,
Structurizr, Port/Cortex/OpsLevel, Team Topologies, ddd-crew, Backstage System Model).
