---
cost_sek: 4500
created: '2026-05-11'
mvp_stage: hypothesis
roi_percent: 344
slug: project-vault-dashboard
status: idea
tags:
- portfolio
- dashboard
- static-site
- dataviz
- cns
title: Project Vault Dashboard
updated: '2026-05-11'
value_sek: 20000
---

## Problem
CNS och Project Vault lever i Markdown och CLI. Det finns ingen lättöverskådlig vy för en utomstående (eller framtida Rikard) att snabbt se vad som byggts, vad det kostat i tid, och vilket värde det levererat. Portföljöversikten kräver idag att man kör terminalkommandon och läser raw-filer.

## Solution
En statisk HTML-dashboard som läser JSON exporterad från CNS och presenterar alla projekt med status, MVP-steg, kostnad/värde/ROI och visuella indikatorer -- utan backend, utan ramverk.

## Target Audience
**Primärt:** Framtida arbetsgivare och kunder som besöker portföljen och vill se vad som byggts, till vilken kostnad, och med vilket resultat.

**Sekundärt:** Jag själv, för att hålla koll på vad som pågår, vad som kostar, och vad som levererar värde.

**Tertiärt:** Andra utvecklare som vill se hur Project Vault är strukturerat och inspireras av ett zero-framework dashboard-bygge.

## Assumptions to Validate
- CNS kan exportera ren JSON som är stabil nog att vara enda datakälla.
- Frontmatter-fälten är tillräckligt konsekventa för att renderas utan tung normalisering.
- En statisk sajt räcker -- server-side filter/sök behövs inte i MVP.
- Visuell portföljöversikt ger mätbart bättre intryck hos arbetsgivare/kunder.

## Why Buy Instead of Build?
- Skapar en visuell portfölj som kan delas med en URL istället för att kräva terminaltillgång.
- Eliminerar behovet av att förklara projektstrukturen muntligt vid intervjuer.
- Ger ett konkret bevis på förmåga att bygga frontend utan ramverk.

## MVP Steps
1. Ta fram JSON-export från CNS (`projects.json`) med en tydlig datamodell.
2. Bygga ett statiskt dashboard-skal (HTML/CSS/vanilla JS).
3. Visa en projekttabell med status, MVP-steg och ROI.
4. Lägga till 2-3 enkla grafer (ROI per projekt, statusfördelning, kostnad vs. värde).
5. Länka varje projekt till detaljvy eller extern dokumentation.
6. Dokumentera setup + deploy i README.

## Cost Estimate
Uppskattad totalkostnad: 4 500 SEK (ca 18 h x 250 kr/h).

| Steg | Timmar | SEK |
|------|--------|-----|
| JSON-export och datamodell | 3 | 750 |
| Dashboard-skal (HTML/CSS) | 4 | 1 000 |
| Projekttabell/kort | 3 | 750 |
| Visualiseringar (grafer) | 4 | 1 000 |
| Detaljvy + länkar | 2 | 500 |
| README + deploy | 2 | 500 |

## Value Estimate
Uppskattat värde: 20 000 SEK.

- Portföljen blir skummbar visuellt -- besökare stannar längre och förstår bredden snabbare.
- Konkret exempel på statisk dashboard utan ramverk fungerar som arbetsexempel vid intervjuer.
- Återanvändbart skal för framtida verktyg (Changelog Digest, AI-verktyg).
- Ger mig själv bättre portföljkontroll utan att behöva öppna terminalen.

## ROI
ROI = (värde - kostnad) / kostnad = (20 000 - 4 500) / 4 500 = 344 %

Estimerat ROI är 344 %, baserat på 20 000 SEK i portföljvärde och 4 500 SEK i tidskostnad.

## Risk Assessment
- **Market** (score 2/5): Dashboarden är främst för egen portfölj, låg extern marknadsrisk.
- **Technical** (score 2/5): Enkel stack (HTML/CSS/JS + JSON), inga tunga beroenden.
- **Competition** (score 1/5): Personlig portfölj, ingen direkt konkurrens.
- **Ops** (score 1/5): Statisk sajt utan server, minimalt underhåll.
- **Legal** (score 1/5): All data är min egen, inga tredjepartskrav.

Primära risker:
- **Datastabilitet:** Om frontmatter-formatet ändras i CNS måste export + dashboard uppdateras synkront.
- **Feature creep:** Risk att bygga fullfjädrad produkt istället för en enkel läsbar vy.
- **Designambition:** Risk att fastna i pixelperfektion innan funktionen finns.

## Timeline
- Vecka 1: Export-lager + datamodell + dashboard-skal.
- Vecka 2: Projekttabell + kort + visualiseringar.
- Vecka 3: Detaljvy + README + deploy.

## Notes
Fokusera på att dashboarden är ett lättviktigt fönster mot CNS-datan -- inte en ny produkt. Håll stacken minimal: ingen bundler, inget ramverk, ingen server. JSON-filen genereras av CNS och kopieras till dashboardens public-mapp vid deploy.
