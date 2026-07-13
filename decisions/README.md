# decisions/ — node prose, not rules

This folder holds **node prose**: the free-form rationale for a system in `catalog.yaml`, keyed by
slug. It is **machine-read** — `scripts/catalog.py` (`read_node` → `raw`), `cns export` and the MCP
tool `lab/app/tools/projects.py` all load `decisions/<slug>.md`. Files here are generated-adjacent
(originally by `lab/scripts/migrate_to_catalog.py`) and belong to the node model.

Node prose answers: *why is this system shaped the way it is?* It is not a decision log.

## The rules moved

The folder used to hold two different species. Four files were never node prose — they were the
actual **rules** governing how we work, with no slug in `catalog.yaml` and no code reading them.
That conflation is why a rule could not be told apart from an artifact.

As of 2026-07-12 the rules live in the Obsidian vault, which is now the canonical rulebook:

    Ideaverse/Cortxt/Playbook/Rules/

| Rule | Was |
|---|---|
| Git/GitHub foundation — repo topology, branch standard, org | `decisions/git-github-grund.md` |
| MCP router & agent tool access | `decisions/mcp-router.md` |
| Portfolio layers — substrate → fog → vertical | `decisions/portfolio-layers.md` |
| ADR: Decision-point critic | `decisions/decision-point-critic.md` |

Precedence: **vault rules → CLAUDE.md → skills → memories.** See the `Regelboken` dashboard.

## Adding to this folder

Only add `<slug>.md` for a slug that exists in `catalog.yaml`. If you are writing a rule — how we
work, what we decided, what we rejected — it does not belong here. Write it in the vault.
