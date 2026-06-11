---
created: '2026-05-02'
updated: '2026-06-08'
slug: webhook-router
title: Webhook Router
kind: component
part_of: infrastructure
stage: building
status: idea
feeds: []
depends_on: []
summary: Self-hosted webhook proxy that logs, searches, and replays incoming webhooks locally — an audit log for developers debugging webhook deliveries without SaaS cost.
type: service
domain: cortxt
tags: []
url_live: ''
url_repo: https://github.com/rian010194/webhook-router
---

## Syfte

Self-hosted webhook proxy that logs, searches, and replays incoming webhooks locally — an audit log for developers debugging webhook deliveries without SaaS cost. Previously framed as internal infra; repositioned as a standalone devtool.

## Beroenden

## Status

## Nästa steg

## Risker

- **Market**: Developers may not actively seek tools despite webhook debugging being painful.
- **Technical**: Proxy + SQLite is straightforward; correct handling of concurrent requests is the main risk.
- **Positioning**: Risk of being confused with Hookdeck/Convoy — requires clear "audit log, not platform" messaging.
- **Adoption**: Self-hosted requires own ops, higher threshold than SaaS.

## Arbetslogg

## Anteckningar
