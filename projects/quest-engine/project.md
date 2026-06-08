---
created: '2026-06-08'
updated: '2026-06-08'
slug: quest-engine
title: Quest Engine
kind: component
part_of: infrastructure
stage: working
status: early_mvp
feeds: []
depends_on: [cns-core]
summary: Quest-livscykel (suggested → active → in_progress → completed/archived) med JSON-lagring, API och auto-övergångar — kopplar aktivitet till handling.
tags: []
url_live: ''
url_repo: https://github.com/rian010194/Project-CNS
---

## Syfte

Quest-systemet (quest_manager.py + /api/quests/*): skapar, uppdaterar och transitionerar quests genom en livscykel. Quests föreslås (manuellt eller från cns-brief), aktiveras, sätts in_progress och completas — delvis automatiskt via github-webhook (push/PR/CI). Lagras som JSON, pushas till GitHub.

## Beroenden

- depends_on cns-core
- Matas av github-webhook (auto-övergångar) och cns-brief (quest-förslag)

## Status

Working. Skapande, transitioner, board/detail-vyer och webhook-driven auto-completion på plats.

## Nästa steg

## Risker

- **Positioning**: Quests mappar inte rent mot något av de fem systemen — en orkestreringsprimitiv som skaver mot taxonomin. Kan signalera ett saknat workflow-systemlager, eller bara höra hemma i infrastructure.
- **Technical**: Slug-matchning för PR/workflow_run sker via fritextsökning i titel/branch — risk för falska träffar.

## Arbetslogg

## Anteckningar

Placeringen part_of: infrastructure är pragmatisk, inte självklar. Notera skavet; bygg inte om systemtaxonomin för en enda nod.
