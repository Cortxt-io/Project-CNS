---
title: CNS Brief
slug: cns-brief
status: early_mvp
mvp_stage: solution_test
family: cns-core
cost_sek: 3000
value_sek: 20000
roi_percent: 567
tags:
- python
- claude
- portfolio
- decision-support
- dashboard
url_repo: https://github.com/rian010194/Project-CNS
url_live: https://app.cortxt.io
created: '2026-05-27'
updated: '2026-05-27'
summary: AI-driven portföljbrief som analyserar hela portföljen och föreslår dagens
  quest och prioriteringar baserat på devwatch, devlog och pending AI-förslag.
layer: pipeline
pipeline: pipeline-intern
---

## Problem

Portföljen har många projekt men inget system för att varje morgon veta vad som är viktigast att göra. Beslut fattas intuitivt utan att ta hänsyn till beroenden, pending förslag eller vad som faktiskt hände igår.

## Solution

portfolio_brief.py konsumerar hela portföljens data (project.md-filer, senaste devwatch-events, devlog-sammanfattning och pending AI-förslag) och skickar det till Claude som returnerar en strukturerad brief med situation, prioriteringar, blockers och ett konkret questförslag. Exponeras via /api/brief i Flask och visas som startsida i cortxt-dashboard-appen.

## Target Audience

**Primary:** Mig själv — portföljägare som vill starta varje dag med ett tydligt beslut istället för att orientera sig manuellt.

## Assumptions to Validate

- Claude kan ge meningsfulla handlingsbara prioriteringar baserat på portföljdata + devwatch + devlog.
- Quest-förslagen är relevanta nog att faktiskt användas som underlag för Qoder-prompts.
- "Visa underlag"-funktionen ger tillräcklig transparens för att lita på brief:en.
- Daglig användning av brief:en minskar tid på orientering och ökar fokus på execution.

## Why Buy Instead of Build?

- En AI-driven portföljbrief kan se beroenden och mönster som är svåra att se manuellt.
- Eliminerar den dagliga orienteringsfasen — direkt till beslut och execution.
- Grunden för framtida MCP-integration där agenter kan konsumera brief:en direkt.

## MVP Steps

- [x] Hypothesis: portfolio_brief.py kan generera en brief med situation, prioriteringar och questförslag.
- [x] Solution test: brief:en visas som startsida i cortxt-dashboard och genereras on-demand.
- [ ] Demand test: används brief:en faktiskt varje morgon för att fatta beslut?
- [ ] Launch: brief:en inkluderar devlog + devwatch som kontext, push-till-planning fungerar, underlag visas.

## Cost Estimate

3 000 SEK (ca 12h × 250 kr/h) — portfolio_brief.py
