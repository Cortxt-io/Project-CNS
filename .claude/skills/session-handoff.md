---
name: session-handoff
description: Hur du överlämnar ett pågående arbete till en annan agent via session-fork med fullständigt handoff-dokument.
---

# /session-handoff

## Syfte
Strukturera överlämning av ett pågående arbete till en annan agent (eller nästa session) så att kontexten inte tappas och nästa agent kan starta utan frågor.

## När du använder den
- Du har gjort din del och nästa steg tillhör en annan agent
- En lång session forkas ut till en specialistagent (t.ex. Ekonomen lämnar vidare till Backend-agent)
- Parallella agenter ska köra delar av ett uppdrag och du orkestrerar återsamlingen
- Session avslutas men arbete återstår — lämna underlag för nästa pass

## Steg

1. **Spara nuläget** med `cortxt_save_session` innan du forkar:
   ```
   cortxt_save_session(
     summary="[Vad som gjorts] + [Vad som återstår]",
     link_kind="issue" | "quest" | "node",
     link_ref="[id]",
     status="running"   # om arbetet fortsätter i fork
   )
   ```

2. **Skapa fork** för nästa agent med `cortxt_fork_session`:
   ```
   cortxt_fork_session(
     parent_id="[din session-id]",
     fork_name="[agent-namn]: [kort uppgiftsbeskrivning]",
     summary="[Vad forken ska göra och leverera]",
     link_kind="issue" | "quest" | "node",
     link_ref="[id]"
   )
   ```

3. **Formulera handoff-dokumentet** (se Output-format nedan) och inkludera `fork-id` från steg 2.

4. **Vid parallella forkar** (flera agenter samtidigt):
   - Varje fork får sin egna `cortxt_fork_session`
   - Inga överlappande ansvar — en fil/uppgift ägs av exakt en agent
   - Dokumentera ägarskap explicit i varje forks `summary`

5. **Återsamling** när parallella agenter är klara:
   - Kör `/cns-sync` för att detektera om sessioner överlappar på samma nod
   - Kör `/cns-flush` för att spola ner slutsatsen i CNS

## Output-format

```
HANDOFF TILL: [agent-namn]
SESSION-FORK: [fork-id från cortxt_fork_session]
PARENT-SESSION: [din session-id]
LÄNK: [link_kind]/[link_ref]

UPPGIFT: [Exakt vad nästa agent ska göra — en tydlig mening]

KONTEXT:
  Klart:       [lista över vad som redan är gjort]
  Återstår:    [lista över vad som ska göras]
  Blockerare:  [lista, eller "inga"]
  Beslut tagna:[relevanta beslut eller antaganden som gjorts]

FÖRVÄNTAT RESULTAT: [Vad nästa agent ska leverera när den är klar]
MARKERA DONE: [Vad som ska stå i cortxt_mark_session_done-summary när klart]
```

## Exempel

Ekonomen har analyserat kostnader och lämnar vidare till Scripts-agent för att implementera tröskelvärden:

```
HANDOFF TILL: scripts-agent
SESSION-FORK: session-a3f812cc
PARENT-SESSION: session-9d21b4e0
LÄNK: issue/42

UPPGIFT: Implementera GUL/RÖD-trösklar i ekonom_tracker.py baserat på beslutad spec

KONTEXT:
  Klart:       Kostnadsanalys klar, trösklar beslutade (GUL >200k, RÖD >500k Haiku-normaliserat)
  Återstår:    Lägga till threshold-logik i ekonom_tracker.py + uppdatera exports/ekonom_stats.json-schemat
  Blockerare:  Inga
  Beslut tagna: Haiku-normalisering används, inte absoluta tokens; buffert 50 %

FÖRVÄNTAT RESULTAT: Fungerande threshold-check i ekonom_tracker.py med test
MARKERA DONE: "ekonom_tracker threshold implementerad — GUL/RÖD live"
```
