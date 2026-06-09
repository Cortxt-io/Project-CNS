---
name: issue-lifecycle
description: Skapa, uppdatera och stäng GitHub-issues korrekt i CNS-systemet.
---

# Issue-livscykeln

## Skapa en issue

```python
cortxt_create_issue(
    title="[Verb + substantiv: 'Implementera X', 'Lägg till Y', 'Fixa Z']",
    body="## Bakgrund\n[varför]\n\n## Acceptanskriterier\n- [ ] [konkret krav]\n- [ ] [konkret krav]",
    labels=["node:<slug>"],  # koppla till nod
    milestone="[quest-titel]"  # koppla till quest om möjligt
)
```

**Titeln måste vara:** verb + substantiv, max 10 ord, inga vaga fraser som "förbättra" eller "kolla".

## Lägga till todos (delsteg)

```python
cortxt_add_todo(
    issue_number=42,
    text="[Konkret delsteg]"
)
```

Todos är `- [ ]`-checkboxar i issue-bodyn. Sanningen lever på GitHub.

## Stänga en issue

```python
cortxt_close_issue(
    issue_number=42,
    comment="Klart: [vad som levererades]"
)
```

**Stäng bara om:** acceptanskriterierna är uppfyllda, inte bara för att arbetet är gjort.

## Prioriteringsordning

1. Issues kopplade till aktiv quest/milestone — högst prioritet
2. Issues med label `node:<slug>` som är `stage: building` — näst högst
3. Orphan-issues (utan milestone) — lägst prioritet

## Vad du INTE gör

- Skapar aldrig issues utan tydliga acceptanskriterier
- Stänger aldrig issues utan att dokumentera vad som levererades
- Kopplar aldrig en issue till mer än en quest
