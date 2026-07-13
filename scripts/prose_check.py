"""Freshness check for descriptive prose — does it still tell the truth about the source?

Prose does one of two jobs, and they have opposite maintenance rules:

* A **record** (ADR, gate review, retro) says why a choice was made, at a moment. It is never
  edited — a wrong one is superseded, not rewritten. It cannot go stale, because it never
  claimed anything about the present. This check leaves records alone.
* A **description** (CLAUDE.md, a skill, a node summary) says what is true *now*. It must change
  in the same commit as the thing it describes — and when it doesn't, it lies silently.

Silent lies are what this catches. Three of them, all found in the wild:

1. a skill running ``scripts/staff-role.py``, which does not exist;
2. a CLAUDE.md claiming the CLI exposes three commands, when it registers dozens;
3. a skill maintaining ``stage``, a field retired from the node model.

Nothing here is judgment — every check is a lookup against the source. That is why it is code
and not a skill. The rulebook lives in the vault (``Playbook/Rules/``); this only enforces that
descriptions of the code match the code.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Backticked spans are only read as file claims when they look like repo paths. A bare word
#: in backticks is almost always a field, a value or a flag — flagging those would bury the
#: signal under noise, and a check nobody trusts is a check nobody runs.
PATH_SUFFIXES = (".py", ".json", ".yaml", ".yml", ".md", ".ts", ".tsx", ".js", ".mjs", ".toml")

#: A span carrying any of these is a *shape*, not a file: `nodes/<slug>/node.md`,
#: `roadmaps/{name}.md`, `nodes/*/node.md`. Flagging templates would make the check cry wolf,
#: and the first thing anyone does with a noisy check is switch it off.
PLACEHOLDERS = ("<", ">", "{", "}", "*")

_BACKTICKED = re.compile(r"`([^`\n]+)`")
_ADD_PARSER = re.compile(r'add_parser\(\s*["\']([a-z0-9][a-z0-9-]*)["\']')
_CNS_COMMAND = re.compile(r"^(?:python\s+)?cns(?:\.py)?\s+([a-z][a-z0-9-]*)")
_TOKENS = re.compile(r"[\s|;'\"()]+")


@dataclass(frozen=True)
class Finding:
    """One stale claim, located precisely enough to fix without hunting."""

    line: int
    kind: str  # missing-path | unknown-command | retired-field
    token: str
    message: str


def is_record(text: str) -> bool:
    """True when the prose declares ``prose: record`` in its frontmatter.

    Prose with no frontmatter counts as a description: that is the species that can lie, and
    it is the safe default. A record must opt in — being exempt from verification is a
    privilege, not a fallback.
    """
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    if end == -1:
        return False
    return re.search(r"^prose:\s*record\s*$", text[3:end], re.MULTILINE) is not None


def _paths_in(span: str) -> set[str]:
    """The file claims inside one backticked span.

    A span is often a command line (``python scripts/validate_org.py``), and it claims the
    script exists just as loudly as a bare path does — so we look *inside* it rather than
    demanding the whole span be a path.
    """
    found = set()
    for token in _TOKENS.split(span):
        if "://" in token or "/" not in token:
            continue
        if any(ch in token for ch in PLACEHOLDERS):
            continue
        if token.endswith(PATH_SUFFIXES):
            found.add(token)
    return found


def referenced_paths(text: str) -> set[str]:
    """Every claim this prose makes about a file in the repo."""
    found: set[str] = set()
    for span in _BACKTICKED.findall(text):
        found |= _paths_in(span.strip())
    return found


def known_commands(source: str) -> set[str]:
    """The subcommands the CLI actually registers — read from the source, not from prose.

    This is the point of the whole module: we ask the code what it does instead of believing
    a document that says so.
    """
    return set(_ADD_PARSER.findall(source))


def _retired_in(span: str, retired: dict[str, str]) -> str | None:
    """Which retired field does this code span steer — if any?

    Substring, not equality. The check used to compare the whole span against the retired key, so
    ``stage`` was caught but ``stage: working`` — which is what the prose actually writes — slipped
    through, and a skill whose entire spine was a deleted field passed as "true to the source".

    Word-bounded, so ``stagehand`` and ``backstage/config`` stay clean: we want the field, not the
    letters.
    """
    for field in retired:
        if re.search(rf"(?<![\w-]){re.escape(field)}(?![\w-])", span):
            return field
    return None


def check_text(
    text: str,
    *,
    repo_files: set[str],
    commands: set[str],
    retired: dict[str, str],
    base: str = "",
) -> list[Finding]:
    """Every claim this prose makes about the source, checked against the source.

    ``base`` is the directory the prose writes from: a skill under ``lab/`` that says
    ``scripts/validate_org.py`` means ``lab/scripts/validate_org.py``. Prose is written from
    where it lives, so the check must read it from there too.
    """
    if is_record(text):
        return []

    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for span in _BACKTICKED.findall(line):
            span = span.strip()

            hit = _retired_in(span, retired)
            if hit:
                findings.append(
                    Finding(
                        line=lineno,
                        kind="retired-field",
                        token=hit,
                        message=f"`{hit}` is retired: {retired[hit]}",
                    )
                )
                continue

            command = _CNS_COMMAND.match(span)
            if command:
                name = command.group(1)
                if commands and name not in commands:
                    findings.append(
                        Finding(
                            line=lineno,
                            kind="unknown-command",
                            token=f"cns {name}",
                            message=f"the CLI registers no `{name}` subcommand",
                        )
                    )
                continue

            for path in sorted(_paths_in(span)):
                candidates = {path, f"{base}/{path}"} if base else {path}
                if candidates & repo_files:
                    continue
                findings.append(
                    Finding(
                        line=lineno,
                        kind="missing-path",
                        token=path,
                        message=f"`{path}` does not exist",
                    )
                )

    return findings


# --- wiring: read the real sources ----------------------------------------------------


def load_repo_files(root: Path) -> set[str]:
    """Every tracked-looking file, as a repo-relative posix path."""
    skip = {".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache"}
    files = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip for part in path.parts):
            continue
        files.add(path.relative_to(root).as_posix())
    return files


def load_retired(root: Path) -> dict[str, str]:
    path = root / "schemas" / "retired.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))["retired"]


def prose_files(root: Path) -> list[Path]:
    """The descriptions we hold to the source: agent-facing prose that steers behaviour.

    `frozen` is excluded for the same reason `archive` is: prose about a frozen layer is a record
    of what was true when it was frozen, not a claim about the system now. Holding it to the
    current source would force us to either edit a record or resurrect the layer. See
    lab/frozen/FROZEN.md.
    """
    found = []
    for pattern in ("CLAUDE.md", "ORIENTERING.md", "**/.claude/skills/**/*.md", "**/skills/**/*.md"):
        for path in root.glob(pattern):
            if path.is_file() and not {"archive", "frozen", ".git"} & set(path.parts):
                found.append(path)
    return sorted(set(found))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", type=Path, help="prose files (default: agent-facing prose)")
    args = parser.parse_args(argv)

    repo_files = load_repo_files(REPO_ROOT)
    commands = known_commands((REPO_ROOT / "cns.py").read_text(encoding="utf-8"))
    retired = load_retired(REPO_ROOT)

    targets = args.paths or prose_files(REPO_ROOT)
    total = 0
    for path in targets:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO_ROOT) if path.is_absolute() else path
        base = "lab" if rel.parts and rel.parts[0] == "lab" else ""
        findings = check_text(
            text, repo_files=repo_files, commands=commands, retired=retired, base=base
        )
        for f in findings:
            print(f"{rel.as_posix()}:{f.line}: {f.kind}: {f.message}")
            total += 1

    if total:
        print(f"\n{total} stale claim(s). Prose that describes the system must match it.", file=sys.stderr)
        return 1
    print(f"{len(targets)} description(s) checked, all true to the source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
