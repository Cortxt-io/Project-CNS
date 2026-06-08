---
created: '2026-06-08'
updated: '2026-06-08'
slug: github-webhook
title: GitHub Webhook Receiver
kind: component
part_of: infrastructure
stage: working
status: early_mvp
feeds: [quest-engine, cortxt-eventstream]
depends_on: [cns-core]
summary: HMAC-verifierad mottagare på /api/webhook/github som auto-completar quests och loggar commits/PR/CI till eventstream.
tags: []
url_live: ''
url_repo: https://github.com/rian010194/Project-CNS
---

## Syfte

Endpoint /api/webhook/github i Flask-appen som tar emot GitHub-events (push, pull_request, workflow_run), verifierar HMAC mot CNS_WEBHOOK_SECRET, och: (1) auto-transitionerar matchande quests, (2) loggar normaliserade events till eventstream (Redis). Triggern som binder GitHub-aktivitet till CNS.

## Beroenden

- depends_on cns-core
- feeds quest-engine (auto-övergångar) och cortxt-eventstream (event-loggning)

## Status

Working. Hanterar push (filväg → slug → completion), PR (fritext-slug → start/complete) och workflow_run (CI-status).

## Nästa steg

## Risker

- **Technical**: Inte att förväxla med webhook-router (fristående devtool) — namnkrock som lätt vilseleder.
- **Technical**: PR/workflow_run saknar fillista, matchar slug via fritext — risk för fel- eller missad matchning.

## Arbetslogg

## Anteckningar

Gränsfall: detta är en endpoint i samma Flask-app som cns-vault-app och kan alternativt vara en rad i den nodens text. Egen nod motiverad av eget secret, egen setup och rollen som trigger för quest-automationen.
