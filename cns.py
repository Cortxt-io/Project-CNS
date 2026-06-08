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
    list_node_files,
    new_node_template,
    node_dir,
    node_path,
    read_node,
    scaffold_node_dirs,
    sections_for_kind,
    write_node,
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

    # Show changed sections — kind-aware
    kind = new_meta.get("kind")
    section_headings = sections_for_kind(kind)
    # Also check headings that exist in sections but not in canonical list
    all_headings = list(section_headings) + [
        h for h in set(list(sections.keys()) + list(new_sections.keys()))
        if h not in section_headings
    ]
    for heading in all_headings:
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

    path = write_node(slug, new_meta, new_sections)
    console.print(f"[green]Updated {path}[/green]")
    return True


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(_args: argparse.Namespace) -> None:
    """Print a summary table of all nodes (node-aware)."""
    files = list_node_files()
    if not files:
        console.print("[yellow]No nodes found.[/yellow]")
        return

    # Collect node data and detect which optional columns have data
    nodes_data = []
    has_any_slice = False
    has_any_cost = False
    for path in files:
        slug = path.parent.name
        try:
            meta, _, _ = read_node(slug)
        except Exception as exc:
            console.print(f"[red]Error reading {slug}: {exc}[/red]")
            continue
        if meta.get("current_slice"):
            has_any_slice = True
        if meta.get("cost_sek", 0) or meta.get("value_sek", 0) or meta.get("roi_percent", 0):
            has_any_cost = True
        nodes_data.append((slug, meta))

    # Sort by part_of so tree structure is visible — nodes with same parent cluster together
    nodes_data.sort(key=lambda x: (x[1].get("part_of", "") or "", x[0]))

    kind_color_map = {
        "framework": "bold magenta",
        "system": "cyan",
        "component": "green",
    }
    stage_color_map = {
        "idea": "dim",
        "building": "yellow",
        "working": "green",
        "maturing": "bold green",
    }
    status_color_map = {
        "idea": "dim",
        "early_mvp": "yellow",
        "mvp": "green",
        "live": "bold green",
        "shelved": "dim red",
    }

    table = Table(title="CNS Nodes", show_lines=True)
    table.add_column("Slug", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Kind")
    table.add_column("Stage")
    table.add_column("Part Of", style="dim")
    table.add_column("Status")
    if has_any_slice:
        table.add_column("Current Slice", max_width=30, no_wrap=True)
    if has_any_cost:
        table.add_column("Cost", justify="right")
        table.add_column("Value", justify="right")
        table.add_column("ROI %", justify="right")

    for slug, meta in nodes_data:
        kind = meta.get("kind", "")
        stage = meta.get("stage", "")
        status = meta.get("status", "")
        part_of = meta.get("part_of", "") or ""

        kind_c = kind_color_map.get(kind, "dim")
        stage_c = stage_color_map.get(stage, "")
        status_c = status_color_map.get(status, "")

        row = [
            slug,
            meta.get("title", ""),
            f"[{kind_c}]{kind or '—'}[/{kind_c}]",
            f"[{stage_c}]{stage}[/{stage_c}]" if stage_c else stage or "—",
            part_of,
            f"[{status_c}]{status}[/{status_c}]" if status_c else status,
        ]
        if has_any_slice:
            slice_val = meta.get("current_slice", "")
            if len(slice_val) > 30:
                slice_val = slice_val[:27] + "..."
            row.append(f"[yellow]{slice_val}[/yellow]" if slice_val else "")
        if has_any_cost:
            cost = meta.get("cost_sek", 0) or 0
            value = meta.get("value_sek", 0) or 0
            roi = meta.get("roi_percent", 0) or 0
            row.extend([
                f"{cost:,}",
                f"{value:,}",
                f"{roi}%",
            ])
        table.add_row(*row)

    console.print(table)


def cmd_show(args: argparse.Namespace) -> None:
    """Print the full content of a single node file."""
    slug = args.slug
    try:
        meta, sections, raw = read_node(slug)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    console.print(Panel(raw, title=f"[bold cyan]{meta.get('title', slug)}[/bold cyan]", border_style="blue"))


def cmd_update(args: argparse.Namespace) -> None:
    """Update a node (local mode or api mode)."""
    slug = args.slug
    instruction = getattr(args, "instruction", None)
    mode = getattr(args, "mode", "local")

    # Smart default: if --instruction is provided without --mode, use api mode
    if instruction and mode == "local":
        mode = "api"
        console.print("[dim]Detected --instruction flag, using api mode.[/dim]")

    # Read current node
    try:
        meta, sections, raw = read_node(slug)
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
    """Validate a node's frontmatter, sections, ROI, and risk categories."""
    from scripts.validator import validate_node

    slug = args.slug
    try:
        meta, sections, _ = read_node(slug)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    errors = validate_node(meta, sections)
    if not errors:
        console.print(f"[green]Node '{slug}' is valid.[/green]")
    else:
        console.print(f"[red]Node '{slug}' has {len(errors)} issue(s):[/red]")
        for err in errors:
            console.print(f"  [red]- {err}[/red]")
        sys.exit(1)


def cmd_export_xlsx(_args: argparse.Namespace) -> None:
    """Export all nodes to an xlsx file."""
    try:
        path = export_xlsx()
        console.print(f"[green]Exported to {path}[/green]")
    except Exception as exc:
        console.print(f"[red]Export failed: {exc}[/red]")
        sys.exit(1)


def cmd_export_json(args: argparse.Namespace) -> None:
    """Export all nodes to a JSON file."""
    output = getattr(args, "output", None)
    try:
        path = export_json(output_path=output)
        console.print(f"[green]Exported to {path}[/green]")
    except Exception as exc:
        console.print(f"[red]Export failed: {exc}[/red]")
        sys.exit(1)


def cmd_new(args: argparse.Namespace) -> None:
    """Create a new node from template with full folder scaffold."""
    slug = args.slug
    kind = getattr(args, "kind", None)

    # Check if already exists
    pdir = node_dir(slug)
    if pdir.exists():
        console.print(f"[red]Node '{slug}' already exists at {pdir}[/red]")
        sys.exit(1)

    # Scaffold directories first, then write node.md
    scaffold_node_dirs(slug)
    meta, sections = new_node_template(slug, kind=kind)

    # Interactive interview (unless --skip-prompts)
    if not getattr(args, "skip_prompts", False):
        from scripts.local_editor import run_new_node_interview

        result = run_new_node_interview(meta, sections, console)
        if result is not None:
            meta, sections = result

    written = write_node(slug, meta, sections)
    console.print(f"[green]Created new node: {written}[/green]")
    if kind:
        console.print(f"[dim]Kind: {kind} | Stage: {meta.get('stage', 'idea')}[/dim]")
    console.print(f"[dim]Node folder: {pdir}[/dim]")


# ---------------------------------------------------------------------------
# Quest commands
# ---------------------------------------------------------------------------

def cmd_quest_init(args: argparse.Namespace) -> None:
    """Initialize quest workflow for a node."""
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
    """Show current quest state for a node."""
    from scripts.quest import read_mvp_scope, QUEST_SECTIONS

    slug = args.slug

    # Read node.md for context
    try:
        meta, _, _ = read_node(slug)
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
    """Sync current_slice from mvp-scope.md into node.md."""
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
    """Run cns-devwatch: detect changes in node.md files and export ChangeEvents."""
    from scripts.devwatch import run_devwatch
    run_devwatch(output=args.output, since=args.since, dry_run=args.dry_run)


def cmd_devlog(args: argparse.Namespace) -> None:
    """Run cns-devlog: generate AI digest from devwatch output and render static HTML."""
    from scripts.devlog import run_devlog
    run_devlog(input_path=args.input, output_path=args.output, dry_run=args.dry_run)


def cmd_watch(_args: argparse.Namespace) -> None:
    """Start file watcher for auto-updating 'updated' timestamps."""
    from scripts.file_watcher import run_watch
    run_watch()


def cmd_analyze(args: argparse.Namespace) -> None:
    """AI-analyze a node and suggest field updates."""
    from scripts.analyst import run_analyze
    try:
        run_analyze(
            args.slug,
            _show_diff_and_confirm,
            dry_run=getattr(args, "dry_run", False),
        )
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


def cmd_scaffold(_args: argparse.Namespace) -> None:
    """Ensure all node directories exist."""
    from scripts.md_parser import ensure_all_node_dirs
    created = ensure_all_node_dirs()
    if created:
        for slug in created:
            console.print(f"[green]Scaffolded missing dirs for: {slug}[/green]")
    else:
        console.print("[dim]All node directories already complete.[/dim]")


def cmd_install_hooks(_args: argparse.Namespace) -> None:
    """Install git hooks for CNS."""
    from scripts.install_hooks import install_post_commit_hook
    install_post_commit_hook()


def cmd_post_commit_analyze(_args: argparse.Namespace) -> None:
    """Identify slugs changed in last commit and queue analyze."""
    import subprocess
    from scripts.analyst import run_analyze
    from pathlib import Path

    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "-r",
         "--name-only", "HEAD"],
        capture_output=True, text=True
    )
    changed_files = result.stdout.strip().splitlines()

    slugs = set()
    for f in changed_files:
        parts = Path(f).parts
        if len(parts) >= 2 and parts[0] == "nodes":
            slugs.add(parts[1])

    if not slugs:
        return

    EXPORTS_DIR = Path("exports")
    EXPORTS_DIR.mkdir(exist_ok=True)
    today = date.today().isoformat()

    for slug in sorted(slugs):
        output_path = EXPORTS_DIR / f"analyze_{slug}_{today}.json"
        try:
            run_analyze(slug, confirm_fn=None, output_path=output_path)
        except Exception as exc:
            print(f"[cns post-commit] Error analyzing {slug}: {exc}")


def cmd_review(_args: argparse.Namespace) -> None:
    """Review and apply pending AI suggestions."""
    from scripts.analyst import load_pending_suggestions, apply_pending

    pending_list = load_pending_suggestions()
    if not pending_list:
        console.print("[dim]No pending suggestions.[/dim]")
        return

    console.print(f"[bold]{len(pending_list)} pending suggestion(s):[/bold]")
    for item in pending_list:
        console.print(
            f"  [cyan]{item['slug']}[/cyan] "
            f"[dim](analyzed {item['analyzed_at']})[/dim]"
        )
    console.print()

    for item in pending_list:
        console.print(
            f"[bold]Reviewing suggestions for "
            f"[cyan]{item['slug']}[/cyan]:[/bold]"
        )
        apply_pending(item, _show_diff_and_confirm)


def cmd_eventstream_sync(args: argparse.Namespace) -> None:
    """Pull events from GitHub API and append to .jsonl archive."""
    from scripts.eventstream import run_sync

    since = args.since
    dry_run = args.dry_run

    if dry_run:
        console.print("[dim]Dry run — showing what would be synced:[/dim]")
        if since:
            console.print(f"  Since: {since}")
        else:
            console.print("  Since: last 24h (default)")
        console.print("  Would fetch from: github_commits, github_workflows, railway, cloudflare")
        return

    console.print("[bold]Syncing eventstream...[/bold]")
    if since:
        console.print(f"  Since: {since}")

    counts = run_sync(since=since)

    for source, count in counts.items():
        if count < 0:
            console.print(f"  [red]{source}: adapter failed[/red]")
        else:
            console.print(f"  [green]{source}:[/green] {count} new events")

    total = counts.get("total_new", 0)
    console.print(f"\n[bold]Total: {total} new events archived[/bold]")


def cmd_eventstream_import(args: argparse.Namespace) -> None:
    """Import a one-time batch of historical events into eventstream."""
    from scripts.eventstream import import_retroactive_events

    events_file = args.file
    console.print(f"[bold]Importing retroactive events from {events_file}...[/bold]")

    count = import_retroactive_events(events_file)
    console.print(f"[green]Imported {count} events[/green]")

    if args.delete:
        import os
        os.remove(events_file)
        console.print(f"[dim]Deleted {events_file} (one-time import)[/dim]")


# ---------------------------------------------------------------------------
# CLI setup
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cns",
        description="CNS (Central Node Store) - Local-first node management CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # cns list
    sp_list = subparsers.add_parser("list", help="List all nodes")
    sp_list.set_defaults(func=cmd_list)

    # cns show <slug>
    sp_show = subparsers.add_parser("show", help="Show a node")
    sp_show.add_argument("slug", help="Node slug")
    sp_show.set_defaults(func=cmd_show)

    # cns update <slug> [--mode local|api] [--instruction "..."]
    sp_update = subparsers.add_parser(
        "update",
        help="Update a node (default: interactive local mode)",
    )
    sp_update.add_argument("slug", help="Node slug")
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
    sp_prepare.add_argument("slug", help="Node slug")
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
        help="Override output path (default: exports/nodes.json)",
    )
    sp_json.set_defaults(func=cmd_export_json)

    # cns new <slug>
    sp_new = subparsers.add_parser("new", help="Create a new node")
    sp_new.add_argument("slug", help="Node slug (e.g. my-new-node)")
    sp_new.add_argument(
        "--kind", "-k",
        choices=["component", "system", "framework"],
        default=None,
        help="Node kind (default: legacy product template)",
    )
    sp_new.add_argument(
        "--skip-prompts", action="store_true", default=False,
        help="Skip interactive prompts and create a blank node",
    )
    sp_new.set_defaults(func=cmd_new)

    # cns validate <slug>
    sp_validate = subparsers.add_parser("validate", help="Validate a node file")
    sp_validate.add_argument("slug", help="Node slug")
    sp_validate.set_defaults(func=cmd_validate)

    # cns quest {init|show|sync} <slug>
    sp_quest = subparsers.add_parser("quest", help="Manage active build quest workflow")
    quest_sub = sp_quest.add_subparsers(dest="quest_command")

    sp_quest_init = quest_sub.add_parser("init", help="Initialize quest for a node")
    sp_quest_init.add_argument("slug", help="Node slug")
    sp_quest_init.set_defaults(func=cmd_quest_init)

    sp_quest_show = quest_sub.add_parser("show", help="Show current quest state")
    sp_quest_show.add_argument("slug", help="Node slug")
    sp_quest_show.set_defaults(func=cmd_quest_show)

    sp_quest_sync = quest_sub.add_parser("sync", help="Sync mvp-scope.md into node.md")
    sp_quest_sync.add_argument("slug", help="Node slug")
    sp_quest_sync.set_defaults(func=cmd_quest_sync)

    # cns devwatch
    sp_devwatch = subparsers.add_parser(
        "devwatch",
        help="Detect changes in node.md files and export ChangeEvents to JSON",
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

    # cns devlog
    sp_devlog = subparsers.add_parser(
        "devlog",
        help="Generate AI digest from devwatch output and render static HTML",
    )
    sp_devlog.add_argument(
        "--input", "-i", default=None,
        help="Override devwatch JSON path (default: latest exports/devwatch_YYYY-MM-DD.json)",
    )
    sp_devlog.add_argument(
        "--output", "-o", default=None,
        help="Override HTML output path (default: exports/devlog_YYYY-MM-DD.html)",
    )
    sp_devlog.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Print prompt and skip Claude call + file write",
    )
    sp_devlog.set_defaults(func=cmd_devlog)

    # cns watch
    sp_watch = subparsers.add_parser(
        "watch",
        help="Watch nodes/ for changes and auto-update 'updated' timestamp",
    )
    sp_watch.set_defaults(func=cmd_watch)

    # cns analyze <slug> [--dry-run]
    sp_analyze = subparsers.add_parser(
        "analyze",
        help="AI-analyze a node and suggest field updates",
    )
    sp_analyze.add_argument("slug", help="Node slug")
    sp_analyze.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Run analysis without saving or applying changes",
    )
    sp_analyze.set_defaults(func=cmd_analyze)

    # cns scaffold
    sp_scaffold = subparsers.add_parser(
        "scaffold",
        help="Ensure all node directories exist",
    )
    sp_scaffold.set_defaults(func=cmd_scaffold)

    # cns install-hooks
    sp_install_hooks = subparsers.add_parser(
        "install-hooks",
        help="Install git hooks for CNS",
    )
    sp_install_hooks.set_defaults(func=cmd_install_hooks)

    # cns post-commit-analyze
    sp_post_commit = subparsers.add_parser(
        "post-commit-analyze",
        help="Analyze nodes changed in the last commit (intended for git hooks)",
    )
    sp_post_commit.set_defaults(func=cmd_post_commit_analyze)

    # cns review
    sp_review = subparsers.add_parser(
        "review",
        help="Review and apply pending AI suggestions",
    )
    sp_review.set_defaults(func=cmd_review)

    # cns eventstream sync
    sp_eventstream = subparsers.add_parser(
        "eventstream",
        help="Eventstream operations",
    )
    es_sub = sp_eventstream.add_subparsers(dest="es_command")
    sp_es_sync = es_sub.add_parser(
        "sync",
        help="Pull events from GitHub API and append to .jsonl archive",
    )
    sp_es_sync.add_argument(
        "--since", default=None,
        help="ISO timestamp to pull events since (default: last 24h)",
    )
    sp_es_sync.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Show what would be synced without writing files",
    )
    sp_es_sync.set_defaults(func=cmd_eventstream_sync)

    sp_es_import = es_sub.add_parser(
        "import",
        help="Import a one-time batch of historical events from a JSON file",
    )
    sp_es_import.add_argument(
        "file",
        help="Path to JSON file containing events array",
    )
    sp_es_import.add_argument(
        "--delete", action="store_true", default=False,
        help="Delete the import file after successful import",
    )
    sp_es_import.set_defaults(func=cmd_eventstream_import)

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
