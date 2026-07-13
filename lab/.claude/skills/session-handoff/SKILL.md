---
name: session-handoff
description: "Hur du lämnar över ett pågående arbete till NÄSTA SESSION: en session-fork plus ett fullständigt handoff-dokument. Använd när sessionen tar slut men jobbet inte är klart — \"forka ut det här\", \"vi tar det nästa pass\", kontexten börjar bli full. Fork plus handoff-dokument, så nästa pass kan börja utan att fråga en enda fråga."
---

<!-- GENERERAD ur vaulten — redigera INTE här.
     Källa: Ideaverse/Cortxt-io/Studio/Skills/session-handoff.md
     Skriv om källnoten och kör `cns skill-export`. En riktning. -->

# session-handoff

## Vad den gör

Hur du lämnar över ett pågående arbete till NÄSTA SESSION: en session-fork plus ett fullständigt handoff-dokument.

## När den ska köras

Använd när sessionen tar slut men jobbet inte är klart — "forka ut det här", "vi tar det nästa pass", kontexten börjar bli full. Fork plus handoff-dokument, så nästa pass kan börja utan att fråga en enda fråga.

## Syfte

Strukturera överlämningen så att kontexten inte tappas mellan pass. Nästa session ska kunna läsa
dokumentet och gå direkt på arbetet — inte rekonstruera vad som hände.

## När du använder den

- Sessionen avslutas men arbete återstår
- Kontexten är full och arbetet behöver ett rent pass
- Ett spår grenar ut sig och förtjänar en egen session (fork under samma förälder)

## Steg

1. **Spara nuläget** med `cortxt_session(action="save", …)` innan du forkar:
   ```
   cortxt_session(
     action="save",
     summary="[Vad som gjorts] + [Vad som återstår]",
     link_kind="issue" | "quest" | "node",
     link_ref="[id]",
     status="running"   # arbetet fortsätter i forken
   )
   ```

2. **Skapa forken** för nästa pass:
   ```
   cortxt_session(
     action="fork",
     parent_id="[din session-id]",
     summary="[Vad nästa pass ska göra och leverera]",
     link_kind="issue" | "quest" | "node",
     link_ref="[id]"
   )
   ```

3. **Formulera handoff-dokumentet** (se Output-format nedan) och inkludera fork-id från steg 2.

4. **Vid flera parallella forkar:** varje spår får sin egen fork, inga överlappande ansvar — en
   fil/uppgift ägs av exakt ett spår. Dokumentera ägarskapet explicit i varje forks `summary`.

5. **Återsamling** när spåren är klara:
   - `cortxt_session(action="list", link_ref=…)` — se om andra sessioner rör samma nod
   - `cortxt_session(action="save", …)` — spola ner slutsatsen i CNS

## Output-format

```
HANDOFF TILL: nästa session
SESSION-FORK: [fork-id]
PARENT-SESSION: [din session-id]
LÄNK: [link_kind]/[link_ref]

UPPGIFT: [Exakt vad nästa pass ska göra — en tydlig mening]

KONTEXT:
  Klart:       [lista över vad som redan är gjort]
  Återstår:    [lista över vad som ska göras]
  Blockerare:  [lista, eller "inga"]
  Beslut tagna:[relevanta beslut eller antaganden som gjorts]

FÖRVÄNTAT RESULTAT: [Vad nästa pass ska leverera när det är klart]
MARKERA DONE: [Vad som ska stå i cortxt_session(action="done")-summary när klart]
```

## Exempel

Specen är skriven och beslutad; implementationen ryms inte i det här passet:

```
HANDOFF TILL: nästa session
SESSION-FORK: session-a3f812cc
PARENT-SESSION: session-9d21b4e0
LÄNK: issue/42

UPPGIFT: Implementera cross-repo-filtret i issues_client enligt beslutad spec

KONTEXT:
  Klart:       Spec skriven och granskad; API-formen (valfri repo-param, default GITHUB_REPO) beslutad
  Återstår:    Implementera param + test som täcker default-fallet och det explicita repo-fallet
  Blockerare:  Inga
  Beslut tagna: Additiv param, inte ny funktion — gamla anrop får inte bryta

FÖRVÄNTAT RESULTAT: Grön testsvit + draft-PR mot issue #42
MARKERA DONE: "cross-repo-filter implementerat, PR öppen"
```
