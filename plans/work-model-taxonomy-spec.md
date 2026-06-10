# Spec: Work-modell & branschstandard-taxonomi för CNS-agenturen

**Status:** GRANSKAD — öppna frågor besvarade 2026-06-10 (se §10). Redo för implementering enligt §7.
**Datum:** 2026-06-10 · **Nod:** `agentur` · **Källa:** session-c3119c20 (verktygsladan)

---

## 1. Problem & mål

CNS work-item-modellen använder fem substantiv — `issues` / `quests` / `ideas` / `projects` / `sessions` — varav flera **inte är branschstandard**. Samtidigt drivs agenturen mot **100+ AI-agenter mot ett delat repo**, vilket ställer krav som dagens modell inte uttrycker (claim, beroenden, maskinläsbara grindar).

Mål: en **branschstandard-taxonomi** + de **koordinationsprimitiver** storskalig multi-agent-drift kräver — additivt och bakåtkompatibelt, utan att bryta "GitHub = sanning" eller connector-kontrakten mot claude.ai.

**Icke-mål:** att bygga lease-lagret nu (se §6, deferred); att döpa om MCP-verktygsnamn nu (se §4, alias-skikt).

---

## 2. Grundande underlag (källbelagt)

- **Blackboard-pattern:** CNS (GitHub-sanning + MCP read/write) ÄR redan den dominerande multi-agent-arkitekturen — delad minnesyta, indirekt koordination, frikopplade specialister. ([Petelin](https://medium.com/@dp2580/building-intelligent-multi-agent-systems-with-mcps-and-the-blackboard-pattern-to-build-systems-a454705d5672))
- **Saknade samtidighetsprimitiver:** delad task-lista med dependency-tracking + claim/lock — det subagenter saknar. ([Augment](https://www.augmentcode.com/guides/git-worktrees-parallel-ai-agent-execution))
- **DoR/DoD inverterar för agenter:** maskinläsbara, binära, Given/When/Then-acceptanskriterier förhindrar fel-bygge. ([faherty](https://medium.com/@eamonn.faherty_58176/bringing-dor-and-dod-to-ai-coding-agents-why-your-ai-needs-clear-definitions-too-ba7a72d774d8), [Addy Osmani](https://addyosmani.com/blog/good-spec/))
- **Standard-taxonomi:** `initiative > epic > story > sub-task` + spike (XP) + bug; Linears 4 typer; opportunity (dual-track discovery). ([Atlassian](https://www.atlassian.com/agile/project-management/epics-stories-themes), [Linear](https://linear.app/docs/conceptual-model), [Shape Up](https://basecamp.com/shapeup/0.3-chapter-01))
- **Anthropics varning:** tungt sammanflätat arbete passar dåligt för multi-agent (15× kostnad utan vinst). ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system))

**MÄTNING 2026-06-10:** 7/8 öppna issues på nod `agentur`; ~alla sessioner länkar `agentur`. Arbetet är **koncentrerat/sammanflätat**, inte parallell-format. → lease-lagret är rätt mål men inte akut; dekomposition är den verkliga flaskhalsen.

---

## 3. Mål-taxonomi (branschstandard)

| Begrepp | Definition | Mappar från CNS |
|---|---|---|
| **component** (katalog) | Produkt/system/tjänst i domänmodellen; `kind` emergerar ur struktur (behålls) | `projects` / noder |
| **opportunity** | Discovery-backlog — råfångad möjlighet/problem, ej åtagen | `ideas` |
| **initiative** | Stort mål som spänner flera epics (valfri toppnivå) | *(ny, valfri)* |
| **epic** | Grupp av relaterade stories mot ett mål | `quests` (GitHub Milestone) |
| **story / task / bug / spike / chore** | Atomisk arbetsenhet; `type`-fält | `issues` (+ nytt `type`) |
| **sub-task** | Delsteg i en story | `todos` (checkbox) |
| **run** | Agent-arbetspass; pollbar `running→done`-signal | `sessions` |

Spike = tidsboxad research (kunskap≠kod). Bug/chore estimeras ej. Hierarki och typer är **branschstandard**; `component` (emergent kind) och `run` (pollbar work-pass) är CNS-bidrag utan ren standard-motsvarighet — behålls medvetet.

---

## 4. Rename-mappning — TVÅ lager

**Lager 1 — begreppsmodell (byts nu, billigt):** docs, agent-prompts, sessionprofiler, CLAUDE.md, dashboard-etiketter. `quest→epic`, `projects→components`, `ideas→opportunities`, `sessions→runs`. `issues`/`todos` oförändrade.

**Lager 2 — MCP-verktygsnamn (deferred, dyrt):** `cortxt_create_issue` m.fl. är **connector-kontrakt mot claude.ai** — rename bryter integration + kräver re-auth (CLAUDE.md). Strategi: **alias-skikt** — nya standard-namn exponeras som alias, gamla namn lever kvar tills en planerad connector-migrering. Ingen hård rename i denna spec.

> **BESLUT 1 (2026-06-10):** `initiative`-toppnivån **läggs till nu** som valfri toppnivå över epic.
> **BESLUT 2 (2026-06-10):** `sessions→runs` **genomförs** — run-vokabulär i begreppsmodellen (Lager 1).

---

## 5. Koordinationsprimitiver på work items (additivt)

1. **`type`** på issue: `story|bug|spike|chore` (default `story`). Billigt, icke-brytande; gör att discovery/delivery och velocity kan särskiljas.
2. **`depends_on`** på issue-nivå (lista av issue-nummer) — dependency-DAG så orchestratorn kan dela ut **oberoende** slices och undvika hotspot-krockar. Speglar nodmodellens `depends_on`.
3. **Maskinläsbara acceptanskriterier** på issue (strukturerat fält el. konvention i body): binära, Given/When/Then, unhappy paths, "ersätt adjektiv med siffror". Detta är agent-DoD:n — grinden in i bygge.

Alla tre additiva: nya fält valfria, gamla fält/flöden fallback (dashboarden bryts ej).

> **BESLUT 3 (2026-06-10):** Acceptanskriterier som **body-konvention** (Given/When/Then i issue-body, likt todos `- [ ]`) — mindre kod, GitHub-native, sanningen lever på GitHub.

---

## 6. Lease-lager (B) — DEFERRED målarkitektur

För 100-agent claim-koordination: Redis-lease med TTL + heartbeat ovanpå issues (återanvänd CNS befintliga Redis i `eventstream.py`); optimistisk claim (`UPDATE WHERE open` → 0 rader = redan tagen). Issues förblir synlig artefakt; live-claimen lever i koordinationslagret.

> **BESLUT 4 (2026-06-10):** Lease-lagret **byggs nu, parallellt** med dekomposition. Avsteg från utkastets rekommendation (mätningen i §2 pekade mot att vänta) — motiverat av ett konkret scenario med agenter som redan krockar om samma uppgifter. **Förutsättning att bekräfta vid implementering:** dokumentera scenariot (vilka agenter, vilka issues krockar) så lease-designen dimensioneras mot verkligt behov, inte hypotetiskt.

**Designskiss (oförändrad):** Redis-lease med TTL + heartbeat ovanpå issues (återanvänd CNS befintliga Redis i `eventstream.py`); optimistisk claim. Egen detaljspec innan kod (se §7 steg 6).

---

## 7. Migreringsplan (additiv, en sak i taget)

1. `type`-fält på issues (`scripts/issues_client.py`) — default `story`, fallback om saknas.
2. `depends_on` på issues (`issues_client.py`) — valfri lista.
3. Acceptanskriterier som body-konvention (Beslut 3) — Given/When/Then i issue-body.
4. Begreppsmodell-rename i docs/prompts/CLAUDE.md + alias-skikt i `app/tools/*` (connector-namn intakta). Inkluderar `initiative` (Beslut 1, valfri toppnivå) och `sessions→runs` (Beslut 2).
5. `schemas/` uppdateras om enums berörs (bl.a. `type`-enum, ev. `initiative`).
6. Lease-lager — **egen detaljspec, byggs parallellt** (Beslut 4). Dokumentera krockscenariot först.

Varje steg: bakåtkompatibelt, validera mot dashboarden, commit en i taget.

---

## 8. Berörda filer
- `scripts/issues_client.py` — `type`, `depends_on`, acceptanskriterier
- `scripts/session_store.py` — ev. `run`-vokabulär (Öppen fråga 2)
- `scripts/eventstream.py` — lease (deferred, §6)
- `app/tools/{issues,quests,ideas,projects,sessions}.py` — alias-skikt (deferred rename)
- `schemas/` — ev. enums för `type`
- `CLAUDE.md` (Project-CNS + workspace) — begreppsmodell-rename

## 9. Verifiering (vid implementering)
- `type`/`depends_on`: skapa issue med typ + en depends_on-kant, läs tillbaka, bekräfta dashboard ej bryts.
- Acceptanskriterier: en agent läser kriterierna och kan avgöra done binärt.
- Lease (när byggt): kör 2 agenter mot samma issue → bara en tar claimen.

## 10. Öppna frågor — BESVARADE 2026-06-10
1. `initiative`-toppnivå nu eller vänta? → **Lägg till nu** (valfri toppnivå).
2. `sessions→runs` — byt eller behåll? → **Byt till run** (begreppsmodell, Lager 1).
3. Acceptanskriterier — strukturerat fält eller body-konvention? → **Body-konvention** (Given/When/Then).
4. Bekräfta sekvens dekomposition→lease, eller akut 100-agent-scenario? → **Lease byggs nu parallellt** (avsteg från §2-rekommendation; kräver dokumenterat krockscenario vid implementering).
