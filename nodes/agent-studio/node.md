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

**Claw Code vs Claude Agent SDK (utvärdering 2026-06-09):**
Claw Code är en open-source Python/Rust clean-room-reimplementering av Claude Code-arkitekturen.
Stödjer Claude, OpenAI och lokala modeller. Har Railway-template (ClaudeClaw) för 24/7-drift.

| | Claw Code | Claude Agent SDK |
|---|---|---|
| Lokala modeller | ✓ native | Kräver adapter |
| Railway-template | ✓ ClaudeClaw | Eget (agent_host.py) |
| Mognad | Ny, okänd stabilitet | Etablerad, testad |

**Beslut: Behåll Claude Agent SDK.** Claw Code är intressant för Qwen/GLM-integration men
lokal AI är ändå uppskjuten pga hårdvara (UHD 610, 1 GB VRAM). Återbesök när lokal AI-deploy
är aktuell — Claw Code kan ge enklare Ollama-integrationsväg då.

**GitHub Agents API:**
Undersök stabilitetsstatus vid nästa session som rör agent-infrastruktur. Om stabilt:
agentdefinitionerna i `.claude/agents/` kan exporteras dit med minimal mappning.
