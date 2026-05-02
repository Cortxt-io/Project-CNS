# CNS (Central Node Store) v0.3

A local-first, API-optional project management CLI for managing startup project ideas and MVPs. Markdown files are the single source of truth.

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

## Project Structure

```
prompt-cns/
├── README.md
├── .env.example             <- optional, only for api mode
├── requirements.txt
├── cns.py                   <- CLI entrypoint
├── system_prompt.md         <- system prompt for Perplexity API / connector briefs
├── schemas/
│   └── project_schema.json  <- JSON schema for validating API responses
├── projects/                <- source of truth
│   └── <slug>/
│       ├── project.md       <- canonical project file (frontmatter + sections)
│       ├── planning/
│       │   ├── mvp-scope.md <- quest workflow: current slice, next steps, not now
│       │   ├── roadmap.md
│       │   └── decisions.md
│       ├── research/
│       ├── notes/
│       ├── exports/
│       └── assets/
├── exports/                 <- global generated files (xlsx)
└── scripts/
    ├── md_parser.py         <- read/write .md files + frontmatter
    ├── quest.py             <- quest workflow (init/show/sync)
    ├── local_editor.py      <- interactive local editing
    ├── connector.py         <- edit brief generator for connector mode
    ├── doctor.py            <- environment diagnostics
    ├── perplexity_client.py <- Perplexity API integration (optional)
    ├── validator.py         <- project + JSON schema validation
    └── xlsx_exporter.py     <- generate exports/MVP_comparison.xlsx
```

## Design Principles

- **Local-first** - all core workflows work without an API key
- **Markdown is master** - `.md` files in `projects/` are the single source of truth
- **API-optional** - Perplexity integration is one of three update paths, not a requirement
- **Connector-compatible** - generate edit briefs for external LLM workflows
- **Exports are read-only** - never edit generated files in `exports/`
- **Confirm before write** - `cns update` always shows a diff and asks `[y/N]`
- **Fail safely** - validation errors are printed clearly; no file is written on failure
- **No database** - the filesystem is the database

## Frontmatter Schema

Every project file uses YAML frontmatter with these fields:

| Field         | Type   | Allowed Values                                                        |
|---------------|--------|-----------------------------------------------------------------------|
| `title`       | string |                                                                       |
| `slug`        | string |                                                                       |
| `status`      | enum   | `idea`, `early_mvp`, `mvp`, `live`, `shelved`                         |
| `tags`        | list   |                                                                       |
| `cost_sek`    | number |                                                                       |
| `value_sek`   | number |                                                                       |
| `roi_percent` | number |                                                                       |
| `mvp_stage`   | enum   | `hypothesis`, `problem_interviews`, `solution_test`, `demand_test`, `launch` |
| `current_slice` | string | Short description of current vertical slice (optional, set by quest) |
| `created`     | date   |                                                                       |
| `updated`     | date   |                                                                       |

## Perplexity API (optional)

Only needed for `cns update --mode api`. Set your key in `.env`:

```
PERPLEXITY_API_KEY=your_key_here
```

Uses the `sonar` model. Responses are validated against `schemas/project_schema.json` before any changes are applied.

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
| `projects/<slug>/project.md` | Frontmatter far `current_slice` + status satt till `early_mvp` |
| `projects/<slug>/planning/mvp-scope.md` | Detaljerat: current slice, next steps, not now |

### Kommandon

```bash
# Initiera quest for ett projekt (skapar mvp-scope.md, uppdaterar project.md)
python cns.py quest init site-change-monitor

# Visa quest-status
python cns.py quest show site-change-monitor

# Synka current_slice fran mvp-scope.md tillbaka till project.md
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

Och `project.md` frontmatter far:

```yaml
current_slice: Basic monitor + diff + alert loop via CLI
status: early_mvp
```

### Dagligt flode

1. Kor `quest init <slug>` en gang nar projektet blir aktivt.
2. Redigera `planning/mvp-scope.md` direkt i editorn nar slicen andras.
3. Kor `quest sync <slug>` for att uppdatera `project.md` fran scope-filen.
4. Kor `cns list` for portfoljeoversikt med current_slice-kolumn.
