---
name: issue-lifecycle
description: "Skapa, uppdatera och stäng GitHub-issues korrekt i CNS-systemet. Använd när en GitHub-issue ska skapas, få todos eller stängas — \"skapa en issue för X\", \"stäng #42\", \"lägg till delsteg\". Och innan du stänger något: kontrollera acceptanskriterierna, inte bara att arbetet är gjort. Använd den INTE för PR:er — det är pr-protokoll."
---

<!-- GENERERAD ur vaulten — redigera INTE här.
     Källa: Ideaverse/Cortxt-io/Studio/Skills/issue-lifecycle.md
     Skriv om källnoten och kör `cns skill-export`. En riktning. -->

# issue-lifecycle

## Vad den gör

Skapa, uppdatera och stäng GitHub-issues korrekt i CNS-systemet.

## När den ska köras

Använd när en GitHub-issue ska skapas, få todos eller stängas — "skapa en issue för X", "stäng #42", "lägg till delsteg". Och innan du stänger något: kontrollera acceptanskriterierna, inte bara att arbetet är gjort. Använd den INTE för PR:er — det är [[pr-protokoll]].

## Verktyget

Allt går genom det feta verktyget `cortxt_issue(action=…)`. Actions: `list`, `get`, `create`, `close`, `move_to_quest`, `add_todo`, `check_todo`, `set_type`, `set_depends_on`, `add_acceptance`.

## Skapa en issue

```python
cortxt_issue(
    action="create",
    node_slug="<slug>",           # kopplingen till noden (krävs)
    title="[Verb + substantiv: 'Implementera X', 'Lägg till Y', 'Fixa Z']",
    body="## Bakgrund\n[varför]",
    quest_number=8,               # valfritt: quest (milestone) som int
    issue_type="story"            # story | bug | spike | chore
)
```

**Titeln måste vara:** verb + substantiv, max 10 ord, inga vaga fraser som "förbättra" eller "kolla".

## Acceptanskriterier

Given/When/Then-kriterier läggs som egna anrop — de är agentens DoD, skilda från todos:

```python
cortxt_issue(action="add_acceptance", number=42,
             given="[utgångsläge]", when="[handling]", then="[förväntat utfall]")
```

## Lägga till todos (delsteg)

```python
cortxt_issue(action="add_todo", number=42, text="[Konkret delsteg]")
cortxt_issue(action="check_todo", number=42, index=0, done=True)
```

Todos är `- [ ]`-checkboxar i issue-bodyn. Sanningen lever på GitHub.

## Stänga en issue

```python
cortxt_issue(action="close", number=42, result_summary="Klart: [vad som levererades]")
```

**Stäng bara om:** acceptanskriterierna är uppfyllda, inte bara för att arbetet är gjort.

## Prioriteringsordning

1. Issues kopplade till aktiv quest (milestone) — högst prioritet
2. Orphan-issues (utan quest) — lägst prioritet

## Vad du INTE gör

- Skapar aldrig issues utan tydliga acceptanskriterier
- Stänger aldrig issues utan att dokumentera vad som levererades
- Kopplar aldrig en issue till mer än en quest
