# Spec: Agenturens routing-modell — flöde + bemanning per (venture, disciplin, typ, station)

> Spec-pass 2026-06-11 (session b14c794b). **Granskningsutkast — ingen kod.** Foundational: definierar hur
> arbetet routas till rätt agentur→department→squad→lead→agenter, med rätt verktyg och modell. Löser
> samtidigt session-typ-driften (de 7 platta typerna).

## Kontext / varför
Session-typ-jakten avslöjade att de 7 koda typerna (brainstorm/spec/bygg/triage/review/verktygsladan/retro)
är drift — de blandar tre saker: faser, en löpande aktivitet (triage=refinement), och en arbetsdomän
(verktygsladan). Roten är inte "fel namn" utan att det **saknas en routing-modell**: en "session/run" är inte
en typ man väljer, utan `(work-item, station)` som routas och bemannas. Insikten: flödet OCH bemanningen
beror på mer än en etikett — på arbetstyp, disciplin, och vilken organisation som äger arbetet.

PR #88 löste redan det *akuta* (sessionstyp följer arbetet, ingen 28h-felstämpel). Detta spec adresserar
*fundamentet*: agenturens operativsystem — multi-venture-redo.

## Modellen: fyra selektionsnivåer (route uppifrån ner)
```
1. VENTURE        → AGENTUR             väljare: node.domain (cortxt / shopify-venture / research-venture …)
                                        idag: 1 produktutvecklings-agentur; designat för N (inkl. ren research-venture)
2. DISCIPLIN      → DEPARTMENT → SQUAD  väljare: node.type (frontend/service/backend/deploy/infra/…)
3. ARBETSTYP      → FLÖDE (stationer)   väljare: issue.type (story/bug/spike/chore)
4. STATION+KOMPLEX→ LEAD + AGENTER, VERKTYG, MODELL   väljare: aktuell station + komplexitet
```
`route(node.domain, node.type, issue.type, station) → (agentur → department → squad → lead → agenter, verktyg, modell)`

**Flöde-per-typ (station-väg, exempel — produktutvecklings-agentur):**
| issue.type | stationer |
|---|---|
| spike | discovery |
| bug / chore | delivery → review |
| story | definition → delivery → review |
| epic/initiative | discovery → definition → (stories) → review → retro |
Grindar mellan stationer (DoR/DoD, acceptanskriterier) finns redan i work-model-researchen.

## Den kritiska generaliseringen: agenturen är KONFIGURERBAR
Routing-**mekanismen** är generisk; **innehållet** deklareras per agentur. Ett research-venture har andra
discipliner (ej frontend/backend) och andra stationer (ej delivery-till-drift, utan t.ex. fråga → metod →
fynd → syntes). Produktutveckling och research är två *instanser* av samma mekanism med olika konfig:
- **per-agentur-konfig:** dess departments/discipliner, dess flöde-per-issue.type (stationer), dess squads/leads.
- **generisk mekanism:** de fyra selektionsnivåerna ovan + parameterisering. Hårdkoda aldrig frontend/discovery —
  de hör till produktutvecklings-agenturens *konfig*, inte mekanismen.

## Befintliga primitiver att komponera (inte bygga från noll)
- `node.domain` (cortxt/shopify-venture, #45/#48) = **venture/agentur-väljaren** — multi-venture redan i datat.
- `node.type` (#45/#48) = **disciplin-signalen** → department/squad.
- `issue.type` (story/bug/spike/chore, `issues_client`) = **flödes-signalen**.
- `exports/agents.json` (#46) bär redan **department / sub_department / squad / status / model** per agent.
- Agent-frontmatterns `## Tillåtna verktyg` (least-privilege) = verktygsytan per agent/squad.
- `model:` per agent + **modell-router #79** = modell-dimensionen (Haiku/Sonnet/topp per station+komplexitet).
- `router.py` gör idag grov nyckelords-routing → detta gör den principiell (route ur typ+domän+station, ej bara ord).
- Ägarskap: `agile-coach` (squad-formning/flöden), `org-arkitekt` (strukturens korrekthet) — finns redan.

## Vad "session/run" blir (löser session-typ-driften)
En run = `(work-item, station)`, routad+bemannad av funktionen. De 7 typerna upplöses:
brainstorm→discovery-station; spec→definition; triage→refinement *inom* definition; bygg→delivery;
review→review; retro→retro/eval; **verktygsladan→ ingen egen typ** (det är delivery på en agentur-nod, dvs
agenturen som bygger på sig själv — samma mekanism, domän=agency). Aktiv-typ-markören blir aktiv-*station*.

## Öppna frågor (besvaras i granskning, före kod)
1. **Var bor agentur-konfigen?** En `agentur`-nod med departments/squads/flöden i frontmatter, eller en egen
   entitet (`agenturer/<slug>.md`) som agents.json projiceras ur? (Plan A/B-väggen gäller.)
2. **Är "agentur" = node.domain, eller ett eget lager ovanför domän?** (En domän kanske har flera agenturer, eller tvärtom.)
3. **Stationer som data:** ska flöde-per-typ deklareras (konfig) eller härledas? Hur representeras en stations-väg maskinläsbart?
4. **Hur långt nu vs senare:** detta är stort. Vilken skiva byggs först (sannolikt: route → squad+modell ur node.type/issue.type, mot dagens enda agentur), och vad parkeras (multi-agentur, research-venture-konfig)?
5. **Relation till #79 (modell-router) och #59 (dispatch):** routing-funktionen är överbyggnaden; #79 är modell-delen, #59 är exekveringen. Hur delas ansvaret?

## Migrering (additiv, en skiva i taget — bryt inget)
1. Spec granskas (denna). 2. Modellera EN agentur (dagens produktutveckling) som konfig-data. 3. route()-funktion
mot node.type/issue.type → squad+modell, mot dagens roster. 4. Stationer som flöde-per-typ. 5. (Senare) multi-agentur
+ research-venture-konfig. 6. (Senare) koppla route() till dispatch (#59) + modell-router (#79).

## Avgränsning
- Bygger inget nu — granskningsdokument. Multi-agentur/research-venture är design-mål, inte v1-bygge.
- Hårdkodar aldrig en specifik agenturs discipliner/stationer i mekanismen.
- MCP-verktygsnamn (`cortxt_*`) orörda (connector-kontrakt). #88:s auto-station-härledning behålls/utökas, rivs ej.
