---
name: session-bokfor
description: "Registrera session-start, fork och avslut korrekt i CNS session-store. Använd i början och slutet av varje AI-arbetspass — \"starta en session\", \"bokför det här passet\", \"markera klar\" — samt när en hängande running-session (>45 min utan uppdatering) behöver stängas. Alla AI-arbetspass ska registreras. Det ger överlappsdetektion, sessionsträd och pollbara signaler. Allt går genom det feta verktyget `cortxt_session(action=…)`. Actions: `start`, `done`, `save`, `list`, `fork`, `tree`."
---

<!-- GENERERAD ur vaulten — redigera INTE här.
     Källa: Ideaverse/Cortxt-io/Studio/Skills/session-bokfor.md
     Skriv om källnoten och kör `cns skill-export`. En riktning. -->

# session-bokfor

## Vad den gör

Registrera session-start, fork och avslut korrekt i CNS session-store.

## När den ska köras

Använd i början och slutet av varje AI-arbetspass — "starta en session", "bokför det här passet", "markera klar" — samt när en hängande running-session (>45 min utan uppdatering) behöver stängas.

Alla AI-arbetspass ska registreras. Det ger överlappsdetektion, sessionsträd och pollbara signaler.

Allt går genom det feta verktyget `cortxt_session(action=…)`. Actions: `start`, `done`, `save`, `list`, `fork`, `tree`.

## Session-start

Kör i början av varje arbetspass:

```python
session = cortxt_session(
    action="start",
    summary="[Vad detta pass ska åstadkomma]",
    link_kind="issue",  # "quest", "node", "idea"
    link_ref="[id]",
    source="code"  # eller "chat"
)
# Spara session["id"] — du behöver det vid avslut
```

## Fork (om du forkar ut ett delproblem)

```python
fork = cortxt_session(
    action="fork",
    parent_id="[din session-id]",
    summary="[vad forken gör]",
    link_kind="issue",
    link_ref="[id]"
)
```

## Session-avslut

Kör ALLTID när du är klar:

```python
cortxt_session(
    action="done",
    session_id="[din session-id]",
    summary="[Vad som levererades, vad som återstår]"
)
```

Eller kombinerat (start+avslut i ett svep, default `status="done"`):

```python
cortxt_session(
    action="save",
    summary="[Slutsats + vad som levererades]",
    link_kind="issue",
    link_ref="[id]"
)
```

## Pollbar signal

`status: running` → `status: done` är en signal som andra sessioner kan vänta på via `/loop`.

En session med `status: running` >45 min utan `updated_at`-ändring = troligen hängande.

## Överlappsdetektion

```
cortxt_session(action="list", link_ref=…)   ← kör innan du börjar: rör någon annan session samma nod?
```

Sedan:
```
cortxt_session(action="save", …)            ← spola ner slutsatsen när du är klar
```
