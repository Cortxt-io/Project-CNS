---
cost_sek: 4000
created: '2026-05-20'
mvp_stage: hypothesis
roi_percent: 275
slug: cns-devlog
status: idea
tags:
- devtools
- openai
- digest
- internal
- python
title: CNS DevLog
updated: '2026-05-20'
value_sek: 15000
summary: Genererar daglig AI-sammanfattning av portföljförändringar, publicerad som statisk sida.
family: internal-monitoring
---

## Problem

Ingen automatisk sammanfattning av vad som faktiskt hänt i portföljen dag för dag - framsteg, blockers och nästa steg är osynliga.

## Solution

Daglig AI-sammanfattning av cns-devwatch-output med OpenAI, publicerad som statisk sida.

## Target Audience

**Primary:** Mig själv - portföljägare som vill ha en daglig digest utan att öppna varje fil.

## Assumptions to Validate

- cns-devwatch-output är strukturerad nog att fungera som prompt-input till OpenAI utan manuell redigering.
- En daglig AI-sammanfattning på 200–400 ord ger tillräcklig kontext för att prioritera nästa steg per projekt.
- Statisk HTML-sida är tillräcklig leveransform – ingen notifiering eller push-mekanism behövs för MVP.
- OpenAI-kostnaden per dag håller sig under 1–2 SEK vid normal portföljstorlek (5–10 projekt).

## Why Buy Instead of Build?

## MVP Steps

- Hypothesis: verifiera att cns-devwatch-output kombinerat med en enkel prompt ger en läsbar och användbar daglig sammanfattning.
- Solution test: kör dagligen i en vecka, utvärdera om sammanfattningen faktiskt speglar vad som gjorts och vad som är kvar.
- Demand test: kontrollera om sidan faktiskt öppnas och används för prioritering, eller ignoreras.
- Launch: publicera som GitHub Pages, koppla till GitHub Actions-pipeline tillsammans med cns-devwatch.

## Cost Estimate

Uppskattat till 4 000 SEK – utvecklingstid för Python-skript + prompt-engineering + GitHub Pages-setup. OpenAI API-kostnad försumbar (< 50 SEK/månad).

## Value Estimate

Uppskattat till 15 000 SEK – daglig klarhet över portföljstatus utan manuell genomgång, bättre prioriteringar, mindre kognitiv overhead.

## ROI

(15 000 - 4 000) / 4 000 = 275%

## Risk Assessment

- **Technical** (score 3/5): Promptkvalitet avgör värdet helt. Dålig prompt ger generiska sammanfattningar som inte tillför något utöver att läsa filerna direkt.
- **Ops** (score 3/5): Pipeline-beroendet på cns-devwatch är hårt – om devwatch inte kör eller ger tom output, kör devlog på inaktuell data utan varning.
- **Technical** (score 2/5): OpenAI API-anrop kan misslyckas tyst. Felhantering och fallback måste in tidigt annars publiceras tom sida.

## Timeline

- Vecka 1: Implementera grundläggande prompt + OpenAI-anrop, testa med hårdkodad devwatch-output.
- Vecka 2: Koppla till verklig cns-devwatch-output, iterera prompt tills sammanfattningen är användbar.
- Vecka 3: Bygg statisk HTML-renderer, publicera manuellt till GitHub Pages.
- Vecka 4: Automatisera hela pipeline via GitHub Actions. Lägg till felhantering och fallback.

## Notes

Koden lever i prompt-cns/scripts/ tills vidare – inget eget repo. Beroende på cns-devwatch för input och OpenAI API-nyckel (finns tillgänglig). Output är en statisk HTML-sida, samma mönster som dev-changelog-engine-mini. Designprincip: AI är ett verktyg i pipeline, inte produkten.