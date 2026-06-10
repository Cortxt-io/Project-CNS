---
name: eskalera-uppat
department: Gemensam
description: Eskaleringsprotokoll — när och hur Ekonomen lyfter en röd budget eller arkitekturbeslut till Teamleader eller Rikard.
---

# /eskalera-uppat

## Syfte
Definiera när Ekonomen (eller annan agent) inte kan fatta beslut ensam och hur eskaleringsmeddelandet formulas så Teamleader eller Rikard kan fatta rätt beslut snabbt.

## När du använder den

Eskalera till **Teamleader** när:
- Ekonomen returnerar RÖD status (>500k tokens estimat, fan-out >5 agenter, Opus >2h)
- Uppgiften kräver koordination med fler än en agent och ingen äger orkestreringsansvaret
- Du saknar ett MCP-verktyg som krävs för uppgiften (rapportera luckan)
- Din tolkning av uppdraget är tvetydig och fel val kostar mycket

Teamleader eskalerar till **Rikard** när:
- Beslut ändrar arkitektur (ny datakälla, ny integration, ny agent)
- Kostnadsprojektionen är röd OCH osäkerhet finns om körningen är värd det
- Ingen agent i teamet har rätt kompetens — ny rekrytering krävs
- Körning i produktion med destruktiv effekt (delete, overwrite, deploy)

**Hoppa aldrig steg.** Du → Teamleader → Rikard.

## Steg

1. **Kör `/ekonomi-uppskattning` först** om du inte redan har en statusrapport. Eskalering utan kostnadsunderlag är ofullständig.

2. **Fastställ eskaleringsnivå** — Teamleader (koordination/kostnad) eller Rikard (arkitektur/destruktiv effekt).

3. **Formulera eskaleringsmeddelandet** med exakt format (se Output-format nedan).

4. **Vänta på beslut** — starta aldrig den dyra operationen tyst. Om Teamleader godkänner → kör. Om Rikard krävs → Teamleader eskalerar vidare.

5. **Återta kontrollen efter beslut:** när beslut är fattat — kör godkänd plan, eller avbryt och markera sessionen done med beslutet dokumenterat i `summary`.

## Output-format

```
ESKALERAR TILL: [operativ-chef | Rikard]
ANLEDNING: [varför du inte kan hantera detta ensam — ett konkret skäl]
KOSTNADSUNDERLAG: [STATUS från /ekonomi-uppskattning]
KONTEXT: [vad som redan gjorts eller är känt]
BESLUT SOM KRÄVS: [exakt vad som behöver beslutas — en eller max tre punkter]
ALTERNATIV: [billigare/enklare alternativ om ett sådant finns]
TIDSKÄNSLIGHET: [kan vänta | bör hanteras denna session | akut]
```

## Exempel

Ekonomen har kört `/ekonomi-uppskattning` på en deep-research-förfrågan:

```
ESKALERAR TILL: operativ-chef
ANLEDNING: Estimat röd — 850k tokens på Opus, överstiger månadsgräns
KOSTNADSUNDERLAG: RÖD ~850k tokens (Opus-syntes)
KONTEXT: Användaren bad om konkurrentanalys på tre bolag med djup syntes
BESLUT SOM KRÄVS: Godkänn Opus-körning (850k), eller kör förenklad Sonnet-version (400k)?
ALTERNATIV: Sonnet-syntes sparar ~450k tokens, täcker huvudfrågan men utan djupanalys
TIDSKÄNSLIGHET: kan vänta
```
