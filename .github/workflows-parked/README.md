# Parked workflows

GitHub only runs workflows under `.github/workflows/`. Files here are **disabled** — they
do not trigger on any event. This is the reversible "park" mechanism for Lab/Agency CI that
isn't load-bearing for the daily Core flow.

To reactivate one: `git mv .github/workflows-parked/<file> .github/workflows/`.

## Currently parked

- `claude.yml` — replies to `/claude` issue comments (agency).
- `claude-code-review.yml` — Claude PR review (agency).

Both belong to the Lab/Agency layer; reactivate when that layer is actively used again.

## Kept active (load-bearing)

- `export-dashboard.yml` — daily nodes.json export the dashboard depends on.
- `project-add-to-project.yml` / `project-status-done.yml` — cheap org-board automation.
