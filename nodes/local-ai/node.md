---
created: '2026-06-09'
updated: '2026-06-09'
slug: local-ai
title: Local AI
kind: component
part_of: infrastructure
stage: idea
status: idea
feeds:
  - cns-mcp
depends_on: []
summary: Lokal AI-inferens (Qwen/GLM via Ollama/LM Studio) som fallback och kodfokuserat komplement till Anthropic-modellerna.
tags: []
url_live: ''
url_repo: ''
---

## Syfte

Lokal AI-inferens som körs på datorns GPU/CPU — primärt Qwen 2.5-Coder och GLM 4 via Ollama eller LM Studio. Fyller tre roller:
1. **Fallback** när Anthropic API-credits tar slut eller API:t är nere.
2. **Kodfokuserat komplement** — Qwen 2.5-Coder presterar väl på kodfokuserade deluppgifter till lägre kostnad.
3. **Multilingual/research-komplement** — GLM 4 för innehåll där kinesisk/multilingual träning ger fördel.

Multi-modell-stödet är redan definierat i `schemas/agent-definition.schema.json` (provider-fältet: `qwen` | `glm`).

## Beroenden

## Status

Research-fas. Inget deployat. Deploy sker i separat session efter att research-frågorna i `planning/local-ai-research.md` besvarats.

## Nästa steg

1. Besvara research-frågorna i `planning/local-ai-research.md`.
2. Välj runtime (Ollama vs LM Studio vs llama.cpp) och modell-variant.
3. Bygg adapter i `agent_host.py` som ropar lokal Ollama-endpoint när `provider=qwen|glm`.

## Risker

- **technical**: VRAM-krav oklara — Qwen 2.5-Coder 7B kräver ~8 GB VRAM; större variant kräver 16–24 GB.
- **ops**: WSL2 vs native Windows påverkar GPU-passthrough och latens.
- **adoption**: Lokal inferens är långsammare och kräver uppvärmningstid; kan störa interaktiva sessioner.

## Arbetslogg

## Anteckningar
