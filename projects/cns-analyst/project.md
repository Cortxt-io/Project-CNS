---
cost_sek: 5000
created: '2026-05-25'
current_slice: Run bulk analysis on scoring-studio, ai-ticket-triage, and cns-devwatch
  to validate precision and usability
family: cns-core
mvp_stage: demand_test
roi_percent: 400
slug: cns-analyst
status: mvp
summary: AI-driven analysmotor som föreslår uppdateringar av MVP-steg, risker och
  ROI-estimat per projekt.
tags:
- python
- openai
- cns-core
- analysis
title: CNS Analyst
updated: '2026-05-28'
value_sek: 25000
layer: pipeline
pipeline: pipeline-review
---

## Problem

CNS-projektfiler uppdateras manuellt och analyseras aldrig automatiskt. MVP-steg, riskbedömningar och ROI-estimat blir inaktuella tyst utan att någon märker det.

## Solution

cns analyze <slug> skickar hela project.md till OpenAI och returnerar strukturerade förslag på mvp_stage, current_slice, roi_percent, value_sek, cost_sek, risker och summary. Användaren godkänner eller avvisar i terminalen.

## Target Audience

**Primary:** Mig själv – portföljägare som vill ha AI-assisterad genomgång av projektfiler utan att lämna terminalen.

## Assumptions to Validate

- OpenAI returnerar strukturerad JSON tillräckligt konsekvent för att vara användbar utan manuell korrigering.
- Förslag på mvp_stage och risker är meningsfulla nog att faktiskt accepteras, inte bara avvisas.
- Flödet känns snabbt nog (< 10 sek) för att användas regelbundet.

## Why Buy Instead of Build?

## MVP Steps

- Hypothesis: verifiera att GPT-4o-mini returnerar användbara förslag på ett verkligt projekt.
- Solution test: kör cns analyze på 3–5 projekt, utvärdera träffsäkerhet per fält.
- Demand test: används analyze faktiskt regelbundet eller är det en one-off?
- Launch: stabil implementation med felhantering, ingår i normal CNS-workflow.

## Cost Estimate

5 000 SEK – Python-skript, prompt-engineering, felhantering. OpenAI API-kostnad försumbar (< 10 SEK/månad vid manuell användning).

## Value Estimate

25 000 SEK – sparad tid från manuell projektanalys, bättre kvalitet på MVP-steg och riskbedömningar, driver bättre prioriteringar.

## ROI

(25 000 - 5 000) / 5 000 = 400%

## Risk Assessment

- **Technical** (score 3/5): LLM-output kan vara inkonsekvent – JSON-parsning måste vara robust med tydlig felhantering.
- **Ops** (score 2/5): OpenAI-anrop kostar pengar och tid – bör inte köras automatiskt, alltid manuellt triggat.
- **Adoption** (score 3/5): Risk att verktyget blir en one-off utility istället för att integreras i regelbunden workflow – kräver att förslagen faktiskt är tillräckligt värdefulla för att accepteras.
- **Technical** (score 2/5): Bulk-analys av flera projekt samtidigt kan leda till rate limiting eller timeout-problem vid API-anrop – kräver retry-logik och progress tracking.

## Timeline

## Notes

Koden lever i scripts/analyst.py och scripts/file_watcher.py. Inga egna repos. Samma OpenAI-nyckel som devlog.py. Designprincip: AI föreslår, användaren bestämmer.
