---
name: ekonomi-uppskattning
description: Kostnadsmodell för agent-körningar — Haiku/Sonnet/Opus, token-budget, go/no-go.
---

# /ekonomi-uppskattning

## Syfte
Beräkna uppskattad token-kostnad för en planerad operation och returnera GRÖN/GUL/RÖD go/no-go med konkret rekommendation.

## När du använder den
- Innan en dyr operation startas: Workflow, deep-research, fan-out med fler än 5 agenter
- När du behöver välja modellnivå per delsteg i en plan
- När du fått en förfrågan som involverar flera parallella agenter
- Som underlag för `/eskalera-uppat` (röd budget kräver eskalering)

## Steg

1. **Inventera delstegen** — lista varje agentanrop som krävs (läs, skriv, analys, syntes).

2. **Tilldela modellnivå per steg** med dessa regler:
   - Haiku 4.5: mekaniskt arbete — hämtning, extraktion, läsning, enkla kontroller
   - Sonnet 4.6: omdöme — kodgenerering, analys, dokumentation, verifiering
   - Opus 4.8 (toppmodell): orkestrering, djup strategi, komplexa synteser — undvik annars

3. **Uppskatta tokens per steg:**
   - Varje fil som läses: 5–20k tokens
   - Varje skrivoperation/iteration: 10–30k tokens
   - Lägg på 50 % buffert

4. **Multiplicera med relativ modellkostnad:**

   | Modell | Relativ kostnad | Typisk användning |
   |--------|----------------|-------------------|
   | Haiku 4.5 | 1x | Orientering, läsning, enkel output |
   | Sonnet 4.6 | 10–15x | Kod, analys, dokumentation |
   | Opus 4.8 | 60–80x | Orkestrering, strategi |

   Tumregel: ett Opus-tänkesteg = ~10 Haiku-sessioner.

5. **Sätt status** baserat på total uppskattad token-kostnad (Haiku-normaliserat):
   - **GRÖN** — under 50k tokens totalt, eller Haiku-uppgift av valfri längd, eller Sonnet under 200k
   - **GUL** — Sonnet 200–500k, eller Opus för uppgift som borde vara Sonnet, eller 4–5 parallella sessioner
   - **RÖD** — över 500k tokens, eller Opus-session förväntad >2h, eller fan-out >5 agenter

6. **Vid GUL/RÖD:** presentera ett billigare alternativ och kräv explicit godkännande innan körning startas.

## Output-format

```
UPPSKATTNING: ~[X]k tokens ([Haiku/Sonnet/Opus per steg])
STATUS: GRÖN | GUL | RÖD
OBSERVATION: [ett konkret skäl till statusen]
REKOMMENDATION: [bara vid GUL/RÖD — konkret billigare alternativ]
```

Max 5 rader. Rapportera aldrig exakta kronor/dollar — enheterna är relativa estimat.

## Exempel

Förfrågan: "Kör deep-research på tre konkurrenter med Opus-syntes"

```
UPPSKATTNING: ~850k tokens (15 fetch@Haiku + 9 verify@Sonnet + 1 syntes@Opus)
STATUS: RÖD
OBSERVATION: Opus-syntes på 1 M+ tokens — motsvarar ~80 Haiku-sessioner i kostnad
REKOMMENDATION: Kör verify på Haiku istället för Sonnet → ~400k tokens (GUL). Godkänn innan start.
```
