# Agent Studio — beslut & anteckningar

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
