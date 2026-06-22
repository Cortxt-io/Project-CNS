# CNS — Central Node Store

A local-first system for modelling a product portfolio.
`catalog.yaml` is the single source of truth. `decisions/` holds durable decision prose.
`cns.py` is the Core CLI.

## Daily workflow

```bash
pip install -r requirements.txt

python cns.py validate              # validate the whole catalog
python cns.py validate <slug>       # validate one system
python cns.py new <slug>            # add a new system to catalog.yaml
python cns.py export <slug>         # export a decision brief (Markdown)
python cns.py export <slug> --format=json   # JSON output
# python cns.py export <slug> --with-llm    # reserved: agent enrichment (not in Core v1)
```

`python cns.py -h` shows exactly these three commands. Everything else is Lab/Agency.

## Architecture layers

### CNS Core

The minimal, self-contained layer. No network calls, no agents required.

| Path | Role |
|---|---|
| `catalog.yaml` | Node model — all systems + graph |
| `decisions/<slug>.md` | Decision prose per system |
| `schemas/` | Enum definitions, used by validate |
| `scripts/` | Core modules: `catalog`, `md_parser`, `validator`, `derive_catalog` |
| `cns.py` | Core CLI: `validate`, `new`, `export` |
| `requirements.txt` | Full backend dependency set (Flask, FastMCP, gunicorn, uvicorn, anthropic, redis, …) — installed by the Railway deploy and the export-dashboard CI; not Core-only |
| `railway.json` | Railway deploy config (NIXPACKS; runs `app.asgi` from `lab/` with both repo-root and `lab/` on `PYTHONPATH`) |
| `tests/` | Test suite (Core + Lab, via `tests/conftest.py`) |

`scripts/` (Core) and `lab/scripts/` (Lab) form one PEP 420 namespace package. Core never
imports from Lab; Lab may import Core. Running `cns.py` from the repo root only ever sees the
Core modules.

### CNS Lab / Agency

The R&D layer for AI agency, dispatch, MCP and the Flask backend. Lives in `lab/`, with its own
entrypoint:

```bash
python lab/cns_lab.py -h          # full command surface (Core + everything else)
python lab/cns_lab.py tui         # Textual Control Tower
python lab/cns_lab.py dispatch --dry-run
```

Not required for Core. See [`lab/README.md`](lab/README.md).
Includes: `agents/`, `skills/`, `sessions/`, `scripts/`, `app/`, `config/`, `.claude/`, `CLAUDE.md`.

## Parked features

Intentionally out of scope for Core v1 — reachable only via `lab/cns_lab.py`:

- **TUI / Control Tower** — `python lab/cns_lab.py tui`
- **Dispatch loop** — `lab/scripts/dispatch.py` (`python lab/cns_lab.py dispatch`)
- **MCP server** — `lab/app/` + `lab/config/`
- **Sessions / quests / PR client** — `lab/cns_lab.py session|quest|pr`
- **Dashboard exports** — `lab/cns_lab.py export-json|export-xlsx`
- **Flask backend / Railway deploy** — `lab/Procfile`, `lab/railway.json`

## Archive

Historical artefacts in `archive/`: old `nodes/`, generated `exports/`, `research/` notes,
`docs/`, and superseded `catalog.*.yaml` migration files.

## Design principles

- **GitHub is the source of truth** — AI content is pushed via the GitHub API.
- **Derive, don't store** — `kind` and health emerge from structure; never hand-set.
- **One canonical model** — CNS owns the model; dashboards and other tools are projection targets.
- **Core first** — Lab/Agency is activated on top of Core, never the other way around.
