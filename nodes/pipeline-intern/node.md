---
created: '2026-06-07'
depends_on: []
feeds: []
kind: system
part_of: cortxt
slug: pipeline-intern
stage: working
status: idea
summary: Intern datapipeline — bearbetar och förädlar information internt.
tags: []
title: Pipeline Intern
updated: '2026-06-07'
---

## Syfte/mål

Intern datapipeline — bearbetar och förädlar information internt.

## Ingående komponenter

- **cns-brief** (working) — AI-driven portföljbrief som analyserar hela portföljen och föreslår dagens quest och prioriteringar baserat på devwatch, devlog och pending AI-förslag.
- **cns-devlog** (working) — Genererar daglig AI-sammanfattning av portföljförändringar, publicerad som statisk sida.
- **cns-devwatch** (working) — Bevakar dagliga git-ändringar i project.md-filer och exporterar dem som ChangeEvents.

## Dataflöde

- cns-devlog → cns-brief
- cns-devwatch → cns-devlog

## Hälsa

## Systemrisker

## Arbetslogg

## Anteckningar
