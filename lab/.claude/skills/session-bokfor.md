---
name: session-bokfor
department: Program
description: Registrera session-start, fork och avslut korrekt i CNS session-store.
---

# Session-bokföring

Alla AI-arbetspass ska registreras. Det ger överlappsdetektion, sessionsträd och pollbara signaler.

## Session-start

Kör i början av varje arbetspass:

```python
session = cortxt_start_session(
    summary="[Vad detta pass ska åstadkomma]",
    link_kind="issue",  # "quest", "node", "idea"
    link_ref="[id]",
    source="code"  # eller "chat"
)
# Spara session["id"] — du behöver det vid avslut
```

## Fork (om du forkar ut ett delproblem)

```python
fork = cortxt_fork_session(
    parent_id="[din session-id]",
    fork_name="[agent]: [uppgift]",
    summary="[vad forken gör]",
    link_kind="issue",
    link_ref="[id]"
)
```

## Session-avslut

Kör ALLTID när du är klar:

```python
cortxt_mark_session_done(
    session_id="[din session-id]",
    summary="[Vad som levererades, vad som återstår]"
)
```

Eller kombinerat:

```python
cortxt_save_session(
    summary="[Slutsats + vad som levererades]",
    link_kind="issue",
    link_ref="[id]",
    status="done"
)
```

## Pollbar signal

`status: running` → `status: done` är en signal som andra sessioner kan vänta på via `/loop`.

En session med `status: running` >45 min utan `updated_at`-ändring = troligen hängande.

## Överlappsdetektion

```
/cns-sync  ← kör innan du börjar om du är osäker på om annan session jobbar på samma nod
```

Sedan:
```
/cns-flush ← spola ner slutsatsen när du är klar
```
