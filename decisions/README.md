# decisions/ — node prose, not rules

This folder holds **node prose**: the free-form rationale for a system in `catalog.yaml`, keyed by
slug. It is **machine-read** — `scripts/catalog.py` (`read_node` → `raw`) and `cns export` load
`decisions/<slug>.md`. Files here belong to the node model.

Node prose answers: *why is this system shaped the way it is?* It is not a decision log.

## The rules moved

The folder used to hold two different species. Four files were never node prose — they were the
actual **rules** governing how we work, with no slug in `catalog.yaml` and no code reading them.
That conflation is why a rule could not be told apart from an artifact.

As of 2026-07-12 the rules live in the Obsidian vault, which is now the canonical rulebook:

    Ideaverse/Cortxt-io/Studio/Rules/

Four files moved there: the git/GitHub foundation, the MCP router, the portfolio layers, and the
decision-point critic. None of them was node prose — they were rules, with no slug in `catalog.yaml`
and no code reading them. That conflation is why a rule could not be told apart from an artifact.

Precedence: **vault rules → CLAUDE.md → skills → memories.**

## Adding to this folder

Only add `<slug>.md` for a slug that exists in `catalog.yaml`. If you are writing a rule — how we
work, what we decided, what we rejected — it does not belong here. Write it in the vault.
