---
name: session-handoff
description: Hur du överlämnar ett pågående arbete till en annan agent via session-fork.
---

# Session-handoff

Använd när du ska överlämna ett pågående arbete till en annan agent — eller när en agent forkas ur din session.

## Handoff-protokollet

### 1. Spara ditt nuläge
```python
cortxt_save_session(
    summary="[Vad du gjort + vad som återstår]",
    link_kind="issue",  # eller "quest", "node"
    link_ref="[id]",
    status="running"  # om arbetet fortsätter i en fork
)
```

### 2. Skapa en fork för nästa agent
```python
cortxt_fork_session(
    parent_id="[din session-id]",
    fork_name="[agent-namn]: [uppgift]",
    summary="[Vad forken ska göra]",
    link_kind="issue",
    link_ref="[id]"
)
```

### 3. Formulera överlämningen

```
HANDOFF TILL: [agent-namn]
SESSION-FORK: [fork-id]
UPPGIFT: [exakt vad de ska göra]
KONTEXT:
  - Vad som är klart: [lista]
  - Vad som återstår: [lista]
  - Blockerare: [om några]
FÖRVÄNTAT RESULTAT: [vad de ska leverera]
```

## Parallell fork (flera agenter samtidigt)

Om du forkar till flera agenter:
- Varje fork får sin egna fork-session
- Markera tydligt vem som äger vad
- Inga överlappande ansvar — en fil/uppgift → en agent

## Återsamling

När parallella agenter är klara och du ska synka:
```
/cns-sync  ← detekterar om sessioner överlappar på samma nod
```

Sedan:
```
/cns-flush ← spola ner slutsatsen i CNS
```
