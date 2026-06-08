# CNS (Central Node Store)

A local-first, Markdown-based system for modelling and running a product portfolio from idea to operation. `nodes/<slug>/node.md` files are the single source of truth; **GitHub is the source of truth in production.**

The CLI below is the local entrypoint. CNS has since grown a **node model** (`kind`/`stage` + `part_of`/`feeds`/`depends_on` relations), a **Flask backend** on Railway, and a **remote MCP server** consumed by the `cortxt` dashboard and by claude.ai.

> **Architecture lives in [`CLAUDE.md`](CLAUDE.md)** — read that for the node model, deploy/data flow, and repo layout. This README documents the CLI and local workflows.

Two AI engines are used for different things:
- **Perplexity** powers `cns update --mode api` (see Three Update Modes below). Needs `PERPLEXITY_API_KEY`.
- **Claude** (Anthropic) powers the analysis features — `analyze`, `devlog`, `brief`, `suggest-quest`. Needs `ANTHROPIC_API_KEY`.

## Setup

```bash
pip install -r requirements.txt
```

No API key is needed for local mode or connector mode. To enable API mode, copy and configure `.env`:

```bash
cp .env.example .env
# Edit .env and add your Perplexity API key (optional)
```

Run `python cns.py doctor` to check your environment.

## Three Update Modes

| Mode | Command | Writes file? | Needs API key? |
|------|---------|:------------:|:--------------:|
| **local** (default) | `cns update <slug>` | Yes | No |
| **connector** | `cns prepare <slug>` | No | No |
| **api** | `cns update <slug> --mode api -i "..."` | Yes | Yes |

### Local mode (default)

Interactive field editing directly in the terminal. No API key required.

```bash
python cns.py update webhook-router
```

```
? Select fields to change:
   1. Status
   2. MVP Stage
   ...
Enter field numbers (comma-separated, e.g. 1,3,8): 1,9,8

? New status: early_mvp
? Risk category: market
? Risk description: Customer acquisition may be harder than expected
? Risk score (1-5): 4
? Note to append: Buy-vs-build messaging needs to be clarified

Proposed changes:
  - status: idea
  + status: early_mvp
  ...

Apply these changes? [y/N] y
```

### Connector mode

Generates a formatted edit brief that you paste into Perplexity chat or a Space with synced files. Does not modify the project file.

```bash
python cns.py prepare webhook-router
```

```
What do you want to change?: Set status to early_mvp, add a market risk
Type of change [general]: status_update
Prompt detail level [detailed]: detailed

+--- Edit Brief -- copy below -------+
| ...                                 |
| --- PROMPT FOR PERPLEXITY ---       |
| Using the synced file for           |
| webhook-router as the source of     |
| truth, update the project so that:  |
| ...                                 |
+-------------------------------------+
```

### API mode

Calls the Perplexity API directly. Requires `PERPLEXITY_API_KEY` in `.env`.

```bash
python cns.py update webhook-router --mode api \
  --instruction "Set status to early_mvp. Add market risk: customer acquisition harder than expected, score 4."
```

If no API key is configured, prints:
> Perplexity API key not configured. Use local mode or connector mode, or add PERPLEXITY_API_KEY to .env.

Note: passing `--instruction` without `--mode` auto-selects api mode.

## Other Commands

### List all projects

```bash
python cns.py list
```

### Show a project

```bash
python cns.py show webhook-router
```

### Create a new project

```bash
python cns.py new my-new-project
```

### Export comparison spreadsheet

```bash
python cns.py export xlsx
```

### Check environment

```bash
python cns.py doctor
```

### Validate a project file

```bash
python cns.py validate webhook-router
```

### AI analysis & logs (Claude — needs `ANTHROPIC_API_KEY`)

```bash
python cns.py analyze webhook-router   # AI analysis of a node
python cns.py devlog                   # generate a devlog entry
python cns.py brief                    # daily portfolio brief
```

### Dev/file watching & git hooks

```bash
python cns.py devwatch                 # watch git diffs for a node
python cns.py watch                    # file watcher
python cns.py install-hooks            # install git hooks
python cns.py post-commit              # post-commit analysis (run by hook)
python cns.py review                   # review pending changes
python cns.py scaffold <slug>          # scaffold a new node's folders
python cns.py eventstream sync         # sync the event stream
```

> Not every subcommand is documented in depth here; run `python cns.py -h` for the full, current list.

## Project Structure

```
Project-CNS/
├── README.md
├── CLAUDE.md                <- authoritative architecture / node model
├── .env.example
├── requirements.txt
├── cns.py                   <- CLI entrypoint
├── system_prompt.md         <- system prompt for connector briefs / API
├── schemas/
│   └── node_schema.json  <- JSON schema for validating AI responses
├── nodes/                <- source of truth (one folder per node)
│   └── <slug>/
│       ├── node.md       <- canonical node file (frontmatter + sections); name is ALWAYS node.md
│       ├── planning/        <- mvp-scope.md (quest), roadmap.md, decisions.md
│       ├── research/  notes/  exports/  assets/
├── exports/                 <- global generated files (e.g. xlsx, nodes.json)
├── app/                     <- backend (Railway)
│   ├── server.py            <- Flask app; /api/nodes runs git_pull() + export_json() live
│   ├── mcp_server.py        <- FastMCP server (GitHub OAuth, Redis token-store)
│   ├── asgi.py              <- ASGI entrypoint: FastMCP owns /mcp, Flask mounted inside via a2wsgi
│   ├── git_ops.py           <- direct GitHub API push (AI content bypasses Railway's ephemeral disk)
│   └── templates/
├── skills/                  <- portable conventions (e.g. cortxt-quests)
└── scripts/
    ├── md_parser.py         <- read/write node.md + frontmatter; kind-aware section templates
    ├── validator.py         <- project + JSON schema validation
    ├── json_exporter.py     <- export all nodes to nodes.json
    ├── analyst.py           <- AI analysis (Claude via ANTHROPIC_API_KEY)
    ├── claude_client.py     <- Anthropic API client
    ├── perplexity_client.py <- Perplexity API client (used by `update --mode api`)
    ├── connector.py         <- edit-brief generator for connector mode
    ├── local_editor.py      <- interactive local editing
    ├── quest.py  quest_manager.py  <- quest workflow / lifecycle
    ├── portfolio_brief.py   <- daily portfolio brief
    ├── devlog.py  devwatch.py  eventstream.py  file_watcher.py  <- dev/activity tracking
    ├── install_hooks.py     <- git hook installation
    ├── doctor.py            <- environment diagnostics
    └── xlsx_exporter.py     <- generate exports/MVP_comparison.xlsx
```

## Design Principles

- **Local-first** - all core workflows work without an API key
- **Markdown is master** - `.md` files in `nodes/` are the single source of truth
- **API-optional** - Perplexity integration is one of three update paths, not a requirement
- **Connector-compatible** - generate edit briefs for external LLM workflows
- **Exports are read-only** - never edit generated files in `exports/`
- **Confirm before write** - `cns update` always shows a diff and asks `[y/N]`
- **Fail safely** - validation errors are printed clearly; no file is written on failure
- **No database** - the filesystem is the database

## Frontmatter Schema

Every node uses YAML frontmatter. Frontmatter is migrated **additively** — newer nodes carry the node-model fields below; some older nodes still carry the legacy fields. Keep fallbacks on old fields so the dashboard doesn't break.

**Node-model fields (current):**

| Field         | Type   | Allowed Values                                              |
|---------------|--------|------------------------------------------------------------|
| `title`       | string |                                                            |
| `slug`        | string |                                                            |
| `kind`        | enum   | `component`, `system`, `framework` — **emerges from `part_of` structure, not declared** |
| `stage`       | enum   | `idea`, `building`, `working`, `maturing`                  |
| `status`      | enum   | `idea`, `early_mvp`, `mvp`, `live`, `shelved`              |
| `part_of`     | string | slug of the parent node (drives nesting + kind)            |
| `feeds`       | list   | slugs this node feeds data to                              |
| `depends_on`  | list   | slugs this node depends on                                 |
| `summary`     | string |                                                            |
| `tags`        | list   |                                                            |
| `url_live`    | string |                                                            |
| `url_repo`    | string |                                                            |
| `created`     | date   |                                                            |
| `updated`     | date   |                                                            |

**Legacy fields (still present on some older nodes):**

| Field           | Type   | Allowed Values                                                               |
|-----------------|--------|-----------------------------------------------------------------------------|
| `cost_sek`      | number |                                                                             |
| `value_sek`     | number |                                                                             |
| `roi_percent`   | number |                                                                             |
| `mvp_stage`     | enum   | `hypothesis`, `problem_interviews`, `solution_test`, `demand_test`, `launch` |
| `current_slice` | string | Short description of current vertical slice (set by quest)                  |

## Perplexity API (optional)

Only needed for `cns update --mode api`. Set your key in `.env`:

```
PERPLEXITY_API_KEY=your_key_here
```

Uses the `sonar` model. Responses are validated against `schemas/node_schema.json` before any changes are applied.

## Aktivt bygge — project quest

Anvand quest-workflowen nar ett projekt gar fran ide till aktivt byggande.
Quest haller koll pa vad som byggs just nu, nasta steg, och vad som medvetet skjuts upp.

### Nar ska jag anvanda quest?

- Nar du bestammer att ett projekt ska borja byggas pa riktigt (inte bara vara en ide).
- Nar du vill ha en tydlig "current vertical slice" och nasta steg dokumenterade.
- Nar du vill att `cns list` ska visa vad du aktivt jobbar med.

### Filer som paverkas

| Fil | Roll |
|-----|------|
| `nodes/<slug>/node.md` | Frontmatter far `current_slice` + status satt till `early_mvp` |
| `nodes/<slug>/planning/mvp-scope.md` | Detaljerat: current slice, next steps, not now |

### Kommandon

```bash
# Initiera quest for ett projekt (skapar mvp-scope.md, uppdaterar node.md)
python cns.py quest init site-change-monitor

# Visa quest-status
python cns.py quest show site-change-monitor

# Synka current_slice fran mvp-scope.md tillbaka till node.md
python cns.py quest sync site-change-monitor
```

### Exempel: site-change-monitor

Nar `quest init` kors pa site-change-monitor skapas `planning/mvp-scope.md`:

```yaml
---
slug: site-change-monitor
quest_started: '2026-05-02'
quest_updated: '2026-05-02'
---

## Current Slice

Basic monitor + diff + alert loop via CLI.

- Fetch URLs from config.yaml
- Extract text, save snapshots, diff against previous
- Classify changes as meaningful vs noise
- Print clear summary to terminal

## Next Steps

1. Simple scheduler (--watch mode eller cron-friendly exit codes)
2. JSON/HTML report per run for downstream tooling

## Not Now

- Auth, billing, web dashboard
- Slack/email-notiser
- JavaScript-rendering
- Deploy-automation
```

Och `node.md` frontmatter far:

```yaml
current_slice: Basic monitor + diff + alert loop via CLI
status: early_mvp
```

### Dagligt flode

1. Kor `quest init <slug>` en gang nar projektet blir aktivt.
2. Redigera `planning/mvp-scope.md` direkt i editorn nar slicen andras.
3. Kor `quest sync <slug>` for att uppdatera `node.md` fran scope-filen.
4. Kor `cns list` for portfoljeoversikt med current_slice-kolumn.
