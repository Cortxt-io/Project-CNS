# Designbeslut — Cortxt Graph View

## 1. Tre tillstånd
Översikt (allt synligt) / system-fokus (semantisk zoom, ej drill) / nod-fokus (dämpning + inspektor, ortogonalt mot zoom).

## 2. Edges
`part_of` ritas aldrig (containern är relationen); `feeds` alltid synlig; `depends_on` dämpad i översikt, full vid fokus.

## 3. Skala
Default allt-synligt, level-of-detail vid utzoom, valbar kollaps per system. Systemnamn = zooma in; separat chevron ▸/▾ = kollaps (krockar ej).

## 4. Layout
Hybrid — handplacerade system (ordning i frontend-config, ej noddata), auto-layout inom system.

## 5. Inspektor
Mall-medveten per `kind`:
- Komponent: Syfte / Beroenden / Status / Nästa steg / Risker
- System: Ingående komponenter / Dataflöde / Hälsa

Faller tillbaka på gamla sektioner endast om migreringen inte körts.
