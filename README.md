cat > README.md << 'EOF'
# CNS — Central Node Store

A local-first system for modelling a product portfolio.
`catalog.yaml` is the single source of truth. `decisions/` holds durable decision prose.
`cns.py` is the CLI.

## Daily workflow

```bash
pip install -r requirements.txt

python cns.py validate              # validate the whole catalog
python cns.py validate <slug>       # validate one system
python cns.py new <slug>            # add a new system to catalog.yaml
python cns.py export <slug>         # export a decision brief (Markdown)
python cns.py export <slug> --format=json   # JSON output
# python cns.py export <slug> --with-llm   # reserved: agent enrichment (not in Core v1)
```

## Architecture layers

### CNS Core

The minimal, self-contained layer. No network calls, no agents required.

| Path | Role |
|---|---|
| `catalog.yaml` | Node model — all systems + graph |
| `decisions/<slug>.md` | Decision prose per system |
| `schemas/` | Enum definitions, used by validate |
| `cns.py` | CLI: `validate`, `new`, `export` |
| `requirements.txt` | Core dependencies only |
| `tests/` | Core test suite |

### CNS Lab / Agency

The R&D layer for AI agency, dispatch, MCP and the Flask backend.
Lives in `lab/`. Not required for Core. See [`lab/README.md`](lab/README.md).

Includes: `agents/`, `skills/`, `sessions/`, `scripts/`, `app/`, `config/`, `.claude/`, `CLAUDE.md`.

## Parked features

These are intentionally out of scope for Core v1:

- **TUI / Control Tower** — `cns.py tui` (moved to lab)
- **Dispatch loop** — `lab/scripts/dispatch.py`
- **MCP server** — `lab/app/` + `lab/config/mcp_servers.json`
- **Session management** — `lab/sessions/`
- **Flask backend / Railway deploy** — `lab/Procfile`, `lab/railway.json`

## Archive

Historical artefacts in `archive/`: old `nodes/`, generated `exports/`, `research/` notes, `docs/`.

## Design principles

- **GitHub is the source of truth** — AI content is pushed via the GitHub API.
- **Derive, don't store** — `kind` and health emerge from structure; never hand-set.
- **One canonical model** — CNS owns the model; dashboards and other tools are projection targets.
- **Core first** — Lab/Agency is activated on top of Core, never the other way around.
EOF

git add README.md
git commit -m "docs: rewrite README for Core v1 — Core/Lab/Archive split, new daily workflow"