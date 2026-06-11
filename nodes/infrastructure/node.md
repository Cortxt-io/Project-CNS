---
created: '2026-06-07'
depends_on: []
feeds: []
kind: system
part_of: cortxt
slug: infrastructure
stage: working
status: idea
summary: Infrastruktursystem — drift, hosting, webhooks och lagring.
type: infra
domain: cortxt
tags: []
title: Infrastructure
updated: '2026-06-07'
---

## Syfte/mål

Infrastruktursystem — drift, hosting, webhooks och lagring.

## Ingående komponenter

- **webhook-router** (building) — Self-hosted proxy som loggar, söker och replayer inkommande webhooks.
- **cortxt-eventstream** (idea) — Enhetlig händelselogning av alla systemaktiviteter med sex dimensioner.
- **cns-hosting-infra** (working) — GitHub Actions-infrastruktur som kör hela CNS-pipelinen automatiskt utan lokal dator.
- **cns-vault-app** (working) — Flask-webapplikation som exponerar CNS via webb med portföljöversikt, projektsidor och AI-review i webbläsaren.

## Dataflöde

- cortxt-eventstream → cns-devlog (extern)
- cortxt-eventstream → cns-brief (extern)

## Hälsa

## Systemrisker

## Arbetslogg

## Anteckningar
