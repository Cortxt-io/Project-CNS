---
name: ekonomi-uppskattning
description: Kostnadsmodell för agent-körningar — Haiku/Sonnet/Opus, token-budget, go/no-go.
---

# Ekonomi-uppskattning

## Relativa kostnader

| Modell | Relativ kostnad | Använd för |
|--------|----------------|------------|
| Haiku 4.5 | 1x | Enkla uppgifter, orientering, läsning, kompakt output |
| Sonnet 4.6 | 10–15x | Kodgenerering, analys, dokumentation |
| Opus 4.8 | 60–80x | Orkestrering, djup analys, strategiska beslut |

## Typiska sessions-kostnader

| Typ | Token-spann |
|-----|------------|
| Kort orientering/planering | 20–80k |
| Kodsession (läs, skriv, iterera) | 200–600k |
| Lång research / workflow | 500k–2M |

**Tumregel:** Varje Opus-tänkesteg = ~10 Haiku-sessioner. Undvik Opus för enkla uppgifter.

## Go/No-go-beslutsregler

**Grön (kör direkt):**
- Haiku-uppgift, oavsett längd
- Sonnet, <200k tokens uppskattning

**Gul (kolla med teamleadern):**
- Sonnet >300k tokens
- Opus för uppgifter som borde vara Sonnet
- 4+ parallella sessioner igång

**Röd (eskalera till Rikard):**
- Opus-session >2h
- Loop-mönster (samma uppdrag 3+ gånger)
- >5 parallella sessioner

## Hur du uppskatttar

1. Räkna antal filer som läses: varje fil ~5–20k tokens
2. Räkna antal skrivoperationer: varje Write-iteration ~10–30k tokens
3. Multipla med modellkostnad
4. Lägg på 50% buffert

Rapportera alltid i formatet:
```
UPPSKATTNING: ~[X]k tokens (Haiku/Sonnet/Opus)
STATUS: GRÖN | GUL | RÖD
```
