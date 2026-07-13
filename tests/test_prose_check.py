"""Verification of the prose freshness check (scripts/prose_check.py).

The check exists because prose that *describes* the system goes stale silently: a skill
kept maintaining a retired field, another ran a script that no longer exists, and a
CLAUDE.md claimed the CLI had three commands when it registered 32. None of that is
caught by tests or types — it is caught by reading the source, which nobody does.

Pure functions: every input is injected (repo files as a set of paths, commands as a set,
retired fields as a dict), so no filesystem or CLI is touched here. Mirrors test_health.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prose_check import (  # noqa: E402
    check_text,
    is_record,
    known_commands,
    referenced_paths,
)

# --- referenced_paths: which backticked spans are claims about files? -------------------


def test_backticked_path_is_a_claim_about_a_file():
    assert referenced_paths("run `scripts/staff-role.py` first") == {"scripts/staff-role.py"}


def test_prose_words_in_backticks_are_not_paths():
    """`stage` and `go` are values, not files. Flagging them would drown the signal."""
    assert referenced_paths("the `stage` field is `go` or `kill`") == set()


def test_urls_are_not_repo_paths():
    assert referenced_paths("see `https://github.com/Cortxt-io/Project-CNS`") == set()


def test_multiple_paths_are_all_found():
    text = "both `scripts/catalog.py` and `schemas/enums.json` matter"
    assert referenced_paths(text) == {"scripts/catalog.py", "schemas/enums.json"}


# --- check_text: missing paths ---------------------------------------------------------


def test_missing_path_is_reported_with_line_number():
    text = "intro\nrun `scripts/staff-role.py` to onboard\n"
    findings = check_text(text, repo_files={"scripts/bemanna.py"}, commands=set(), retired={})

    assert len(findings) == 1
    assert findings[0].kind == "missing-path"
    assert findings[0].token == "scripts/staff-role.py"
    assert findings[0].line == 2


def test_existing_path_is_not_reported():
    text = "run `scripts/bemanna.py` to onboard"
    findings = check_text(text, repo_files={"scripts/bemanna.py"}, commands=set(), retired={})

    assert findings == []


def test_archived_path_is_reported_even_though_the_file_exists_somewhere():
    """`docs/agent-design-playbook.md` moved to archive/. The prose still points at docs/."""
    text = "grounded in `docs/agent-design-playbook.md`"
    findings = check_text(
        text,
        repo_files={"archive/docs/agent-design-playbook.md"},
        commands=set(),
        retired={},
    )

    assert [f.kind for f in findings] == ["missing-path"]


def test_placeholder_paths_are_not_claims():
    """`nodes/<slug>/node.md` is a shape, not a file. A check that flags templates is a check
    that cries wolf — and the first thing anyone does with a noisy check is turn it off."""
    text = "write to `nodes/<slug>/node.md` and `roadmaps/{name}.md` and `nodes/*/node.md`"
    findings = check_text(text, repo_files=set(), commands=set(), retired={})

    assert findings == []


def test_a_path_is_resolved_against_the_prose_file_s_own_root():
    """A skill under lab/ that says `scripts/validate_org.py` means lab/scripts/validate_org.py.
    Prose is written from where it lives; the check must read it from there too."""
    text = "run `scripts/validate_org.py`"
    findings = check_text(
        text,
        repo_files={"lab/scripts/validate_org.py"},
        commands=set(),
        retired={},
        base="lab",
    )

    assert findings == []


def test_a_path_missing_under_both_roots_is_still_reported():
    text = "run `scripts/staff-role.py`"
    findings = check_text(
        text,
        repo_files={"lab/scripts/bemanna.py"},
        commands=set(),
        retired={},
        base="lab",
    )

    assert [f.token for f in findings] == ["scripts/staff-role.py"]


def test_a_path_inside_a_shell_command_is_still_checked():
    """`python scripts/gone.py` claims the script exists just as loudly as a bare path."""
    text = "run `python scripts/gone.py` to validate"
    findings = check_text(text, repo_files=set(), commands=set(), retired={})

    assert [f.token for f in findings] == ["scripts/gone.py"]


# --- check_text: unknown CLI commands --------------------------------------------------


def test_unknown_cns_command_is_reported():
    text = "run `cns frobnicate` to sync"
    findings = check_text(text, repo_files=set(), commands={"export", "validate"}, retired={})

    assert len(findings) == 1
    assert findings[0].kind == "unknown-command"
    assert findings[0].token == "cns frobnicate"


def test_known_cns_command_is_not_reported():
    text = "run `cns export juvahem` for the brief"
    findings = check_text(text, repo_files=set(), commands={"export"}, retired={})

    assert findings == []


# --- check_text: retired fields --------------------------------------------------------


def test_retired_field_is_reported_with_its_reason():
    text = "the skill maintains `stage` transitions"
    findings = check_text(
        text,
        repo_files=set(),
        commands=set(),
        retired={"stage": "retired in the node teardown — lifecycle is delegated to the board"},
    )

    assert len(findings) == 1
    assert findings[0].kind == "retired-field"
    assert findings[0].token == "stage"
    assert "delegated to the board" in findings[0].message


def test_live_field_is_not_reported():
    text = "the `gate_decision` field drives the funnel"
    findings = check_text(text, repo_files=set(), commands=set(), retired={"stage": "gone"})

    assert findings == []


# --- records are exempt: they never claimed anything about the present -----------------


def test_a_record_is_never_checked():
    """A record (ADR, gate review) documents a past choice. It cites files that were true
    then and may be gone now — that is not rot, that is history. Checking it would force
    us to edit records, which is precisely what a record must never allow."""
    text = "---\nprose: record\n---\nwe ran `scripts/gone.py` back then"
    assert is_record(text) is True

    findings = check_text(text, repo_files=set(), commands=set(), retired={})
    assert findings == []


def test_a_description_is_checked():
    text = "---\nprose: description\n---\nrun `scripts/gone.py`"
    assert is_record(text) is False

    findings = check_text(text, repo_files=set(), commands=set(), retired={})
    assert [f.kind for f in findings] == ["missing-path"]


def test_prose_without_frontmatter_is_treated_as_a_description():
    """Repo prose (CLAUDE.md, skills) carries no frontmatter today. Defaulting to
    'description' is the safe bet: it is the species that can lie."""
    assert is_record("run `scripts/gone.py`") is False


# --- known_commands: read the CLI's real subcommands, do not trust the prose -----------


def test_known_commands_reads_registered_subparsers():
    source = '''
    sp_new = subparsers.add_parser("new", help="Create a system")
    sp_export = subparsers.add_parser("export", help="Export a brief")
    '''
    assert known_commands(source) == {"new", "export"}


# --- pensionerade fält INUTI ett större kodspann ------------------------------------------------
# Hålet som lät skräpet överleva: checken matchade bara kodspann som var EXAKT lika med det
# pensionerade fältet. `stage` föll — men `stage: working`, som är vad nod-granska.md faktiskt
# skriver, gled rakt igenom, och prose_check svarade "all true to the source" om en skill vars
# hela ryggrad var ett raderat fält.

RETIRED = {
    "stage": "retired with the node teardown (epic #11)",
    "node.md": "the node-as-file model was torn down 2026-06-12 (PR #104)",
}


def _retired_tokens(text: str) -> list[str]:
    found = check_text(text, repo_files=set(), commands=set(), retired=RETIRED)
    return [f.token for f in found if f.kind == "retired-field"]


def test_retired_field_inside_a_larger_code_span() -> None:
    """`stage: working` styr ett pensionerat fält lika mycket som `stage` gör."""
    assert _retired_tokens("Sätt aldrig `stage: working` utan bevis.") == ["stage"]


def test_retired_path_inside_a_glob() -> None:
    """`nodes/*/node.md` påstår att den rivna fil-modellen lever."""
    assert _retired_tokens("| Vad en nod är | `nodes/*/node.md` |") == ["node.md"]


def test_exact_span_still_caught() -> None:
    assert _retired_tokens("Fältet `stage` är borta.") == ["stage"]


def test_no_false_positive_on_an_unrelated_word() -> None:
    """`stagehand` innehåller 'stage' men styr inte fältet. Ett ordgränskrav, inte blind substring."""
    assert _retired_tokens("Kör `stagehand` och `backstage/config`.") == []


# --- the gate must not punish the prose that warns you ---------------------------------
#
# Four holes, all found on 2026-07-13 when the gate was first pointed at lab/CLAUDE.md — the one
# file it exists to guard, and the one file it had never read (the glob was not recursive).


def test_a_line_that_declares_a_field_retired_is_not_a_lie():
    """The only sentence that stops the next reader reinventing `stage` must not be flagged.

    Punish it and the honest move — warning about a retired field — costs you a red check, so the
    warning gets deleted and the field comes back.
    """
    text = "- **Pensionerade:** `status`, `stage`, `mvp_stage` — delegerade till board."
    findings = check_text(text, repo_files=set(), commands=set(), retired={"stage": "gone"})

    assert findings == []


def test_a_line_that_declares_a_path_absent_does_not_claim_it_exists():
    text = "routningen krävde `exports/agents.json`, som inte fanns → tom squad"
    findings = check_text(text, repo_files=set(), commands=set(), retired={})

    assert findings == []


def test_a_relative_path_resolves_against_the_prose_file_s_own_directory():
    """`../CLAUDE.md` in lab/agents/README.md is lab/CLAUDE.md — not the repo root."""
    text = "conventions live in `../CLAUDE.md`"
    findings = check_text(
        text,
        repo_files={"lab/CLAUDE.md"},
        commands=set(),
        retired={},
        base="lab",
        here="lab/agents",
    )

    assert findings == []


def test_a_path_in_another_repo_is_not_checked_here():
    """Specs live in the private `cns-internal`. We cannot look them up — so we do not pretend to."""
    text = "Spec: `cns-internal/plans/work-model-taxonomy-spec.md` (privat repo)."
    findings = check_text(text, repo_files=set(), commands=set(), retired={})

    assert findings == []
