# Spec: Work-modell & branschstandard-taxonomi för CNS-agenturen

**Status:** GRANSKAD — öppna frågor 1–4 besvarade av Rikard (se §10). Ändrar ingen kod; implementering följer additivt per migreringsplanen.
**Datum:** 2026-06-10 · **Nod:** `agentur` · **Källa:** session-c3119c20 (verktygsladan)
**Scope-not:** Linear körs PARALLELLT med GitHub via Linears **native integration**, **GitHub kanon** (en sanning per item; ingen egenbyggd sync). GitHub förblir sanning; all taxonomi läggs PÅ GitHub Issues/Milestones.

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

> ÖPPEN FRÅGA 1: Vill Rikard ha `initiative`-toppnivån alls nu, eller räcker `epic` tills portföljen kräver det? (Anti-bloat: lägg till när ett verkligt behov finns.)
> ÖPPEN FRÅGA 2: `sessions→runs` — värt vokabulärbytet, eller behåll "session" som etablerad CNS-term? (Lågt värde, viss kostnad.)

---

## 5. Koordinationsprimitiver på work items (additivt)

1. **`type`** på issue: `story|bug|spike|chore` (default `story`). Billigt, icke-brytande; gör att discovery/delivery och velocity kan särskiljas.
2. **`depends_on`** på issue-nivå (lista av issue-nummer) — dependency-DAG så orchestratorn kan dela ut **oberoende** slices och undvika hotspot-krockar. Speglar nodmodellens `depends_on`.
3. **Maskinläsbara acceptanskriterier** på issue (strukturerat fält el. konvention i body): binära, Given/When/Then, unhappy paths, "ersätt adjektiv med siffror". Detta är agent-DoD:n — grinden in i bygge.

Alla tre additiva: nya fält valfria, gamla fält/flöden fallback (dashboarden bryts ej).

> ÖPPEN FRÅGA 3: Acceptanskriterier som strukturerat fält i issues_client, eller konvention i issue-body (likt todos `- [ ]`)? Body-konvention = mindre kod, GitHub-native; fält = maskinläsbart utan parsing.

---

## 6. Lease-lager (B) — DEFERRED målarkitektur

För 100-agent claim-koordination: Redis-lease med TTL + heartbeat ovanpå issues (återanvänd CNS befintliga Redis i `eventstream.py`); optimistisk claim (`UPDATE WHERE open` → 0 rader = redan tagen). Issues förblir synlig artefakt; live-claimen lever i koordinationslagret.

**Byggs INTE nu.** Mätningen (§2) visar att arbetet inte är dekomponerat i oberoende slices — lease-lagret har inget att koordinera än. Bygg det när `depends_on` + dekomposition gett genuint parallellt arbete.

> ÖPPEN FRÅGA 4: Bekräfta sekvensen — dekompositions-primitiver (§5) först, lease-lager (§6) när arbetsformen kräver det? Eller finns redan ett konkret 100-agent-scenario som motiverar lease-lagret omgående?

---

## 7. Migreringsplan (additiv, en sak i taget)

1. `type`-fält på issues (`scripts/issues_client.py`) — default `story`, fallback om saknas.
2. `depends_on` på issues (`issues_client.py`) — valfri lista.
3. Acceptanskriterier (per Öppen fråga 3).
4. Begreppsmodell-rename i docs/prompts/CLAUDE.md + alias-skikt i `app/tools/*` (connector-namn intakta).
5. `schemas/` uppdateras om enums berörs.
6. Lease-lager — separat spec när §6-sekvensen bekräftats.

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

## 10. Öppna frågor — BESVARADE av Rikard (2026-06-10)
1. **initiative-toppnivå:** ✅ JA, lägg till nu — full hierarki `initiative > epic > story > sub-task`.
2. **sessions→run:** ✅ JA, byt term till `run` i begreppsmodellen. MCP-tool-namnen (`cortxt_*_session`) behålls som connector-alias (ingen hård rename → bryter ej claude.ai); vokabulärbyte nu, tool-rename deferred.
3. **acceptanskriterier:** ✅ body-konvention som speglar todos — ett `## Acceptans`-block (Given/When/Then), parsat likt `_TODO_RE` i `issues_client.py`. GitHub-native, lite kod, maskinläsbart.
4. **sekvens:** ✅ bekräftad — dekomposition (type + depends_on + acceptanskriterier) FÖRST; lease-lager (B) deferred tills parallellkörning faktiskt drar igång (mätningen visar koncentrerat arbete, inget akut 100-agent-scenario).
5. **Linear:** ✅ ÅTERINFÖRT — parallellt med GitHub via **native integration, GitHub kanon** (research: undvik dubbelriktad dup, "never let the same item live in both"; [Linear Docs](https://linear.app/docs/github-integration)). Linear = människo-board/triage-UI + PR-automatik; GitHub = sanning för work items. **Ingen egenbyggd sync-kod** — Linears native GitHub-integration konfigureras i Linear (OAuth, välj Project-CNS-repot), manuell engångsåtgärd. Befintliga `cortxt_*_linear`-verktyg kvarstår som komplement.
