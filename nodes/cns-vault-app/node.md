---
created: '2026-06-07'
updated: '2026-06-08'
slug: cns-vault-app
title: CNS Vault App
kind: component
part_of: infrastructure
stage: working
status: early_mvp
feeds: []
depends_on: []
summary: Flask-app på Railway som exponerar CNS via webb med git som synkmekanism.
type: service
domain: cortxt
owner_agent: backend-utvecklare
tags: []
url_live: https://project-cns-production.up.railway.app
url_repo: https://github.com/rian010194/Project-CNS
---

## Syfte

Flask-app på Railway som exponerar CNS via webb — portföljöversikt, projektsidor och AI-review i webbläsaren, med git som synkmekanism (pull före läsning, commit+push efter skrivning).

## Beroenden

## Status

## Nästa steg

## Risker

- **Technical**: Git pull/push som synk kan ge konflikter vid samtidiga ändringar.
- **Ops**: Railway-appen sover på gratisplan — första laddning 30–60 s.
- **Technical**: CORS krävs för att dashboarden ska kunna anropa Railway-API:et.
- **Market**: Personligt verktyg, låg marknadsrisk.

## Arbetslogg

## Anteckningar
