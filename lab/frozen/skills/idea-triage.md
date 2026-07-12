---
name: idea-triage
department: Produkt
description: Fånga → triage → promote/resolve. Driver hela idélivscykeln; använder cns triage för grupperingen och cortxt_idea för åtgärderna.
---

# Idé-triage (form a — det drivande flödet, #39)

Triage är att göra den växande inkorgen **åtgärdbar**, inte bara läsbar. Grupperingen
(stale/mogna/kluster/otriagerade) görs av delad kod — `scripts/triage.group_ideas`, återanvänd
av MCP-batchverktyget (b) och TUI-vyn (c). Detta flöde är agentens omdöme ovanpå den grupperingen.

## Steg 1: Fånga direkt (när en tanke dyker upp)

Fånga medan den är färsk:

```python
cortxt_idea(action="capture", text="[fri text]", slug="[nod-slug om känd]",
            session_id="[aktiv session om känd]")
```

## Steg 2: Hämta grupperingen

Kör grupperingen — en läsning, redan sorterad i hinkar:

```
cns triage           # markdown-överblick
cns triage --json    # för programmatisk drift
```

Hinkar (ur `group_ideas`): **mature** (har slug + konkret kropp → promotkandidat) ·
**stale** (otriagerad + gammal → resolve/wontfix-kandidat) · **clusters** (flera öppna på samma
nod → besluta ihop) · **untriaged** (saknar nod).

## Steg 3: Döm varje hink mot matrisen

| Värde | Effort | Brådska | Åtgärd |
|-------|--------|---------|--------|
| Hög | Låg | Hög | Promote direkt |
| Hög | Låg | Låg | Promote till backlog |
| Hög | Hög | Hög | Promote, flagga operativ-chef |
| Hög | Hög | Låg | Behåll, ta upp vid planering |
| Låg | * | * | Resolve (wontfix) — promota ej |

## Steg 4: Utför (loop tills inkorgen är sorterad)

- **Mature → promote** (bara om kriterierna nedan är uppfyllda):
  ```python
  cortxt_idea(action="promote", idea_id="[id]", slug="[nod-slug]",
              title="[konkret titel: verb + substantiv]", body="[scope/acceptans]",
              quest_number=[epic # om passande])
  ```
- **Stale → resolve** (rensa bruset, behåll spåret):
  ```python
  cortxt_idea(action="resolve", idea_id="[id]", resolution="wontfix", reason="[varför]")
  ```
- **Clusters → besluta ihop:** läs alla på noden i en svep; promota det mogna, slå ihop dubbletter
  (resolve `duplicate` med `reason` som pekar på den kvarhållna), lämna resten.
- **Untriaged utan nod:** ge den en nod (fånga om med `slug`) eller resolve om den är överspelad.

## Promote-kriterier (en idé blir issue ENBART om)

- [ ] Titeln beskriver en konkret leverans (verb + substantiv)
- [ ] Det finns en rimlig nod (`slug`) och ev. epic att länka till
- [ ] Effort är inte "omöjlig att estimera"

## Vad du INTE promotar

- Vaga idéer ("förbättra agenturen", "gör det snabbare") — `group_ideas` håller dessa utanför
  *mature* (för korta eller markerade `riktningsfråga`); resolve eller låt mogna.
- Idéer som kräver ett arkitekturellt beslut som inte tagits — lyft i discovery/definition först.
