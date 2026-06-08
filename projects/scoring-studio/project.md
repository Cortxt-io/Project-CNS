---
created: '2026-06-07'
updated: '2026-06-08'
slug: scoring-studio
title: Scoring Studio
kind: component
part_of: pipeline-extern
stage: idea
status: idea
feeds: []
depends_on: []
summary: Visuellt verktyg för att justera scoring-vikter utan att redigera kod.
tags: []
url_live: ''
url_repo: ''
---

## Syfte

Visuellt verktyg för att justera scoring-vikterna i Changelog Engine Mini utan att redigera kod — läser `scoring.config.json`, låter dig ändra vikter och exporterar ny config.

## Beroenden

## Status

## Nästa steg

## Risker

- **Technical**: Externalisering av `DEFAULT_WEIGHTS` kräver att CLI:t läser config och faller tillbaka utan krasch.
- **Ops**: Config måste versionshanteras i repot, annars försvinner justeringar vid pull.

## Arbetslogg

## Anteckningar
