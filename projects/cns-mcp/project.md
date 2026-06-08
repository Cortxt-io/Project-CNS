---
created: '2026-06-08'
updated: '2026-06-08'
slug: cns-mcp
title: CNS MCP Server
kind: component
part_of: infrastructure
stage: working
status: early_mvp
feeds: []
depends_on: [cns-core]
summary: Remote MCP-server på Railway (GitHub OAuth, Redis-token-store) som exponerar CNS som verktyg för Claude — nåbar från telefon och webb.
tags: []
url_live: https://project-cns-production.up.railway.app/mcp
url_repo: https://github.com/rian010194/Project-CNS
---

## Syfte

MCP-server (app/mcp_server.py) monterad i Flask-appen via ASGI, nåbar på /mcp. Exponerar fem verktyg (list/get projects, list/get/complete quests) för Claude via claude.ai custom connector. Skyddas med GitHub OAuth (FastMCP GitHubProvider) eftersom claude.ai bara stödjer OAuth, inte statisk Bearer.

## Beroenden

- depends_on cns-core (verktygen läser noddata via parsern)
- Externt: FastMCP 3.4.2, Redis (token-store), GitHub OAuth-app

## Status

Working men ohärdad. Token-store i Redis med Fernet-kryptering + stabil JWT-signeringsnyckel (löste JTI-mapping-buggen vid worker-restart).

## Nästa steg

## Risker

- **Technical**: GitHubProvider släpper in vilken GitHub-användare som helst — allowlist på inloggat användarnamn behövs innan servern litas på, eftersom complete_quest muterar data och pushar.
- **Ops**: Rotation av JWT_SIGNING_KEY eller STORAGE_ENCRYPTION_KEY invaliderar alla tokens — varje connector måste återanslutas.

## Arbetslogg

## Anteckningar
