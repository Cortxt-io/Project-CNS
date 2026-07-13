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
import posixpath
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

#: En rad som säger att ett fält ÄR pensionerat styr inte mot fältet — den varnar för det. Utan
#: detta undantag straffar grinden den enda prosa som hindrar nästa läsare från att återinföra det,
#: och priset för att varna blir en röd check.
_DECLARES_RETIREMENT = re.compile(
    r"pensionerad|pensionerade|retired|teardown|delegeras till board|borttagna ur|död rest",
    re.IGNORECASE,
)

#: En rad som säger att något SAKNAS eller är FRYST påstår inte att det finns. Att flagga den vore
#: att kräva att prosan tiger om det som gick sönder — och det är just den tystnaden som lät
#: agentur-lagret ljuga i månader.
_DECLARES_ABSENCE = re.compile(
    r"som inte fanns|inte finns|finns inte|saknas|är fryst|FRYST|togs bort|borttagen|död rest",
    re.IGNORECASE,
)

#: Sökvägar i andra repon kan inte slås upp här. De märks ut explicit istället för att låtsas
#: vara lokala — specs bor i det privata `cns-internal`.
EXTERNAL_PREFIXES = ("cns-internal/",)

_BACKTICKED = re.compile(r"`([^`\n]+)`")
_ADD_PARSER = re.compile(r'add_parser\(\s*["\']([a-z0-9][a-z0-9-]*)["\']')
#: Båda skrivsätten är samma påstående: "det här kommandot finns". `cns <cmd>` är Core-CLI:t,
#: `python lab/cns_lab.py <cmd>` är Lab-CLI:t — och Lab-formen var osynlig för grinden fram till
#: 2026-07-13, så README lovade `tui` och `dispatch` långt efter att de rivits, i grönt CI.
_CNS_COMMAND = re.compile(
    r"^(?:python\s+)?(?:lab/)?cns(?:\.py|_lab\.py)?\s+([a-z][a-z0-9-]*)"
)
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
    here: str = "",
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
        # Att NAMNGE en pensionerad fält för att säga att den är pensionerad är inte att styra mot
        # den — det är den enda prosa som får rädda nästa läsare från att återinföra den. Grinden
        # flaggade den varningen som en lögn, vilket gör att den enda ärliga meningen straffas.
        declares_retirement = _DECLARES_RETIREMENT.search(line) is not None

        for span in _BACKTICKED.findall(line):
            span = span.strip()

            hit = None if declares_retirement else _retired_in(span, retired)
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

            if _DECLARES_ABSENCE.search(line):
                continue

            for path in sorted(_paths_in(span)):
                if path.startswith(EXTERNAL_PREFIXES):
                    continue
                candidates = {path, f"{base}/{path}"} if base else {path}
                # `../CLAUDE.md` i lab/agents/README.md betyder lab/CLAUDE.md — inte roten. Prosan
                # skriver relativt sin egen mapp; grinden läste den relativt repo-roten och kallade
                # en sökväg som stämmer för en lögn.
                if path.startswith(("./", "../")) and here:
                    candidates.add(posixpath.normpath(f"{here}/{path}"))
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

    `archive`/`frozen` are excluded because prose about a torn-down or frozen layer is a record of
    what was true then, not a claim about now. Holding a record to the current source would force us
    to either edit the record or resurrect the layer.
    """
    found = []
    # Rekursivt. `CLAUDE.md` (icke-rekursivt) matchade bara roten — och repots enda CLAUDE.md bor
    # i lab/. Grinden rapporterade grönt i CI utan att ha läst den fil den byggdes för.
    for pattern in ("**/CLAUDE.md", "**/ORIENTERING.md", "**/README.md",
                    "**/.claude/skills/**/*.md", "**/skills/**/*.md"):
        for path in root.glob(pattern):
            # `archetypes/` är MALLAR för andra repon — deras sökvägar (`data/index.json`) beskriver
            # vad ett genererat projekt producerar, inte vad som finns här. Att hålla en mall till
            # det här repots verklighet är att kräva att den beskriver fel system.
            #
            # `node_modules`/`dist` är främmande prosa: tredjepartspaket bär egna README som beskriver
            # SINA repon. Att fälla vårt bygge för att clsx nämner `dist/clsx.mjs` är brus, och brus
            # dödar en grind lika säkert som blindhet — man slutar läsa den.
            #
            # `_<namn>/` är en nästlad utcheckning av ETT ANNAT repo (CI klonar syskonrepot dit).
            # Dess prosa hör till det repot och checkas när det är sin egen `--root` — inte som en
            # del av vårt filträd, där varje sökväg den nämner ser ut att saknas.
            if not path.is_file():
                continue
            parts = path.relative_to(root).parts  # relativt roten — annars skippar `_cortxt` sig själv
            skip = {"archive", "frozen", "archetypes", ".git", "node_modules", "dist", "build"}
            nested_checkout = any(p.startswith("_") for p in parts[:-1])
            if not skip & set(parts) and not nested_checkout:
                found.append(path)
    return sorted(set(found))


def sibling_index(roots: list[Path]) -> set[str]:
    """Filer i syskonrepon, adresserade med repo-namn: `Project-CNS/decisions/x.md`.

    Ett påstående får peka över en repo-gräns — men bara om det säger vilket repo. Bar `tests/x.py`
    i cortxt-prosa är ett fel även om filen finns i CNS; läsaren (och jag) hittar den inte.
    """
    files: set[str] = set()
    for root in roots:
        # I CI checkas syskonrepot ut i `_cortxt/` (understreck = "nästlad utcheckning, inte vår
        # kod" — se prose_files). Prosan skriver `cortxt/...`, alltså repots riktiga namn.
        name = root.name.lstrip("_")
        for rel in load_repo_files(root):
            files.add(f"{name}/{rel}")
    return files


def check_root(
    root: Path,
    targets: list[Path] | None = None,
    *,
    extra_files: set[str] | None = None,
) -> list[tuple[str, Finding]]:
    """Kontrollera ett repos prosa mot *det repots* källa.

    Roten är ett argument, inte en konstant. Ett påstående i `cortxt/CLAUDE.md` handlar om cortxt —
    slår man upp dess sökvägar i Project-CNS rapporterar grinden att varje fil saknas, vilket är
    åtta falska positiv och noll värde. Varje fil hålls mot sitt eget repo.

    `cns`-kommandon och pensionerade fält är CNS-begrepp. Saknar roten `cns.py` respektive
    `schemas/retired.json` görs de kontrollerna inte — frånvaro av en källa är inte ett fel, den är
    bara en check som inte gäller här.
    """
    repo_files = load_repo_files(root) | (extra_files or set())
    cns_py = root / "cns.py"
    commands = known_commands(cns_py.read_text(encoding="utf-8")) if cns_py.exists() else set()
    retired = load_retired(root)

    out: list[tuple[str, Finding]] = []
    for path in targets or prose_files(root):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root) if path.is_absolute() else path
        base = "lab" if rel.parts and rel.parts[0] == "lab" else ""
        here = rel.parent.as_posix()
        for f in check_text(
            text, repo_files=repo_files, commands=commands, retired=retired, base=base, here=here
        ):
            out.append((rel.as_posix(), f))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", type=Path, help="prose files (default: agent-facing prose)")
    parser.add_argument(
        "--root", action="append", type=Path, dest="roots", metavar="DIR",
        help="repo to check (repeatable). Default: this repo. Prose is held to ITS OWN repo.",
    )
    args = parser.parse_args(argv)

    roots = [r.resolve() for r in (args.roots or [REPO_ROOT])]
    for root in roots:
        if not root.is_dir():
            print(f"root does not exist: {root}", file=sys.stderr)
            return 2
    # Korsrepo-referenser (`Project-CNS/decisions/x.md`) slås upp mot syskonen — men bara med prefix.
    siblings = sibling_index(roots) if len(roots) > 1 else set()

    if args.paths:
        findings = check_root(roots[0], [p.resolve() for p in args.paths], extra_files=siblings)
        checked = len(args.paths)
    else:
        findings = []
        checked = 0
        for root in roots:
            targets = prose_files(root)
            checked += len(targets)
            for rel, f in check_root(root, targets, extra_files=siblings):
                prefix = "" if len(roots) == 1 else f"{root.name}/"
                findings.append((f"{prefix}{rel}", f))

    for rel, f in findings:
        print(f"{rel}:{f.line}: {f.kind}: {f.message}")

    if findings:
        print(f"\n{len(findings)} stale claim(s). Prose that describes the system must match it.",
              file=sys.stderr)
        return 1
    print(f"{checked} description(s) checked, all true to the source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
