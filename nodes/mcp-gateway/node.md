---
created: '2026-06-09'
updated: '2026-06-09'
slug: mcp-gateway
title: MCP Gateway (router)
kind: component
part_of: infrastructure
stage: idea
status: idea
feeds: []
depends_on: [cns-mcp]
summary: Planerad separat router/gateway-process som aggregerar flera MCP-servrar bakom en endpoint med central auth, rate-limit och per-agent verktygsfiltrering. Idag ersatt av config-routern (.mcp.json) — byggs först när Plan B-agenter når många servrar i produktion.
tags: []
url_live: ''
url_repo: ''
---

## Syfte

En gateway/router-tjänst framför flera MCP-servrar: en endpoint för agenterna, med
central auth, rate-limit och verktygsfiltrering per agent. Ersätter på sikt config-routern
(`.mcp.json`), som räcker så länge det bara finns en handfull servrar och inga
produktionsagenter (Plan B) som behöver central styrning.

## Beroenden

- depends_on cns-mcp (gatewayen fronter den befintliga MCP-servern)
- Externt: en gateway/router-runtime (t.ex. mcp-router/gateway) + deploy bredvid Railway

## Status

idea — inte påbörjad. I dag är routern config-baserad: `.mcp.json` i repo-roten listar
servrarna. Noden finns för att lämna plats i strukturen utan att bygga något ännu.

## Nästa steg

- Verkligt behov: ≥3 MCP-servrar eller en Plan B-produktionsagent som kräver central auth/filtrering.
- Då: spec först (val av runtime, deploy, auth-modell mot befintlig GitHub-OAuth).

## Risker

- **Ops**: ny tjänst att drifta och övervaka — bygg inte förrän behovet är konkret.
- **Technical**: dubbel auth-yta (gateway + cns-mcp) måste hållas konsekvent.

## Arbetslogg

## Anteckningar
