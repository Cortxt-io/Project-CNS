# Plan: Work-modell för 100-agent-skala — byta ut eller bygga om de 5 substantiven?

## Context

Rikard driver CNS-agenturen solo som människa men med **100+ AI-agenter mot ett delat repo**. Frågan: ska de 5 work-item-substantiven (issues/quests/ideas/projects/sessions) bytas ut för att passa det? Tidigare svar ("behåll + minimalt", grundat i small-team-agile/Linear/Shape Up) vilade på fel premiss — den flaskhalsen är *mänsklig kognitiv last*, inte *maskinkoordination vid hög samtidighet*. Rikard korrigerade detta korrekt. Denna plan vilar på rätt korpus: **multi-agent-systemkoordination + distribuerade task-queues + storskalig repo-koordination.**

Belägg från live-situationen detta pass: en bakgrundsagent pushade förbi en "vänta"-grind; 4+ agenter svarade parallellt på samma /btw. Det *är* 100-agent-koordinationsfelet i miniatyr.

---

## Research-syntes (källbelagd)

**1. CNS har redan RÄTT makroarkitektur — blackboard/shared-state.** Den dominerande multi-agent-patternen är *blackboard*: en central delad minnesyta där agenter postar/läser och koordinerar **indirekt** (inte peer-to-peer), vilket frikopplar agenter och gör det lätt att lägga till/ta bort specialister. CNS = GitHub (delad sanning) + MCP (read/write-gränssnitt) = en blackboard. ([Petelin/Medium](https://medium.com/@dp2580/building-intelligent-multi-agent-systems-with-mcps-and-the-blackboard-pattern-to-build-systems-a454705d5672), [agent-blackboard](https://github.com/claudioed/agent-blackboard)). Slutsats: substantiven är inte fel *axel* — arkitekturen är redan rätt.

**2. Det som saknas är samtidighetsprimitiver på work item-nivå**, exakt det subagenter saknar: *delad task-lista med dependency-tracking + fil-låsning* ([Agent Teams / Augment](https://www.augmentcode.com/guides/git-worktrees-parallel-ai-agent-execution)). CNS har task-listan (issues) men:
   - `depends_on` finns bara på **noder**, inte på work items → orchestratorn kan inte dela ut oberoende slices säkert.
   - ingen **claim/lease/owner** → två agenter kan ta samma issue (samma write-kollision vi såg).

**3. Distribuerad task-queue-claiming är det lösta mönstret:** worker tar lock/lease med TTL + heartbeat; *optimistisk låsning* (UPDATE status WHERE open → 0 rader = redan tagen); idempotensnycklar ([techinterview](https://www.techinterview.org/post/3233474183/system-design-distributed-task-scheduler-cron-job-delayed-execution-priority-queue-exactly-once-celery-temporal-airflow/)). CNS sessions har `running→done` (pollbar signal — redan multi-agent-native) men work items saknar claim/lease/idempotens.

**4. DoR/DoD INVERTERAR för agenter.** Small-team-rådet "DoR = antimönster" gällde människor som undviker vattenfall. För LLM-arbetare är **maskinläsbara acceptanskriterier essentiella** och förhindrar att fel sak byggs: binära, testbara, fokuserade, Given/When/Then, "ersätt adjektiv med siffror", ange unhappy paths. "Evals are the new acceptance criteria." ([faherty](https://medium.com/@eamonn.faherty_58176/bringing-dor-and-dod-to-ai-coding-agents-why-your-ai-needs-clear-definitions-too-ba7a72d774d8), [earezki](https://earezki.com/ai-news/2026-06-03-i-changed-how-i-write-acceptance-criteria-and-my-ai-agent-stopped-building-the-wrong-thing/), [Addy Osmani](https://addyosmani.com/blog/good-spec/)). Spec-artefakten ska alltså vara *maskinläsbara acceptanskriterier*, inte en mänsklig pitch.

**5. Worktree-isolation räcker inte vid 100 agenter.** Även med worktrees är ~3–5 parallella gränsen innan merge-komplexitet på hotspot-filer (routes/configs/registries) ([MindStudio](https://www.mindstudio.ai/blog/git-worktrees-parallel-ai-coding-agents)). Skala kräver task-level dependency-DAG + claiming för att *partitionera* arbetet, inte bara isolera det. CNS använder redan worktrees.

**6. Anthropics varning (ärlig motvikt):** domäner där alla agenter måste dela samma kontext ELLER har många inbördes beroenden passar **dåligt** för multi-agent — då betalar man 15× token-kostnaden utan att tjäna in den ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)). Implikation: work-modellens *viktigaste* jobb är att partitionera arbete i **oberoende** slices. Dependency-DAG:en finns för att hålla beroenden FÅ, inte för att fira dem.

---

## MÄTNING (mät-först, beslutat) — arbetet är INTE parallell-format ännu

Faktisk arbetsfördelning 2026-06-10 (read-only via MCP):
- **Öppna issues: 8 → 7 på noden `agentur`, 1 på `shopify-venture`.** 87,5 % på EN nod.
- **Sessioner: ~alla länkar till `agentur`** (överlappsfrågan `link_ref=agentur` ger massiv överlapp — c3119c20, 01ac736a, 9ccd75ab, 92e7d989, 40730d9f m.fl.).

**Slutsats:** agenturens arbete är i dag extremt koncentrerat och sammanflätat på en nod, inte en bred uppsättning oberoende slices. Det är precis Anthropics anti-mönster för multi-agent-parallellism (delad kontext / många beroenden → 15×-kostnad utan vinst). 100 agenter på dagens backlog skulle alla stapla på `agentur` och krocka — vilket är exakt vad de parallella agenterna detta pass *gjorde*.

**Konsekvens för designen:** en 100-agent claim/lease-layer (B) är **rätt målarkitektur men för tidig nu**. Flaskhalsen är inte claim-kontention vid skala — det är att arbetet inte är dekomponerat i oberoende enheter alls. Lease-lagret har inget att koordinera förrän arbetet kan partitioneras.

## Rekommendation (reviderad av mätningen): bygg dekompositions-primitiverna FÖRST, lease-lagret NÄR arbetsformen kräver det

De 5 är rätt nouns OCH rätt arkitektur (blackboard). Det som ändras vid 100-agent-skala är inte taxonomin utan att work item-lagret behöver **distribuerad-task-queue-semantik** ovanpå. Fyra additiva primitiver:

1. **Claim/lease/owner på issues** — vilken agent äger den nu, med TTL/heartbeat så en död agents arbete frigörs. Optimistisk låsning (assignee + ett `claimed_at`/lease, eller en lättviktig lease i Redis som CNS redan kör för eventstream). Detta löser write-kollisionen direkt.
2. **Dependency-DAG på work item-nivå** — `depends_on` på issues (speglar nodmodellens relation), så orchestratorn delar ut oberoende slices och undviker hotspot-krockar.
3. **Maskinläsbara acceptanskriterier** på issues (binära, Given/When/Then, unhappy paths) — agent-DoD:n som hindrar fel-bygge. Detta ÄR spec-grinden, men maskinläsbar, inte en mänsklig pitch.
4. **Litet typ-fält** (task/bug/spike) — blygsamt, för routing/filtrering.

**Öppen designfråga (kärnan):** kan GitHub Issues bära claim/lease/heartbeat alls? Issues är ingen task-queue — assignee+labels är svaga claim-primitiver, ingen TTL. Två vägar:
- **(A) Augmentera issues** med claim-fält + depends_on + acceptanskriterier (håller "GitHub = sanning", stabilt connector-kontrakt).
- **(B) Lägg ett dedikerat claim/lease-lager** (Redis-lease, som CNS redan har för eventstream) BREDVID issues: issues förblir den synliga artefakten, men live-claimen lever i koordinationslagret. Närmare ett riktigt distribuerat task-queue, men ett nytt primitiv.

Detta är "delvis byta ut" snarare än "behåll allt orört" — vilket är närmare ditt instinkt än mitt förra svar.

---

## Branschstandard-nomenklatur (Rikard: "ner mot branschstandard")

Ärlig revidering — tre av de 5 ÄR icke-standard:

| CNS idag | Branschstandard | Åtgärd |
|---|---|---|
| `issues` / `todos` | issue/story/task / sub-task | ✅ behåll — redan standard |
| `quests` | **epic** (el. initiative) | byt etikett — "quest" är gamification utan branschgrund |
| `projects` (noder) | **component/system/service-katalog** | byt etikett — "project" krockar med PM-"projekt"; konceptet (emergent kind) behålls |
| `ideas` | **opportunity** (dual-track) | byt etikett — opportunity är discovery-standardtermen |
| `sessions` | **run** (agent work-pass) | CNS-native; ev. "run" — ingen ren standard finns |

Plus typ-lagret som saknas: `issue.type ∈ {story,bug,spike,chore}` + hierarki `initiative > epic > story > sub-task`.

**Två skilda lager:** (1) *begreppsmodell* (noder/docs/agent-prompts/taxonomi) kan flyttas till standard fritt; (2) *MCP-verktygsnamn* (`cortxt_create_issue`…) är connector-kontrakt mot claude.ai — rename bryter integration + kräver re-auth (CLAUDE.md). Vokabulär kan standardiseras utan att röra tool-namnen.

## Caveat (ärlig)
- Källorna är branschpraxis + verktygsdesign + (för DoR/DoD-för-agenter) 2026-bloggar och ett par primärkällor (Anthropic). **Ingen empirisk studie** mäter detta vid 100-agent-skala — det är ett ungt fält. Behandla som välgrundad riktning, inte bevisad lag.
- Anthropic-varningen är den starkaste motvikten: om agenturens arbete är tungt sammanflätat passar massiv parallellism dåligt oavsett datamodell — då är lösningen färre, bredare agenter, inte en finare task-queue.

---

## Beslut (Rikard)
- **Koordinationslager:** B — dedikerat Redis-lease-lager (issues förblir synlig artefakt).
- **Parallell-premiss:** mät först → **mätt: arbetet är koncentrerat/sammanflätat (87,5 % på `agentur`)**, så lease-lagret är rätt mål men inte den akuta flaskhalsen.
- **Nomenklatur:** ner mot branschstandard (quest→epic, projects→components, ideas→opportunities; behåll issues/todos; sessions→run).
- **Omfattning:** spec:a målmodellen FÖRST — ingen rename/kod förrän specen är granskad.

## Deliverable: granskningsbar spec (detta är nästa steg att utföra)

Skriv `Project-CNS/plans/work-model-taxonomy-spec.md` (CNS spec-konvention, jfr `cns-tui/plans/tui-agentur-spec.md`). Innehåll:

1. **Mål-taxonomi (branschstandard):** hierarki `initiative > epic > story > sub-task` + `issue.type ∈ {story,bug,spike,chore}`; `opportunity` (discovery-backlog); `component`-katalog (= dagens noder, emergent kind behålls); `run` (= dagens session, pollbar work-pass).
2. **Exakt rename-mappning** CNS→standard, i två lager: (a) begreppsmodell/docs/agent-prompts (byts nu), (b) MCP-tool-namn (connector-kontrakt — alias-skikt, deferred rename).
3. **Koordinations-primitiver (additivt på work items):** `depends_on` (dependency-DAG på issue-nivå), maskinläsbara acceptanskriterier (binära/Given-When-Then/unhappy paths), `type`-fält.
4. **Lease-lager (B), deferred:** Redis-lease med TTL+heartbeat ovanpå issues (återanvänd CNS befintliga Redis/`eventstream.py`); optimistisk claim. Markeras som mål-arkitektur, byggs när arbetet faktiskt dekomponerats i oberoende slices.
5. **Dekomposition först:** eftersom mätningen visar koncentrerat arbete — specens första praktiska steg är att göra arbetet dekomponerbart (depends_on + acceptanskriterier), inte att bygga lease-lagret.
6. **Migreringsplan:** additiv, bakåtkompatibel (nya fält valfria; gamla fält fallback så dashboarden inte bryts), en sak i taget.
7. **Berörda filer:** `scripts/issues_client.py` (type/depends_on/acceptanskriterier), `scripts/session_store.py` (run-vokabulär), `scripts/eventstream.py` (lease, deferred), `app/tools/*` (alias-lager), `schemas/`, CLAUDE.md. **Öppna frågor** ställs i specen för Rikards svar (spec-först-regeln).

**Verifiering (när specen senare implementeras):** prototyp `depends_on` + acceptanskriterier på en issue; för lease-lagret — kör 2 agenter mot samma issue och bekräfta att bara en tar claimen.

Specen ÄNDRAR ingen kod — den är ett granskningsdokument. Implementering följer först efter att Rikard godkänt specen.

---

## Öppna frågor — BESVARADE av Rikard
1. **initiative-toppnivå:** JA, lägg till nu (`initiative > epic > story > sub-task` fullt ut).
2. **sessions→run:** JA byt term till `run` i begreppsmodellen; MCP-tool-namnen (`cortxt_*_session`) behålls som connector-alias (ingen hård rename → bryter ej claude.ai). Vokabulärbyte nu, tool-namn deferred.
3. **acceptanskriterier:** body-konvention som speglar todos (`## Acceptans`-block, Given/When/Then, parsat likt `_TODO_RE`).
4. **sekvens:** bekräftad — dekomposition (type + depends_on + acceptanskriterier) FÖRST; lease-lager (B) deferred tills parallellkörning faktiskt drar igång.

5. **Linear:** ÅTERINFÖRT — parallellt med GitHub via **native integration, GitHub kanon** (research-grundat: undvik dubbelriktad dup, "never let the same item live in both"). Linear = människo-board/triage-UI + PR-automatik; GitHub = sanning för work items (CNS issues). **Ingen egenbyggd sync-kod.** Linears native GitHub-integration konfigureras i Linear (OAuth, välj Project-CNS-repot) — en manuell engångsåtgärd på Rikards sida. Befintliga `cortxt_*_linear`-verktyg kvarstår som komplement.

**Åtgärd (mig):** dokumentera beslutet i spec + issue #33 (Linear återinförd, native/GitHub-kanon, ingen sync-kod). **Åtgärd (Rikard):** aktivera Linear↔GitHub native integration i Linears inställningar.

**GitHub förblir sanning** genom hela modellen — taxonomi-ändringarna (type/depends_on/acceptanskriterier som body-konvention, quest→epic i vokabulär) läggs PÅ GitHub Issues/Milestones; inget lämnar GitHub.

**Nästa åtgärd:** uppdatera spec-dokumentet (branch `spec/work-model-taxonomy`) så öppna frågorna (1–4) är lösta enligt besluten + Linear utgår, sen publicera specen som GitHub wiki-sida och pusha branch-uppdateringen.

## Synliggörande (Rikard: "jag ser inte spec")

Specen låg bara som fil på branchen `spec/work-model-taxonomy` → osynlig i dashboard/MCP. **Beslut: publicera som CNS wiki-sida** (`cortxt_write_wiki_page`), som syns i dashboarden och nås via `cortxt_read_wiki_page`. Branch-filen finns kvar som källa. Detta är nästa åtgärd att utföra: skapa wiki-sida "Work-Model-Taxonomi-Spec" med specens innehåll + de 4 öppna frågorna.
