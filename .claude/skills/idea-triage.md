---
name: idea-triage
department: Produkt
description: Fånga → triage → promote. Protokoll för hela idélivscykeln från tanke till GitHub-issue.
---

# Idé-triage

## Steg 1: Fånga direkt

Fånga medan tanken är färsk — tänk inte för länge:

```python
cortxt_capture_idea(
    text="[Fri text — tanken som den kom]",
    slug="[nod-slug om känd]",
    session_id="[nuvarande session-id om känd]"
)
```

## Steg 2: Triage-matris

| Värde | Effort | Brådska | Åtgärd |
|-------|--------|---------|--------|
| Hög | Låg | Hög | Promote direkt |
| Hög | Låg | Låg | Promote till backlog |
| Hög | Hög | Hög | Promote, flagga operativ-chefn |
| Hög | Hög | Låg | Spara, ta upp vid planering |
| Låg | * | * | Spara, promota ej |

## Steg 3: Promote (bara om kriterierna är uppfyllda)

**En idé får bli issue ENBART om:**
- [ ] Titeln beskriver en konkret leverans (verb + substantiv)
- [ ] Det finns en rimlig quest (milestone) att länka till
- [ ] Effort är inte "omöjlig att estimera"

```python
cortxt_promote_idea_to_issue(
    idea_id="[id]",
    title="[Konkret titel]",
    milestone="[quest-namn]",
    labels=["node:<slug>"]
)
```

## Vad du INTE promotar

- Vaga idéer: "förbättra agenturen", "gör det snabbare"
- Idéer utan tydlig avgränsning
- Idéer som kräver ett arkitekturellt beslut som inte tagits

## Batch-triage (för gamla idéer)

```python
ideas = cortxt_list_ideas(status="open")
# Gå igenom varje idé mot matrisen ovan
# Promota det som är redo, lämna resten
```
