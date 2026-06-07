"""cns-devwatch: git-diff-based change detector for the CNS project portfolio.

Monitors ALL .md files under projects/<slug>/ and exports one ChangeEvent per
slug, compatible with the DocsWatch/cns-devlog schema.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scripts.md_parser import read_project, list_project_files


class DevwatchError(RuntimeError):
    """Raised when devwatch cannot run (e.g. git unavailable)."""

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPORTS_DIR = REPO_ROOT / "exports"
LAST_RUN_FILE = REPO_ROOT / ".devwatch_state.json"

# Git empty-tree SHA — used as baseline when the repo has only one commit
GIT_EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

console = Console()


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command from the repo root."""
    return subprocess.run(
        ["git"] + args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=check,
    )


def _git_available() -> bool:
    try:
        r = _git(["rev-parse", "--is-inside-work-tree"], check=False)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def get_baseline_commit(
    since_date: Optional[str] = None,
    last_run: Optional[dict] = None,
) -> str:
    """Return the git commit SHA to use as the diff baseline.

    Priority: --since DATE > last_commit SHA from state file > HEAD~1 > empty tree.
    """
    if since_date:
        r = _git(["log", f"--before={since_date}", "-1", "--format=%H"], check=False)
        sha = r.stdout.strip()
        if sha:
            return sha
        return GIT_EMPTY_TREE

    if last_run:
        sha = last_run.get("last_commit", "")
        if sha:
            return sha

    # No prior state: try HEAD~1
    r = _git(["rev-parse", "HEAD~1"], check=False)
    if r.returncode == 0:
        return r.stdout.strip()

    return GIT_EMPTY_TREE


def run_git_diff(baseline_commit: str) -> str:
    """Return unified diff for all .md files under projects/ since baseline_commit."""
    r = _git(
        ["diff", "--unified=3", f"{baseline_commit}..HEAD", "--", "projects/"],
        check=False,
    )
    return r.stdout


# ---------------------------------------------------------------------------
# Diff parsing — group by slug, track subfile
# ---------------------------------------------------------------------------

# Matches:  diff --git a/projects/<slug>/some/path.md b/projects/<slug>/some/path.md
_DIFF_HEADER_RE = re.compile(
    r"^diff --git a/projects/([^/]+)/(.+\.md) b/projects/[^/]+/.+\.md$"
)


def parse_diff_by_slug(diff_output: str) -> dict[str, dict[str, str]]:
    """Split a unified diff into per-slug, per-file chunks.

    Returns:
        {
            slug: {
                "project.md": "<diff text>",
                "planning/decisions.md": "<diff text>",
                ...
            }
        }
    """
    result: dict[str, dict[str, str]] = {}
    current_slug: Optional[str] = None
    current_file: Optional[str] = None
    current_lines: list[str] = []

    def _flush() -> None:
        if current_slug and current_file:
            result.setdefault(current_slug, {})[current_file] = "".join(current_lines)

    for line in diff_output.splitlines(keepends=True):
        m = _DIFF_HEADER_RE.match(line.rstrip())
        if m:
            _flush()
            current_slug = m.group(1)
            current_file = m.group(2)
            current_lines = [line]
        elif current_slug is not None:
            current_lines.append(line)

    _flush()
    return result


# ---------------------------------------------------------------------------
# Per-file diff classification
# ---------------------------------------------------------------------------

_FM_FIELD_RE = re.compile(r"^([a-z_]+):\s*(.*)$")


def classify_file_diff(diff_text: str, is_project_md: bool = False) -> dict:
    """Analyse the diff for a single file.

    Returns:
        {
            "changed_fields": [...],   # frontmatter keys (project.md only)
            "sections": [...],         # ## Heading names with changed content
            "raw_content": "...",      # diff snippets, per-section <= 500 chars
        }
    """
    changed_fields: set[str] = set()
    changed_sections: set[str] = set()
    section_diffs: dict[str, list[str]] = {}
    current_section: Optional[str] = None

    for line in diff_text.splitlines():
        # Skip diff meta-lines
        if re.match(r"^(diff |index |--- |\+\+\+ |@@)", line):
            continue
        if line.startswith("@@"):
            current_section = None
            continue

        # Detect section headings in context/added/removed lines
        sec_m = re.match(r"^[ +\-]## (.+)$", line)
        if sec_m:
            current_section = sec_m.group(1).strip()
            continue

        # Changed lines only
        if not line.startswith(("+", "-")):
            continue
        content = line[1:].strip()

        # Frontmatter field detection (project.md only)
        if is_project_md:
            fm_m = _FM_FIELD_RE.match(content)
            if fm_m:
                changed_fields.add(fm_m.group(1))
                continue

        # Section content change
        if current_section:
            changed_sections.add(current_section)
            section_diffs.setdefault(current_section, []).append(line)

    # Build rawContent: per-section snippets truncated to 500 chars each
    parts = []
    for section, lines in section_diffs.items():
        snippet = "\n".join(lines)
        if len(snippet) > 500:
            snippet = snippet[:500] + "\n...[truncated]"
        parts.append(f"## {section}\n{snippet}")

    raw_content = "\n\n".join(parts) if parts else diff_text[:800]

    return {
        "changed_fields": sorted(changed_fields),
        "sections": sorted(changed_sections),
        "raw_content": raw_content,
    }


# ---------------------------------------------------------------------------
# Noise filter
# ---------------------------------------------------------------------------

def is_noise(classified: dict[str, dict]) -> bool:
    """Return True if all changes for a slug are noise-only.

    Noise = only project.md changed AND only the `updated` field changed
    AND no section content changed.
    Any change to a non-project.md file is always meaningful.
    """
    file_keys = set(classified.keys())

    # Any non-project.md file changed → always meaningful
    if file_keys - {"project.md"}:
        return False

    pmd = classified.get("project.md", {})
    changed_fields = pmd.get("changed_fields", [])
    sections = pmd.get("sections", [])

    if sections:
        return False

    meaningful_fields = [f for f in changed_fields if f != "updated"]
    return len(meaningful_fields) == 0


# ---------------------------------------------------------------------------
# Fingerprint & event builder
# ---------------------------------------------------------------------------

def _fingerprint(slug: str, changed_files_meta: list[dict]) -> str:
    """Stable hash of slug + sorted(all file paths + section names)."""
    parts = [slug]
    for cf in sorted(changed_files_meta, key=lambda x: x["file"]):
        parts.append(cf["file"])
        parts.extend(sorted(cf["sections"]))
    key = "|".join(parts)
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def build_event(
    slug: str,
    classified: dict[str, dict],
    project_meta: dict,
    run_id: str,
    now_iso: str,
) -> dict:
    """Build one ChangeEvent aggregating all changed files for a slug."""

    changed_files_meta = [
        {"file": rel_file, "sections": info["sections"]}
        for rel_file, info in sorted(classified.items())
    ]

    # Top-level changed_fields from project.md only
    changed_fields = classified.get("project.md", {}).get("changed_fields", [])

    # Title: slug + comma-joined file names
    file_names = ", ".join(cf["file"] for cf in changed_files_meta)
    title = f"{slug}: {file_names}"

    # rawContent: all file snippets joined with file headers
    raw_parts = []
    for rel_file, info in sorted(classified.items()):
        if info["raw_content"]:
            raw_parts.append(f"### {rel_file}\n{info['raw_content']}")
    raw_content = "\n\n".join(raw_parts)

    fp = _fingerprint(slug, changed_files_meta)
    run_compact = run_id.replace("_", "T") + "Z"

    project_title = project_meta.get("title", slug)
    project_tags = project_meta.get("tags") or []
    tags = sorted({slug} | set(project_tags))

    return {
        "id": f"devwatch:{slug}:{fp}:{run_compact}",
        "detectedAt": now_iso,
        "source": {
            "id": slug,
            "name": project_title,
            "type": "devwatch",
            "url": None,
        },
        "title": title,
        "rawContent": raw_content,
        "url": None,
        "kind": "changed",
        "tags": tags,
        "meta": {
            "run_id": run_id,
            "run_timestamp": run_compact,
            "slug": slug,
            "project_title": project_title,
            "changed_fields": changed_fields,
            "changed_files": changed_files_meta,
            "noise_filtered": False,
        },
    }


# ---------------------------------------------------------------------------
# Stage-transition detection
# ---------------------------------------------------------------------------

_STAGE_DIFF_RE = re.compile(r"^stage:\s*(.+)$")


def _extract_stage_transition(diff_text: str) -> tuple[Optional[str], Optional[str]]:
    """Parse unified diff for stage field changes in project.md frontmatter.

    Returns (old_stage, new_stage) or (None, None) if no transition detected.
    """
    old: Optional[str] = None
    new: Optional[str] = None
    for line in diff_text.splitlines():
        # Only look at changed lines (not context or diff metadata)
        if line.startswith("-") and not line.startswith("---"):
            m = _STAGE_DIFF_RE.match(line[1:].strip())
            if m:
                old = m.group(1).strip()
        elif line.startswith("+") and not line.startswith("+++"):
            m = _STAGE_DIFF_RE.match(line[1:].strip())
            if m:
                new = m.group(1).strip()
    return old, new


# ---------------------------------------------------------------------------
# Eventstream adapter
# ---------------------------------------------------------------------------

def to_eventstream_event(
    change_event: dict, old_stage: Optional[str], new_stage: Optional[str]
) -> dict:
    """Convert a ChangeEvent to an eventstream event."""
    from scripts.eventstream import make_event

    meta = change_event.get("meta", {})
    slug = meta.get("slug", "")
    changed_fields = meta.get("changed_fields", [])
    changed_files = meta.get("changed_files", [])
    project_title = meta.get("project_title", slug)

    # Determine event type
    has_stage_change = (
        old_stage is not None and new_stage is not None and old_stage != new_stage
    )
    what = "stage_change" if has_stage_change else "md_change"

    # Build how summary
    file_names = [cf.get("file", "?") for cf in changed_files]
    how = f"{len(file_names)} files: {', '.join(file_names)}"

    # Deterministic event ID based on devwatch fingerprint
    devwatch_id = change_event.get("id", "")
    parts = devwatch_id.split(":")
    fp = parts[2] if len(parts) >= 3 else uuid.uuid4().hex[:16]
    event_id = f"evt:devwatch:{what}:{slug}:{fp}"

    return make_event(
        what=what,
        when=change_event.get("detectedAt", ""),
        why=change_event.get("title", ""),
        how=how,
        who="",
        where=f"devwatch:{slug}",
        source="devwatch",
        slug=slug,
        event_id=event_id,
        meta={
            "devwatch_id": devwatch_id,
            "changed_fields": changed_fields,
            "changed_files": changed_files,
            "project_title": project_title,
            "stage_from": old_stage,
            "stage_to": new_stage,
        },
    )


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def load_last_run() -> Optional[dict]:
    if LAST_RUN_FILE.exists():
        try:
            return json.loads(LAST_RUN_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_devwatch(
    output: Optional[str] = None,
    since: Optional[str] = None,
    dry_run: bool = False,
) -> Path:
    """Run the devwatch pipeline. Returns path to output file."""

    if not _git_available():
        console.print("[bold red]Error:[/bold red] git is not available or this is not a git repo.")
        console.print("cns-devwatch requires the CNS repo to be tracked by git.")
        raise DevwatchError("git is not available or this is not a git repo")

    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%d_%H%M%S")
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    today_str = now.strftime("%Y-%m-%d")

    if output:
        output_path = Path(output)
    else:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = EXPORTS_DIR / f"devwatch_{today_str}.json"

    # Resolve baseline
    last_run = load_last_run()
    baseline_commit = get_baseline_commit(since_date=since, last_run=last_run)

    if since:
        baseline_label = since
    elif last_run and last_run.get("last_commit"):
        baseline_label = last_run["last_commit"][:7]
    else:
        baseline_label = "HEAD~1"

    diff_output = run_git_diff(baseline_commit)
    slug_diffs = parse_diff_by_slug(diff_output)

    all_slugs = [p.parent.name for p in list_project_files()]
    projects_scanned = len(all_slugs)

    events: list[dict] = []
    es_events: list[dict] = []
    noise_count = 0

    for slug, file_diff_map in slug_diffs.items():
        classified: dict[str, dict] = {
            rel_file: classify_file_diff(diff_text, is_project_md=(rel_file == "project.md"))
            for rel_file, diff_text in file_diff_map.items()
        }

        if is_noise(classified):
            noise_count += 1
            continue

        try:
            project_meta, _, _ = read_project(slug)
        except FileNotFoundError:
            project_meta = {"title": slug, "tags": []}

        change_event = build_event(slug, classified, project_meta, run_id, now_iso)
        events.append(change_event)

        # Detect stage transition and convert to eventstream event
        project_md_diff = file_diff_map.get("project.md", "")
        old_stage, new_stage = _extract_stage_transition(project_md_diff)
        es_events.append(to_eventstream_event(change_event, old_stage, new_stage))

    no_changes = (len(events) == 0 and noise_count == 0 and not slug_diffs)

    payload = {
        "schema_version": "1.0",
        "exported_at": now_iso,
        "run_id": run_id,
        "baseline": baseline_label,
        "events": events,
        "meta": {
            "projects_scanned": projects_scanned,
            "projects_changed": len(slug_diffs),
            "events_exported": len(events),
            "noise_filtered": noise_count,
            "no_changes": no_changes,
        },
    }

    _print_summary(payload, baseline_label, events, noise_count, output_path, dry_run)

    if not dry_run:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        json_text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        output_path.write_text(json_text, encoding="utf-8")
        # State file: used for local runs only. CI uses --since flag instead
        # to avoid race conditions with automated commits.
        head_sha = _git(["rev-parse", "HEAD"]).stdout.strip()
        state = {**payload, "last_commit": head_sha}
        LAST_RUN_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        # Write eventstream events (adapter mode)
        if es_events:
            from scripts.eventstream import append_to_jsonl, push_to_redis, generate_aggregate
            for evt in es_events:
                append_to_jsonl(evt)
                push_to_redis(evt)
            generate_aggregate()

    return output_path


# ---------------------------------------------------------------------------
# Rich display
# ---------------------------------------------------------------------------

def _print_summary(
    payload: dict,
    baseline_label: str,
    events: list[dict],
    noise_count: int,
    output_path: Path,
    dry_run: bool,
) -> None:
    meta = payload["meta"]
    run_id = payload["run_id"]

    header = (
        f"Run: {run_id}  Baseline: {baseline_label}\n"
        f"Scanned {meta['projects_scanned']} projects · "
        f"{meta['projects_changed']} changed · "
        f"{noise_count} filtered"
    )
    if dry_run:
        header += "  [dim](dry-run)[/dim]"

    console.print(Panel(header, title="[bold cyan]cns-devwatch[/bold cyan]", expand=False))

    if events:
        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
        table.add_column("slug", style="cyan")
        table.add_column("changed files")
        table.add_column("changed fields")

        for event in events:
            m = event["meta"]
            files_str = ", ".join(cf["file"] for cf in m["changed_files"])
            fields_str = ", ".join(m["changed_fields"]) if m["changed_fields"] else "[dim]—[/dim]"
            table.add_row(m["slug"], files_str, fields_str)

        console.print(table)
    elif meta["no_changes"]:
        console.print("[dim]No changes detected since last run.[/dim]")
    else:
        console.print(
            f"[dim]All {noise_count} change(s) were noise-filtered "
            f"(updated date only).[/dim]"
        )

    if noise_count:
        console.print(f"  [dim]Noise-filtered: {noise_count} (updated date only)[/dim]")

    if not dry_run:
        console.print(f"  Output: [green]{output_path}[/green]")


# ---------------------------------------------------------------------------
# Direct script execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="devwatch",
        description="Detect changes in CNS project files via git diff",
    )
    parser.add_argument("--output", "-o", default=None, help="Override output file path")
    parser.add_argument(
        "--since", default=None,
        help="ISO date baseline (e.g. 2026-05-18). Overrides last-run state file.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Print detected changes without writing output files",
    )
    args = parser.parse_args()
    try:
        run_devwatch(output=args.output, since=args.since, dry_run=args.dry_run)
    except DevwatchError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        sys.exit(1)
