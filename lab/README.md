# CNS Lab / Agency

This directory is the **R&D and agency layer** of CNS. It is not required to run CNS Core.

## Entrypoint

```bash
python lab/cns_lab.py -h          # full command surface (Core + Lab)
python lab/cns_lab.py tui         # Textual Control Tower
python lab/cns_lab.py dispatch --dry-run
python lab/cns_lab.py session list
```

`cns_lab.py` reuses the command functions defined in `cns.py` and adds the parked/advanced
registrations on top. It puts both the repo root and `lab/` on `sys.path` so the `scripts`
namespace package merges (Core modules in `scripts/`, Lab modules in `lab/scripts/`).

## What lives here

| Directory / file | Purpose |
|---|---|
| `cns_lab.py` | Lab/Agency CLI entrypoint |
| `scripts/` | dispatch loop, agent-host, MCP router, sessions, TUI, dashboard exporters |
| `agents/` | Role-based AI agents |
| `skills/` | Agent skill definitions |
| `sessions/` | Session profiles + artefacts |
| `app/` | Flask / FastMCP backend (Railway) |
| `config/` | MCP server configs + agenturer |
| `.claude/`, `.mcp.json` | Claude tooling + MCP manifest |
| `CLAUDE.md` | Deep architecture + conventions |
| `requirements-agent.txt` | Agent-specific dependencies |
| `Procfile` / `railway.json` | Agency backend deploy |

## Status

**Experimental / R&D.** CNS Core (`catalog.yaml`, `decisions/`, `cns.py`) runs independently.
The lab layer is activated on top of Core once a concrete use case justifies it.

## Future hook

`python cns.py export <slug> --with-llm` is reserved as the integration point where Core export
hands off to an agent in this layer for enrichment (report / course module). Not implemented in
Core v1.
