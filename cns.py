#!/usr/bin/env python3
"""CNS (Central Node Store) - CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scripts.md_parser import (
    apply_changes,
    list_project_files,
    new_project_template,
    project_dir,
    project_path,
    read_project,
    scaffold_project_dirs,
    write_project,
    SECTIONS,
)
from scripts.xlsx_exporter import export_xlsx
from scripts.json_exporter import export_json

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _show_diff_and_confirm(
    meta: dict,
    new_meta: dict,
    sections: dict,
    new_sections: dict,
    slug: str,
) -> bool:
    """Show a colored diff preview and ask for confirmation.

    Returns True if the user confirmed and the file was written.
    """
    console.print()
    console.print("[bold]Proposed changes:[/bold]")

    has_changes = False

    # Show changed frontmatter fields
    for key in sorted(set(list(meta.keys()) + list(new_meta.keys()))):
        old_val = meta.get(key)
        new_val = new_meta.get(key)
        if old_val != new_val:
            has_changes = True
            console.print(f"  [red]- {key}: {old_val}[/red]")
            console.print(f"  [green]+ {key}: {new_val}[/green]")

    # Show changed sections
    for heading in SECTIONS:
        old_text = sections.get(heading, "").strip()
        new_text = new_sections.get(heading, "").strip()
        if old_text != new_text:
            has_changes = True
            console.print(f"\n  [bold]## {heading}[/bold]")
            if old_text:
                for line in old_text.splitlines():
                    console.print(f"  [red]- {line}[/red]")
            if new_text:
                for line in new_text.splitlines():
                    console.print(f"  [green]+ {line}[/green]")

    if not has_changes:
        console.print("  [dim](no changes)[/dim]")
        return False

    console.print()

    confirm = input("Apply these changes? [y/N] ").strip().lower()
    if confirm != "y":
        console.print("[yellow]Changes discarded.[/yellow]")
        return False

    path = write_project(slug, new_meta, new_sections)
    console.print(f"[green]Updated {path}[/green]")
    return True


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(_args: argparse.Namespace) -> None:
    """Print a summary table of all projects."""
    files = list_project_files()
    if not files:
        console.print("[yellow]No projects found.[/yellow]")
        return

    # Check if any project has a current_slice to decide whether to show the column
    projects_data = []
    has_any_slice = False
    for path in files:
        slug = path.parent.name
        try:
            meta, _, _ = read_project(slug)
        except Exception as exc:
            console.print(f"[red]Error reading {slug}: {exc}[/red]")
            continue
        if meta.get("current_slice"):
            has_any_slice = True
        projects_data.append((slug, meta))

    table = Table(title="CNS Projects", show_lines=True)
    table.add_column("Slug", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Status")
    table.add_column("MVP Stage")
    if has_any_slice:
        table.add_column("Current Slice", max_width=30, no_wrap=True)
    table.add_column("Cost SEK", justify="right")
    table.add_column("Value SEK", justify="right")
    table.add_column("ROI %", justify="right")

    for slug, meta in projects_data:
        status = meta.get("status", "")
        status_color = {
            "idea": "dim",
            "early_mvp": "yellow",
            "mvp": "green",
            "live": "bold green",
            "shelved": "dim red",
        }.get(status, "")

        row = [
            slug,
            meta.get("title", ""),
            f"[{status_color}]{status}[/{status_color}]" if status_color else status,
            meta.get("mvp_stage", ""),
        ]
        if has_any_slice:
            slice_val = meta.get("current_slice", "")
            # Truncate for table readability
            if len(slice_val) > 30:
                slice_val = slice_val[:27] + "..."
            row.append(f"[yellow]{slice_val}[/yellow]" if slice_val else "")
        row.extend([
            f"{meta.get('cost_sek', 0):,}",
            f"{meta.get('value_sek', 0):,}",
            f"{meta.get('roi_percent', 0)}%",
        ])
        table.add_row(*row)

    console.print(table)


def cmd_show(args: argparse.Namespace) -> None:
    """Print the full content of a single project file."""
    slug = args.slug
    try:
        meta, sections, raw = read_project(slug)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    console.print(Panel(raw, title=f"[bold cyan]{meta.get('title', slug)}[/bold cyan]", border_style="blue"))


def cmd_update(args: argparse.Namespace) -> None:
    """Update a project (local mode or api mode)."""
    slug = args.slug
    instruction = getattr(args, "instruction", None)
    mode = getattr(args, "mode", "local")

    # Smart default: if --instruction is provided without --mode, use api mode
    if instruction and mode == "local":
        mode = "api"
        console.print("[dim]Detected --instruction flag, using api mode.[/dim]")

    # Read current project
    try:
        meta, sections, raw = read_project(slug)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    if mode == "local":
        _update_local(slug, meta, sections)
    elif mode == "api":
        _update_api(slug, meta, sections, raw, instruction)


def _update_local(slug: str, meta: dict, sections: dict) -> None:
    """Interactive local edit mode."""
    from scripts.local_editor import run_local_edit

    changes = run_local_edit(meta, sections, console)
    if changes is None:
        return

    new_meta, new_sections = apply_changes(
        meta.copy(), {k: v for k, v in sections.items()}, changes
    )
    new_meta["updated"] = date.today().isoformat()

    _show_diff_and_confirm(meta, new_meta, sections, new_sections, slug)


def _update_api(slug: str, meta: dict, sections: dict, raw: str, instruction: str | None) -> None:
    """API mode: call Perplexity, validate, apply."""
    if not instruction:
        console.print("[red]API mode requires --instruction flag.[/red]")
        console.print("Usage: cns update <slug> --mode api --instruction \"...\"")
        sys.exit(1)

    # Check API key before importing the client
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        console.print(
            "[red]Perplexity API key not configured.[/red]\n"
            "Use local mode or connector mode, or add PERPLEXITY_API_KEY to .env."
        )
        sys.exit(1)

    from scripts.perplexity_client import send_update_request
    from scripts.validator import validate_response

    console.print(f"[bold]Sending update request for [cyan]{slug}[/cyan]...[/bold]")

    # Call Perplexity
    try:
        raw_json = send_update_request(raw, instruction)
    except RuntimeError as exc:
        console.print(f"[red]API Error: {exc}[/red]")
        sys.exit(1)

    # Parse JSON
    try:
        response_data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Failed to parse API response as JSON: {exc}[/red]")
        console.print(Panel(raw_json, title="Raw Response", border_style="red"))
        sys.exit(1)

    # Validate against schema
    valid, error_msg = validate_response(response_data)
    if not valid:
        console.print(f"[red]Validation failed: {error_msg}[/red]")
        console.print(Panel(json.dumps(response_data, indent=2), title="Invalid Response", border_style="red"))
        sys.exit(1)

    # Check for clarification
    if response_data.get("clarification_needed"):
        question = response_data.get("clarification_question", "No question provided.")
        console.print(Panel(
            f"[yellow]{question}[/yellow]",
            title="Clarification Needed",
            border_style="yellow",
        ))
        sys.exit(0)

    # Apply changes
    changes = response_data.get("changes", {})
    changes["updated_at"] = date.today().isoformat()

    new_meta, new_sections = apply_changes(
        meta.copy(), {k: v for k, v in sections.items()}, changes
    )
    new_meta["updated"] = date.today().isoformat()

    _show_diff_and_confirm(meta, new_meta, sections, new_sections, slug)


def cmd_prepare(args: argparse.Namespace) -> None:
    """Generate an edit brief for external LLM (connector mode)."""
    from scripts.connector import generate_edit_brief
    generate_edit_brief(args.slug, console)


def cmd_doctor(_args: argparse.Namespace) -> None:
    """Check environment and configuration."""
    from scripts.doctor import run_doctor
    run_doctor(console)


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate a project's frontmatter, sections, ROI, and risk categories."""
    from scripts.validator import validate_project

    slug = args.slug
    try:
        meta, sections, _ = read_project(slug)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    errors = validate_project(meta, sections)
    if not errors:
        console.print(f"[green]Project '{slug}' is valid.[/green]")
    else:
        console.print(f"[red]Project '{slug}' has {len(errors)} issue(s):[/red]")
        for err in errors:
            console.print(f"  [red]- {err}[/red]")
        sys.exit(1)


def cmd_export_xlsx(_args: argparse.Namespace) -> None:
    """Export all projects to an xlsx file."""
    try:
        path = export_xlsx()
        console.print(f"[green]Exported to {path}[/green]")
    except Exception as exc:
        console.print(f"[red]Export failed: {exc}[/red]")
        sys.exit(1)


def cmd_export_json(args: argparse.Namespace) -> None:
    """Export all projects to a JSON file."""
    output = getattr(args, "output", None)
    try:
        path = export_json(output_path=output)
        console.print(f"[green]Exported to {path}[/green]")
    except Exception as exc:
        console.print(f"[red]Export failed: {exc}[/red]")
        sys.exit(1)


def cmd_new(args: argparse.Namespace) -> None:
    """Create a new project from template with full folder scaffold."""
    slug = args.slug

    # Check if already exists
    pdir = project_dir(slug)
    if pdir.exists():
        console.print(f"[red]Project '{slug}' already exists at {pdir}[/red]")
        sys.exit(1)

    # Scaffold directories first, then write project.md
    scaffold_project_dirs(slug)
    meta, sections = new_project_template(slug)

    # Interactive interview (unless --skip-prompts)
    if not getattr(args, "skip_prompts", False):
        from scripts.local_editor import run_new_project_interview

        result = run_new_project_interview(meta, sections, console)
        if result is not None:
            meta, sections = result

    written = write_project(slug, meta, sections)
    console.print(f"[green]Created new project: {written}[/green]")
    console.print(f"[dim]Project folder: {pdir}[/dim]")


# ---------------------------------------------------------------------------
# Quest commands
# ---------------------------------------------------------------------------

def cmd_quest_init(args: argparse.Namespace) -> None:
    """Initialize quest workflow for a project."""
    from scripts.quest import quest_init

    slug = args.slug
    try:
        result = quest_init(slug)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    if result["scope_existed"]:
        console.print(f"[yellow]planning/mvp-scope.md already exists for '{slug}'.[/yellow]")
        console.print(f"[dim]Edit it directly, then run: cns quest sync {slug}[/dim]")

    for change in result["changes"]:
        console.print(f"  [green]+ {change}[/green]")

    if not result["changes"] and not result["scope_existed"]:
        console.print(f"[dim]Quest already initialized for '{slug}', no changes needed.[/dim]")
    elif result["changes"]:
        console.print(f"\n[bold green]Quest initialized for '{slug}'.[/bold green]")
        console.print(f"[dim]Next: edit planning/mvp-scope.md, then run: cns quest sync {slug}[/dim]")


def cmd_quest_show(args: argparse.Namespace) -> None:
    """Show current quest state for a project."""
    from scripts.quest import read_mvp_scope, QUEST_SECTIONS

    slug = args.slug

    # Read project.md for context
    try:
        meta, _, _ = read_project(slug)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    # Read mvp-scope.md
    try:
        scope_meta, scope_sections = read_mvp_scope(slug)
    except FileNotFoundError:
        console.print(f"[yellow]No quest initialized for '{slug}'.[/yellow]")
        console.print(f"[dim]Run: cns quest init {slug}[/dim]")
        sys.exit(1)

    # Header
    title = meta.get("title", slug)
    status = meta.get("status", "?")
    mvp_stage = meta.get("mvp_stage", "?")
    current_slice = meta.get("current_slice", scope_sections.get("Current Slice", "").split("\n")[0].strip())

    console.print()
    console.print(f"[bold cyan]{title}[/bold cyan]  [dim]({slug})[/dim]")
    console.print(f"  Status: [bold]{status}[/bold]  |  MVP Stage: [bold]{mvp_stage}[/bold]")
    if current_slice:
        console.print(f"  Current Slice: [bold yellow]{current_slice}[/bold yellow]")
    console.print()

    # Sections
    for heading in QUEST_SECTIONS:
        content = scope_sections.get(heading, "").strip()
        if content:
            console.print(f"[bold]## {heading}[/bold]")
            console.print(content)
            console.print()
        else:
            console.print(f"[bold]## {heading}[/bold]  [dim](empty)[/dim]")
            console.print()


def cmd_quest_sync(args: argparse.Namespace) -> None:
    """Sync current_slice from mvp-scope.md into project.md."""
    from scripts.quest import quest_sync

    slug = args.slug
    try:
        result = quest_sync(slug)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    if result["synced"]:
        console.print(f"[green]Synced current_slice for '{slug}':[/green]")
        console.print(f"  [bold]{result['current_slice']}[/bold]")
    else:
        console.print(f"[dim]current_slice already in sync for '{slug}'.[/dim]")


def cmd_devwatch(args: argparse.Namespace) -> None:
    """Run cns-devwatch: detect changes in project.md files and export ChangeEvents."""
    from scripts.devwatch import run_devwatch
    run_devwatch(output=args.output, since=args.since, dry_run=args.dry_run)


# ---------------------------------------------------------------------------
# CLI setup
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cns",
        description="CNS (Central Node Store) - Local-first project management CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # cns list
    sp_list = subparsers.add_parser("list", help="List all projects")
    sp_list.set_defaults(func=cmd_list)

    # cns show <slug>
    sp_show = subparsers.add_parser("show", help="Show a project")
    sp_show.add_argument("slug", help="Project slug")
    sp_show.set_defaults(func=cmd_show)

    # cns update <slug> [--mode local|api] [--instruction "..."]
    sp_update = subparsers.add_parser(
        "update",
        help="Update a project (default: interactive local mode)",
    )
    sp_update.add_argument("slug", help="Project slug")
    sp_update.add_argument(
        "--mode", "-m",
        choices=["local", "api"],
        default="local",
        help="Update mode: local (interactive, default) or api (requires Perplexity key + --instruction)",
    )
    sp_update.add_argument(
        "--instruction", "-i",
        default=None,
        help="Natural language instruction (required for api mode)",
    )
    sp_update.set_defaults(func=cmd_update)

    # cns prepare <slug>
    sp_prepare = subparsers.add_parser(
        "prepare",
        help="Generate an edit brief for external LLM (connector mode)",
    )
    sp_prepare.add_argument("slug", help="Project slug")
    sp_prepare.set_defaults(func=cmd_prepare)

    # cns doctor
    sp_doctor = subparsers.add_parser("doctor", help="Check environment and configuration")
    sp_doctor.set_defaults(func=cmd_doctor)

    # cns export xlsx
    sp_export = subparsers.add_parser("export", help="Export data")
    export_sub = sp_export.add_subparsers(dest="format")
    sp_xlsx = export_sub.add_parser("xlsx", help="Export to Excel")
    sp_xlsx.set_defaults(func=cmd_export_xlsx)

    sp_json = export_sub.add_parser("json", help="Export to JSON")
    sp_json.add_argument(
        "--output", "-o", default=None,
        help="Override output path (default: exports/projects.json)",
    )
    sp_json.set_defaults(func=cmd_export_json)

    # cns new <slug>
    sp_new = subparsers.add_parser("new", help="Create a new project")
    sp_new.add_argument("slug", help="Project slug (e.g. my-new-project)")
    sp_new.add_argument(
        "--skip-prompts", action="store_true", default=False,
        help="Skip interactive prompts and create a blank project",
    )
    sp_new.set_defaults(func=cmd_new)

    # cns validate <slug>
    sp_validate = subparsers.add_parser("validate", help="Validate a project file")
    sp_validate.add_argument("slug", help="Project slug")
    sp_validate.set_defaults(func=cmd_validate)

    # cns quest {init|show|sync} <slug>
    sp_quest = subparsers.add_parser("quest", help="Manage active build quest workflow")
    quest_sub = sp_quest.add_subparsers(dest="quest_command")

    sp_quest_init = quest_sub.add_parser("init", help="Initialize quest for a project")
    sp_quest_init.add_argument("slug", help="Project slug")
    sp_quest_init.set_defaults(func=cmd_quest_init)

    sp_quest_show = quest_sub.add_parser("show", help="Show current quest state")
    sp_quest_show.add_argument("slug", help="Project slug")
    sp_quest_show.set_defaults(func=cmd_quest_show)

    sp_quest_sync = quest_sub.add_parser("sync", help="Sync mvp-scope.md into project.md")
    sp_quest_sync.add_argument("slug", help="Project slug")
    sp_quest_sync.set_defaults(func=cmd_quest_sync)

    # cns devwatch
    sp_devwatch = subparsers.add_parser(
        "devwatch",
        help="Detect changes in project.md files and export ChangeEvents to JSON",
    )
    sp_devwatch.add_argument(
        "--output", "-o", default=None,
        help="Override output file path (default: exports/devwatch_YYYY-MM-DD.json)",
    )
    sp_devwatch.add_argument(
        "--since", default=None,
        help="ISO date baseline, e.g. 2026-05-18 (overrides last-run state file)",
    )
    sp_devwatch.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Print detected changes without writing output files",
    )
    sp_devwatch.set_defaults(func=cmd_devwatch)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
