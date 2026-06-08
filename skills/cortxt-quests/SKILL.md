---
name: cortxt-quests
description: CNS quest workflow and project portfolio queries. Use when the user asks about active quests, what to work on next, project status, completing tasks, or anything related to their CNS portfolio. Trigger words: quest, project, portfolio, status, planning, CNS, cortxt, "vad jobbar jag med", "what should I work on".
---

# CNS Quest Workflow

Quests are actionable tasks tracked across the CNS portfolio. They follow a defined lifecycle and can be queried/managed via MCP tools or the `cns quest` CLI.

## Tools

### cortxt_list_active_quests
Returns quests with status `active` or `in_progress`.

**When to use:** User asks "what quests are active?", "what am I working on?", "what should I tackle next?"

**Returns:** Array of quest objects: `id`, `slug`, `title`, `description`, `estimated_impact`, `status`, `source`, `created_at`, `started_at`

### cortxt_get_quest
Full quest details enriched with parent project context.

**Params:** `quest_id` (e.g. `quest-a1c37d56`)

**When to use:** User asks about a specific quest, wants context before starting work, or references a quest ID.

**Returns:** Quest object + `project_context` (meta, summary, layer, pipeline)

### cortxt_complete_quest
Transition a quest to `completed`, record a result summary, and push to GitHub.

**Params:** `quest_id`, `result_summary` (concise description of what was accomplished)

**When to use:** User says they finished a quest or asks to mark something done.

**IMPORTANT — two things to know:**

1. **Always confirm with the user before calling.** This is not politeness — the tool mutates persistent state (writes the quest JSON) AND pushes to the remote GitHub repo. There is no undo once pushed.

2. **Git push requires OAuth env vars** (`MCP_GITHUB_CLIENT_ID`, `MCP_GITHUB_CLIENT_SECRET` etc. in `.env`). In a local stdio session without these vars, the quest file will be updated on disk but the push will fail silently or error. If the push fails, tell the user: "Quest marked completed locally, but the git push did not go through — you'll need to commit and push manually or set up the OAuth env vars."

### cortxt_list_projects
List all CNS project nodes with key metadata.

**When to use:** User asks "what projects exist?", "show portfolio", "list nodes"

**Returns:** Array of: `slug`, `title`, `status`, `layer`, `pipeline`, `summary`

### cortxt_get_project
Full project context including sections and planning files.

**Params:** `slug` (e.g. `cns-devlog`, `cortxt-dashboard-app`)

**When to use:** User asks about a specific project, needs architecture context, or wants to understand what a project does before modifying it.

**Returns:** `meta` (all frontmatter fields), `sections` (markdown body), `planning` (contents of planning/*.md files)

## Quest Lifecycle

```
suggested → active → in_progress → completed → archived
```

Transitions are enforced — you cannot skip states. `cortxt_complete_quest` handles the transition to `completed` automatically.

## Workflow Patterns

### Starting a work session
1. `cortxt_list_active_quests` — see what is in flight
2. `cortxt_get_quest` on the relevant quest — get full description + project context
3. Use quest description + project context to guide implementation

### Understanding a project before changes
1. `cortxt_get_project` with the slug
2. Read planning files in the response for scope, architecture decisions, and constraints

### Finishing a quest
1. Confirm with user: "Mark quest-XXXX as completed with summary: '...'?"
2. Call `cortxt_complete_quest`
3. If push fails, inform user they need to push manually

### CLI alternative
The same data is accessible via `cns quest show <slug>` and `cns quest sync <slug>` if MCP is unavailable.

## Project Fields Reference

Key metadata fields in project responses:
- `status`: idea | early_mvp | mvp | live | shelved
- `stage`: idea | building | working | maturing
- `layer`: infrastructure | platform | application
- `pipeline`: intern | extern | review
- `current_slice`: what is being actively worked on
