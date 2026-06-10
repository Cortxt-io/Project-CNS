---
name: cortxt-quests
department: Gemensam
description: CNS work-item workflow (quests/issues/todos) and project portfolio queries. Use when the user asks about open work, what to tackle next, project status, finishing tasks, breaking work into sub-tasks, or anything about their CNS portfolio. Trigger words: quest, issue, todo, task, project, portfolio, status, planning, CNS, cortxt, "vad jobbar jag med", "what should I work on".
---

# CNS Work-Item Workflow (quests → issues → todos)

Work in CNS lives on **GitHub** (GitHub = source of truth). Three levels, plus
the idea inbox that feeds them:

```
Node (node.md)                          the product piece, label node:<slug>
  └─ Quest = GitHub Milestone           a work package; GitHub computes progress (X/Y)
       └─ Issue = task (open/closed)    a concrete unit of work, label node:<slug>
            └─ Todo = checkbox in body  a sub-step (- [ ] / - [x])
Idea (inbox)  --promote-->  Issue (optionally under a Quest)
```

A quest does **not** hold todos directly: a quest groups **issues**, and an issue
breaks into **todos**. A quest's "stage" is just its milestone open/closed + the
progress GitHub computes — there is no Projects board or stage label.

## Tools

### Issues (the task level)
- `cortxt_list_open_issues(node_slug=None)` — open work items, optionally one node's.
  *Use for:* "what's open?", "what should I work on for X?"
- `cortxt_get_issue(number)` — one issue + its node context (kind/stage/summary) and
  its `todos` (parsed checkboxes, each with an `index`/`text`/`done`).
- `cortxt_create_issue(node_slug, title, body="", quest_number=None)` — new task on a
  node, optionally filed under a quest (milestone).
- `cortxt_close_issue(number, result_summary)` — close with a summary comment.
  **Confirm with the user first** — it mutates state and pushes to GitHub (no undo).

### Todos (the sub-task level — checkboxes in the issue body)
- `cortxt_add_todo(number, text)` — append `- [ ] text` to the issue.
- `cortxt_check_todo(number, index, done=True)` — tick/untick the index-th checkbox
  (indices come from `cortxt_get_issue(...).todos`).

### Quests (the grouping level — GitHub milestones)
- `cortxt_list_quests()` — open quests with progress (closed/total issues).
- `cortxt_get_quest(number)` — a quest (milestone) + its issues.
- `cortxt_create_quest(title, description="")` — new work package to group issues.
- `cortxt_close_quest(number)` — close it; its issues keep their own state.

### Ideas (the inbox that feeds work)
- `cortxt_capture_idea(text, source="chat", slug=None, session_id=None)` — keep a raw
  thought (lighter than an issue).
- `cortxt_list_ideas(status="open", slug=None, session_id=None)`.
- `cortxt_promote_idea_to_issue(idea_id, title, slug=None, body=None, quest_number=None)`
  — turn an idea into an issue (optionally under a quest). The idea is kept and marked
  'promoted'. **Confirm with the user first** (it creates a GitHub issue).

### Projects (the portfolio level — nodes)
- `cortxt_list_projects()` — all nodes with metadata.
- `cortxt_get_project(slug)` — full node context: meta, sections, planning/*.md.

## Workflow patterns

### Starting a work session
1. `cortxt_list_open_issues` (or scope to a node) — see what's open.
2. `cortxt_get_issue` on the one you'll do — read its node context + `todos`.
3. Work through the todos; `cortxt_check_todo` as you finish each.

### Breaking a task down
1. `cortxt_get_issue(number)` to see existing todos.
2. `cortxt_add_todo(number, "...")` for each sub-step.

### From idea to work
1. `cortxt_list_ideas` to triage the inbox.
2. Survivors: `cortxt_promote_idea_to_issue(...)` (optionally `quest_number=` to file it
   under a quest). Confirm first.

### Finishing
1. Confirm with the user: "Close issue #N with summary '...'?"
2. `cortxt_close_issue(number, result_summary)`.
3. If the work changed architecture, conventions, deploy flow, repo layout, or the node
   model, update the repo's `CLAUDE.md` in the same change — see below.

### Push mode (same caveat across the cortxt_* tools)
Mutations push via `git_ops` Contents API (or the issues client) using
`CNS_GITHUB_TOKEN`/`GITHUB_REPO` (or OAuth env in a remote session). Without them the
change may be made on disk but the push fails — tell the user it didn't reach GitHub.

## Keeping CLAUDE.md current

Each repo (`Project-CNS`, `cortxt`) has a `CLAUDE.md` at its root, loaded at the start
of every session — the node model, repo layout, deploy flow, conventions, gotchas.
**Treat it as living:** whenever work changes something it describes, update it in the
same change (architecture/data flow, new/renamed/removed nodes, deploy/auth/DNS, a new
convention or a gotcha worth not hitting twice). Keep it concise and high-signal. If it
drifts, every future session starts from stale assumptions.

## Node model reference

The live model is **kind + stage + relations**. A node is `nodes/<slug>/node.md`.

- `kind`: component | system | framework — **emerges from structure**, not declared. A
  node is a *system* if other nodes point to it via `part_of`, a *component* if none do,
  a *framework* if it is top-level. Fractal.
- `stage`: idea | building | working | maturing — **"idea" is a stage, not a kind**.
- `status`: idea | early_mvp | mvp | live | shelved
- relations: `part_of` (containment), `feeds` (data flow), `depends_on` (dependency)

`layer` and `pipeline` are **legacy** frontmatter fields, usually empty — structure now
comes from `part_of`/`kind`. Do not rely on them.
