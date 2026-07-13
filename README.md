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
```

`python cns.py -h` shows exactly these three commands. Everything else lives in Lab.

## Architecture

Two layers. `scripts/` (Core) and `lab/scripts/` (Lab) form one PEP 420 namespace package: Core never
imports from Lab; Lab may import Core.

### Core — repo root

Minimal and self-contained. No network calls.

| Path | Role |
|---|---|
| `catalog.yaml` | The node model — every system, plus the graph |
| `decisions/<slug>.md` | Decision prose per system (sparse; only where one exists) |
| `schemas/` | Enum definitions, used by validate |
| `scripts/` | `catalog`, `md_parser`, `validator`, `derive_catalog`, `prose_check` |
| `cns.py` | Core CLI: `validate`, `new`, `export` |
| `tests/` | The suite (Core + Lab, via `tests/conftest.py`) |

### Lab — `lab/`

The Flask backend and the portfolio pipeline. Entrypoint:

```bash
python lab/cns_lab.py -h                 # full command surface
python lab/cns_lab.py skill-export       # vault → .claude/skills/. One direction.
python lab/cns_lab.py selftest           # every core capability, green or red
```

## What the backend actually serves

Four read-only endpoints, and they exist for one consumer — the portfolio view on app.cortxt.io:

| Endpoint | Read by |
|---|---|
| `/api/command-center` | the Cockpit |
| `/api/vertical/<slug>` | the per-venture page |
| `/api/nodes?domain=` | the architecture graph |
| `/api/cookbook/<slug>` | the build guide |

`tests/test_api_contract.py` pins their shape against recordings in `tests/golden/`. Re-record with
`python scripts/record_golden.py` before and after a change: same fields, and the app survives.

Everything else was removed on 2026-07-13 — the MCP server (53 tools, never once called), the session
store (zero sessions written), the idea inbox, the agency layer, 31 unused endpoints, and an archive
that was a third of the repo. Git is the memory.

## The honesty gate

`scripts/prose_check.py` runs in CI on every PR. It fails the build when a description claims
something the source does not support: a backticked path that does not exist, a CLI command that is
not registered, a retired field described as live.

**The root is an argument.** CI runs it over this repo *and* `cortxt`, and every file is held against
its own repo — a path in cortxt prose resolves in cortxt, not here. A cross-repo reference must name
the repo (`Project-CNS/tests/...`); a path without its repo is a path the reader cannot follow.

A file with `prose: record` in its frontmatter is never checked — a record makes no claim about the
present. Everything else is a description, and a description must be true today.

**What it cannot see:** any claim that is not mechanically verifiable. "Three routes" and "exactly
four functions" are invisible to it, and so is a Mermaid diagram — `ORIENTERING.md` drew a dead MCP
server as live infrastructure for a day and the gate never blinked. It is a floor, not a ceiling.

The vault's rules are still ungated, and twelve of fifteen skills export to a machine-local directory
CI cannot see. Those gaps are tracked in the Ärlighetsgrinden effort, not hidden here.

## Design principles

- **GitHub is the source of truth** for work — issues, milestones, PRs. CNS does not mirror them.
- **Derive, don't store** — `kind` and health emerge from structure; never hand-set.
- **One canonical model** — CNS owns it; dashboards are projection targets.
- **Nothing without a consumer.** If nobody reads it, it goes. It cannot be kept honest otherwise.
