---
cost_sek: 4000
created: '2026-05-25'
depends_on: []
family: digest-pipeline
feeds: []
kind: component
mvp_stage: hypothesis
part_of: pipeline-extern
roi_percent: 250
slug: scoring-studio
stage: idea
status: idea
summary: Visuellt verktyg för att justera scoring-vikter i Changelog Engine Mini utan
  att redigera kod.
tags:
- devtools
- digest-pipeline
- scoring
- config
- static-site
title: Scoring Studio
updated: '2026-05-25'
value_sek: 14000
---

## Syfte

## Beroenden

## Status

## Nästa steg

## Risker

## Arbetslogg

## Anteckningar

## Problem

Scoring-vikterna i Changelog Engine Mini är hårdkodade i `weights.ts`. Varje justering kräver att man öppnar koden, hittar rätt konstant, ändrar ett värde och committar. Under en månads drift har vikterna behövt justeras flera gånger för att rätt ändringar ska ta sig igenom – för mycket filtreras bort som brus. Det finns inget sätt att se effekten av en viktändring utan att köra hela pipeline på nytt.

## Solution

Ett statiskt HTML-verktyg som läser aktuell `scoring.config.json` från Changelog Engine Mini-repot, låter användaren justera vikter och nyckelord visuellt, och exporterar en ny JSON-fil redo att committas. På sikt: live preview mot senaste digest-data som visar vilka events som hade inkluderats med de nya vikterna.

## Target Audience

**Primary:** Mig själv – som underhåller DocsWatch + Changelog Engine Mini-pipeline och behöver justera scoring utan att gå in i koden.

## Assumptions to Validate

- Att flytta `DEFAULT_WEIGHTS` till en extern `scoring.config.json` inte bryter befintlig pipeline.
- Att en visuell editor för vikter ger tillräcklig kontroll utan att exponera hela TypeScript-strukturen.
- Att export-till-JSON + manuell commit är ett acceptabelt arbetsflöde för MVP – ingen backend behövs.
- Att live preview mot befintlig digest-data är värdefullt nog att motivera steget efter MVP.

## Why Buy Instead of Build?

- Eliminerar friktionen att justera scoring – från "öppna kod, hitta konstant, ändra, committa" till ett formulär med slider och spara-knapp.
- Gör pipeline-underhåll möjligt utan att ha utvecklingsmiljön öppen.
- Skapar ett stabilt konfigurationslager som framtida features (fler vikter, nyckelord, dampeners) kan bygga på.

## MVP Steps

- Hypothesis: verifiera att `DEFAULT_WEIGHTS` kan externaliseras till `scoring.config.json` utan att pipeline-beteendet förändras.
- Solution test: använd den statiska editorn för att göra en verklig viktjustering, utvärdera om det är snabbare och mindre friktionsfyllt än att redigera koden direkt.
- Demand test: kontrollera om verktyget faktiskt används vid nästa behov av viktjustering, eller om gamla vanor tar över.
- Launch: publicera som statisk sida under digest-pipeline-familjen, länka från Changelog Engine Mini README.

## Cost Estimate

Uppskattat till 4 000 SEK – externalisering av config i TypeScript-koden (1 dag) plus statisk HTML-editor med export (1–2 dagar). Ingen infrastruktur, ingen backend.

## Value Estimate

Uppskattat till 14 000 SEK – sparad tid och friktion vid scoring-justeringar, plus ett stabilt konfigurationslager för framtida features i digest-pipeline.

## ROI

(14 000 - 4 000) / 4 000 = 250%

## Risk Assessment

- **Technical** (score 2/5): Externaliseringen av `DEFAULT_WEIGHTS` är ett litet ingrepp i befintlig kod men kräver att CLI:t läser filen korrekt och faller tillbaka på defaults utan att krascha.
- **Ops** (score 2/5): Config-filen måste versionshanteras i repot – annars försvinner justeringar vid nästa pull. Kräver tydlig konvention för var filen bor.
- **Technical** (score 3/5): Live preview mot digest-data kräver att editorn kan ladda och re-scorea events i browsern – det är ett större steg och tillhör inte MVP.

## Timeline

- Vecka 1: Externalisera `DEFAULT_WEIGHTS` till `scoring.config.json` i Changelog Engine Mini. Verifiera att pipeline fungerar identiskt.
- Vecka 2: Bygg statisk HTML-editor – formulär för kind-vikter, keyword-lista, dampener-patterns. Export till JSON.
- Vecka 3: Testa i verklig situation – gör en justerings-session med editorn istället för kod. Utvärdera friktion.
- Vecka 4: Publicera, länka från README. Besluta om live preview är nästa steg.

## Notes

Beroende på Changelog Engine Mini (`src/scoring/weights.ts`) – externalisering måste göras där först. Scoring Studio är ett verktyg i digest-pipeline-familjen, inte ett fristående projekt. Koden lever troligen i dev-changelog-engine-mini-repot som en `/studio`-undermapp eller som en separat statisk sida i samma GitHub Pages-deploy. Live preview är ett tydligt steg-2-feature och ingår inte i MVP.
