---
created: '2026-05-31'
updated: '2026-06-08'
slug: cns-analyst
title: CNS Analyst
kind: component
part_of: pipeline-review
stage: working
status: mvp
feeds: []
depends_on: []
summary: AI-driven analysmotor som föreslår uppdateringar av stage, risker och summary.
tags: []
url_live: ''
url_repo: https://github.com/rian010194/Project-CNS
---

## Syfte

AI-driven analysmotor (`cns analyze <slug>`) som läser en hel project.md och föreslår uppdateringar av `stage`, risker och `summary` — användaren godkänner eller avvisar. AI föreslår, du bestämmer.

## Beroenden

## Status

## Nästa steg

## Risker

- **Technical**: LLM-output inkonsekvent, JSON-parsning måste vara robust.
- **Ops**: OpenAI-anrop kostar pengar och tid, alltid manuellt triggat.
- **Adoption**: Risk att bli engångs-utility istället för regelbunden workflow.
- **Technical**: Bulk-analys kan ge rate limiting/timeout, kräver retry-logik.

## Arbetslogg

## Anteckningar
