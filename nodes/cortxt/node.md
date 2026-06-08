---
created: '2026-06-07'
depends_on: []
feeds: []
kind: framework
part_of: ''
slug: cortxt
stage: working
status: idea
summary: Verktygskedja för AI-assisterad produktutveckling — från idé till leverans.
tags: []
title: Cortxt
updated: '2026-06-07'
---

## Vision

Cortxt är en verktygskedja som binder samman idé, analys, genomförande och leverans i en enhetlig arbetscykel.

## Ingående system

- **infrastructure** (system, working) — Infrastruktursystem — drift, hosting, webhooks och lagring.
  - webhook-router (building)
  - cortxt-eventstream (idea)
  - cns-hosting-infra (working)
  - cns-vault-app (working)
- **interface** (system, working) — Gränssnittssystem — dashboarder, landing page och grafvy.
  - cortxt-graph-view (idea)
  - cortxt-dashboard-app (working)
  - cortxt-landing (working)
- **pipeline-extern** (system, idea) — Extern pipeline — hanterar utgående data och publicering.
  - scoring-studio (idea)
  - dev-changelog-engine-mini (working)
  - docs-watch (working)
- **pipeline-intern** (system, working) — Intern datapipeline — bearbetar och förädlar information internt.
  - cns-brief (working)
  - cns-devlog (working)
  - cns-devwatch (working)
- **pipeline-review** (system, working) — Granskningspipeline — analyserar och utvärderar projekt och data.
  - cns-analyst (working)

## Karta

## Riktning

## Principer

- Lokalt först, API valfritt
- Markdown är sanningen
- Additiv migrering, ej hård
- Kind följer struktur, inte spekulation

## Arbetslogg

## Anteckningar
