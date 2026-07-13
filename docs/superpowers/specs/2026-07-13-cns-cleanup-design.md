---
prose: record
date: 2026-07-13
status: approved
supersedes: null
---

# Design: consolidate and clean up Project-CNS

A record of the design agreed on 2026-07-13. It is not a description of the repo — it
describes the work to be done, at the moment it was decided. It is not edited after the fact.

## Context

The agency layer was frozen on 2026-07-12 (`lab/frozen/FROZEN.md`) because it lied silently
on every prompt. The freeze cut cleanly, but it left a repo full of surfaces that still
describe, import, or advertise the layer that is now gone — plus the debris of two earlier
teardowns (the node model, epic #11; the Core/Lab split).

Three surveys were run against the source on 2026-07-13. What they found:

**The honesty gate itself is blind.** `scripts/prose_check.py` reports
`18 description(s) checked, all true to the source`, exit 0, green in CI. Line 203 uses
`root.glob("CLAUDE.md")` — non-recursive. The repo's only CLAUDE.md lives in `lab/`, so it is
never checked. `README.md` is not in the pattern list at all. Run explicitly against the
skipped files, the gate finds **30 stale claims** (28 in `lab/CLAUDE.md`, 2 in `README.md`).
Second hole: `known_commands()` scrapes every `add_parser(...)` in `cns.py`, including the six
that are frozen stubs, so a document claiming `cns tui` works passes the check.

**Dead code.** Seven modules with no living consumer (`file_watcher`, `systemmap`,
`phase_board`, `projections`, `migrate_quests_to_issues`, `migrate_to_catalog`,
`lab/app/tools/linear.py`). Eight dead or rejecting CLI commands. A `--with-llm` flag on
`export` that prints "reserved hook" and then does the plain export anyway.

**The suite does not run.** `tests/test_lease_store.py` imports `fakeredis`, which is not in
`requirements.txt`. pytest interrupts on collection error, so one missing import blocks all
261 tests.

**Two silent bugs of the exact class FROZEN.md warns about.** `derive_catalog.py:23` requires
`exports/agents.json`; the file does not exist, so it derives zero agent nodes without saying
so. `derive_catalog.py:38-39` points at `catalog.annotations.yaml` and `catalog.merged.yaml`
at root paths where they do not live (they are in `archive/`) — a `cns derive --apply` would
recreate them and produce a fifth and sixth copy of the catalog.

**archive/ is a third of the repo.** 171 of 525 tracked files.

## Decisions

- `lab/frozen/` is not touched. It is a deliberate record and stays as it is.
- Value is rescued as *understanding*, not as relocated files. Git history is the memory.
- Nothing from `archive/` is moved into the vault. Most of it describes the layer that was
  just frozen or decisions already made; moving a month of stale research to a nicer address
  would repeat the mistake `archive/` already made.
- The six frozen command stubs stay. They exit 2 and point at FROZEN.md — that is a signpost,
  not a lie, and the freeze record describes them as intentional.

## Pass 1 — repair the honesty gate

Everything downstream depends on this. A gate that reports green on a file it never read
cannot prove that the rest of the cleanup landed.

`scripts/prose_check.py`:
- Make the glob recursive so `lab/CLAUDE.md` is caught; add `README.md` to the patterns.
- `known_commands()` must stop counting frozen commands as real. It should recognise handlers
  that call `_frozen()` and treat those commands as non-existent, so prose citing `cns tui`
  fails.

`requirements.txt`: add `fakeredis`, so the suite can be collected and the 261 tests run.

Red before green: first write the test proving today's gate misses `lab/CLAUDE.md`, watch it
fail, then fix. **At the end of this pass CI is red** — reporting the 30 false claims. That
redness is the proof the gate works. The prose is corrected in pass 4.

## Pass 2 — delete dead code

Remove, with their tests: `file_watcher.py`, `phase_board.py`, `projections.py`,
`systemmap.py`, `migrate_quests_to_issues.py`, `migrate_to_catalog.py`,
`lab/app/tools/linear.py`.

`systemmap` and `phase_board` are a judgement call, not obvious rot: they have passing tests
and their own docstrings promise CLI commands that were never registered. They are
*unfinished*, not rotten, and FROZEN.md lists `systemmap` among what survives. Either wire the
parser in (one line) or delete them. Leaving them unwired with green tests is the third and
worst option — it looks alive and is not.

Remove the retired no-op stubs `watch` and `scaffold`, and the `--with-llm` no-op flag on
`export`.

Fix the two silent bugs in `derive_catalog.py`: drop the dangling `ANNOTATIONS_PATH` /
`MERGED_PATH` constants, and stop deriving agent nodes rather than restoring `agents.json`
from `archive/` — the agent roster belongs to the frozen layer and must not be revived
sideways.

Out of scope, flagged not touched: `catalog.generated.yaml` is written and committed by cron
every six hours and has zero readers. `reconcile.yml` argues the diff *is* the point (a drift
log). Defensible, but it is a second catalog in git that nobody reads. Left alone pending an
explicit decision.

## Pass 3 — remove archive/

Delete `archive/` in full — the ~160 snapshots (99 idea JSON, 43 session dumps, old dashboard
and node-model dumps) and the eight prose files alike. Nothing is relocated. The repo drops
from 525 to roughly 350 tracked files.

Two live references into `archive/docs/` must be removed in the same commit, or one lie is
traded for a broken link: `ORIENTERING.md:247` and
`lab/frozen/skills/staff-role/SKILL.md:18`. The second is inside the frozen layer. Correcting
it is consistent with the freeze: FROZEN.md says the layer must not be *revived*, not that it
may point at files that no longer exist.

`tests/test_prose_check.py:73` uses an archive path as a fixture string and needs another.

## Pass 4 — correct the prose

This is where pass 1 pays off: the now-honest gate lists exactly what is false, and the work
is done when CI is green for the right reason.

- `lab/CLAUDE.md` — heaviest, 28 claims. Most point at modules that moved to `lab/frozen/`.
- `README.md`, `lab/README.md` — stop documenting `tui` and `dispatch` as runnable; drop
  `lab/scripts/dispatch.py` and `lab/railway.json`, neither of which exists.
- `ORIENTERING.md` — the hardest. Its Mermaid diagrams draw the dispatch loop and
  `.claude/agents/` as live infrastructure while line 232 of the same file correctly states
  the layer is frozen. The diagrams must show the system that exists — three layers, no
  agency. The frozen surface is named in prose, not drawn as a node in the topology. Also:
  the heading "Fyra minneslager" sits above a table with three rows.
- `.github/workflows-parked/README.md` — lists the disabled `export-dashboard.yml` as "Kept
  active (load-bearing)" and omits `ci.yml` and `reconcile.yml`, the two that actually run.

## Acceptance

- `prose_check` green, having actually read `lab/CLAUDE.md` and `README.md`.
- All 261 tests collectable and passing.
- No living reference points at anything that does not exist.
