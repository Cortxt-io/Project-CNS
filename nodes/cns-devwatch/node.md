---
created: '2026-06-07'
updated: '2026-06-08'
slug: cns-devwatch
title: CNS Devwatch
kind: component
part_of: pipeline-intern
stage: working
status: early_mvp
feeds:
- cns-devlog
depends_on: []
summary: Bevakar dagliga git-ändringar i project.md-filer och exporterar som ChangeEvents.
type: pipeline
domain: cortxt
tags: []
url_live: ''
url_repo: https://github.com/rian010194/Project-CNS
---

## Syfte

Bevakar dagliga git-ändringar i project.md-filer och exporterar dem som ChangeEvents — intern monitoring av portföljarbetet, input till cns-devlog.

## Beroenden

## Status

## Nästa steg

## Risker

- **Technical**: Glesa commits ger ingen diff-signal.
- **Ops**: Måste köras dagligen för att ge värde, faller annars i glömska.
- **Ops**: Output-format måste vara stabilt, annars bryts cns-devlog-integrationen.

## Arbetslogg

## Anteckningar
