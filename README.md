# CNS — Central Node Store

A local-first system for modelling and running a product portfolio from idea to operation,
built to be driven by an **AI agency** (a fleet of role-based agents) rather than by hand.
**GitHub is the source of truth.**

> **Architecture, data flow and conventions live in [`CLAUDE.md`](CLAUDE.md)** — that file is the
> maintained, authoritative description. This README is the orientation for a first read.

## What it is

CNS keeps product knowledge structured, validated and ready so AI sessions don't waste tokens
re-discovering context. Two layers:

- **The node model** — one entry per system in **[`catalog.yaml`](catalog.yaml)** (`title`, `summary`,
  `part_of`, `feeds`, `depends_on`, `type`, `domain`, `owner_agent`), plus sparse ADR prose in
  **`decisions/<slug>.md`**. `kind` (component/system/framework) is *derived* from the `part_of`
  structure, never stored. Health is *derived* at read time. Stage/status are delegated to the board.
- **The work layer** — work items live on **GitHub**: `epic` = Milestone, `story` = Issue (+ `type:`/`node:`
  labels), `todo` = task-list checkbox. An optional `initiative` top level + status flow live on an
  **org-level GitHub Project v2**.

The **agency** runs the portfolio: a dispatch loop picks suitable issues, routes them to role-based
agents, runs gated passes, and opens draft PRs (`scripts/dispatch.py`). Agents reach CNS through an
MCP server (10 consolidated tools, one per domain).

## Stack

Python · Flask · FastMCP · Railway (backend). The dashboard + landing page are a separate repo
(**`cortxt`**, React/Vite/ReactFlow on Vercel) that proxies `/api/*` to this backend.

## Setup

```bash
pip install -r requirements.txt
python cns.py validate        # validate the whole catalog
```

AI features (analysis, brief, dispatch passes) need `ANTHROPIC_API_KEY`. MCP/GitHub features need a
GitHub token; see `CLAUDE.md` (Deploy & data flow, Agents & tooling).

## Daily workflow

The node model is edited **by hand** in `catalog.yaml` / `decisions/` (the AI write-path is being
re-wired post-teardown). The work runs through GitHub + the agency:

```bash
python cns.py validate <slug>        # validate one system (or omit slug for the whole catalog)
python cns.py new <slug>             # add a new system to catalog.yaml
python cns.py tui                    # interactive overview / Control Tower
python -m scripts.dispatch           # run the agency dispatch loop (read-first by default)
python cns.py session list           # AI work sessions (first-class objects)
```

Run `python cns.py -h` for the full, current command list.

## Repo layout (high level)

```
catalog.yaml          <- the single structured source for the node model (systems + graph)
decisions/<slug>.md   <- sparse ADR prose (durable decision knowledge)
cns.py                <- CLI entrypoint
scripts/              <- catalog reader, validator, exporter, dispatch loop, MCP tool core, …
app/                  <- Flask backend + FastMCP server (Railway); git_ops.py pushes via GitHub API
schemas/enums.json    <- single source for node-model enums (kind/type/domain)
.github/workflows/    <- CI + org-Project automation
.claude/              <- the agency's tooling (versioned)
```

> Implementation specs and research live in a separate **private** repo (`cns-internal`); finished
> decisions are promoted into `decisions/` here.

Full layout, the node-model rationale, the deploy/data-flow gotchas, and the agency/tooling model are
documented in **[`CLAUDE.md`](CLAUDE.md)**.

## Design principles

- **GitHub is the source of truth** — AI-generated content is pushed via the GitHub API, not to
  Railway's ephemeral disk.
- **Derive, don't store** — `kind` and health emerge from structure/signals; a hand-set status goes stale.
- **One canonical model, projected outward** — CNS owns the model; GitHub (and later Linear/Vercel) are
  projection targets, not parallel stores.
- **Spec first** — review an implementation spec before code.
- **Update `CLAUDE.md` in the same change** as any architecture/convention it describes.
