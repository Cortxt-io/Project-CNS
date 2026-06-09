---
created: '2026-06-09'
updated: '2026-06-09'
slug: agent-studio
title: Agent Studio
kind: component
part_of: interface
stage: building
status: early_mvp
feeds:
  - cns-mcp
depends_on:
  - cns-mcp
  - local-ai
summary: Interaktivt studio för att skapa, konfigurera och dokumentera agenter utan manuell JSON-redigering — via /agent-studio skill.
tags: []
url_live: ''
url_repo: ''
---

## Syfte

Agent Studio är det verktyg som skapar verktyg. Via `/agent-studio`-skillen
guidar Claude användaren genom ett agentval (syfte → modell → tools → eval-kriterier)
och producerar automatiskt:
1. En CNS-nod som dokumenterar agenten (`kind: component`, `part_of: agent-studio`)
2. En agentfil (`.claude/agents/<slug>.md`) klar att använda i Claude Code

Varje agent som skapas via studion blir en barn-nod till denna.

## Beroenden

- `cns-mcp` — MCP-verktygen agenten använder
- `local-ai` — Qwen/GLM-modeller för kodfokuserade agenter (deploy väntar på research)

## Status

MVP-fas. Skillen är implementerad och producerar korrekta artefakter.
Lokal AI-integration (Qwen/GLM) väntar på `nodes/local-ai/planning/local-ai-research.md`.

## Nästa steg

1. Besvara local-ai research-frågorna → aktivera `provider: qwen` i agentval
2. Utvärdera Claw Code som agent-host på Railway-servern (se Anteckningar)
3. Undersök GitHub Agents API — om stabilt: exportera agenter dit automatiskt
4. Lägg till `/agent-studio`-flow i TUI (ny skärm under tangent `a`)

## Risker

- **technical**: Qwen-modeller kräver VRAM som ännu inte kartlagts (lokal-ai-research)
- **ops**: .claude/agents/-filerna är maskinlokala — delning mellan maskiner kräver repo-commit

## Arbetslogg

## Anteckningar

**Claw Code vs Claude Agent SDK (beslutspunkt):**
Utvärdera Claw Code som agent-host på Railway-servern *innan* agent-creator-arkitekturen
låses för servern. Jämför: Claw Code (Railway-native?) / Claude Agent SDK (nuvarande
agent_host.py-ansats) / eget wrapper. Dokumentera valet här när det är fattat.

**GitHub Agents API:**
Undersök stabilitetsstatus vid nästa session som rör agent-infrastruktur. Om stabilt:
agentdefinitionerna i `.claude/agents/` kan exporteras dit med minimal mappning.
