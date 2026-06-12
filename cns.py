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
    read_node,
    read_all_nodes,
)
from scripts.xlsx_exporter import export_xlsx
from scripts.json_exporter import export_json

# Tvinga utf-8 på stdout så Rich inte kraschar på cp1252-konsoler när nod-/
# sessiondata innehåller unicode (pilar, em-dash m.m.) — samma skydd som dash.py.
import io as _io

console = Console(
    file=_io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace"),
    highlight=False,
)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(_args: argparse.Namespace) -> None:
    """Print a summary table of all nodes (node-aware)."""
    all_nodes = read_all_nodes()  # ur catalog.yaml (#101)
    if not all_nodes:
        console.print("[yellow]No nodes found.[/yellow]")
        return

    # Collect node data and detect which optional columns have data
    nodes_data = []
    has_any_slice = False
    has_any_cost = False
    for meta, _sections in all_nodes:
        slug = meta.get("slug", "")
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
    """Interaktiv redigering av ett systems katalogfält (nodmodell-teardown #105).

    Redigerar catalog.yaml-fälten direkt. `kind` härleds (redigeras ej). Varaktig
    beslutsprosa hör till decisions/<slug>.md, inte hit.
    """
    from rich.prompt import Prompt
    from scripts.catalog import load_catalog, upsert_system

    slug = args.slug
    systems = load_catalog()
    if slug not in systems:
        console.print(f"[red]System '{slug}' saknas i catalog.yaml[/red]")
        sys.exit(1)

    entry = systems[slug]
    console.print(f"\n[bold]Redigerar[/bold] [cyan]{slug}[/cyan]  [dim](Enter behåller nuvarande)[/dim]\n")

    fields: dict = {}
    # Skalärfält — bara icke-tomma ändringar (rensa ett fält = redigera catalog.yaml för hand)
    for label, key in (("Title", "title"), ("Summary", "summary"),
                       ("Part of (tomt = toppnivå)", "part_of"),
                       ("Type", "type"), ("Domain", "domain"), ("Owner agent", "owner_agent")):
        current = str(entry.get(key, "") or "")
        val = Prompt.ask(f"  {label}", default=current).strip()
        if val and val != current:
            fields[key] = val

    # Listfält (kommaseparerat)
    for label, key in (("Feeds (komma)", "feeds"), ("Depends on (komma)", "depends_on")):
        current_list = entry.get(key) or []
        val = Prompt.ask(f"  {label}", default=", ".join(current_list)).strip()
        new_list = [s.strip() for s in val.split(",") if s.strip()]
        if new_list != current_list:
            fields[key] = new_list

    if not fields:
        console.print("  [dim](inga ändringar)[/dim]")
        return

    upsert_system(slug, fields)
    console.print(f"[green]Uppdaterade '{slug}' i catalog.yaml.[/green]")


def cmd_prepare(args: argparse.Namespace) -> None:
    """Generate an edit brief for external LLM (connector mode)."""
    from scripts.connector import generate_edit_brief
    generate_edit_brief(args.slug, console)


def cmd_doctor(_args: argparse.Namespace) -> None:
    """Check environment and configuration."""
    from scripts.doctor import run_doctor
    run_doctor(console)


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate the catalog (nodmodell-teardown #100).

    `cns validate`          → validera hela catalog.yaml (referensintegritet + cykler + enums).
    `cns validate <slug>`   → validera bara ett system (delmängd av katalog-checkarna).
    """
    from scripts.catalog import load_catalog
    from scripts.validator import validate_catalog

    systems = load_catalog()
    slug = getattr(args, "slug", None)

    if slug and slug not in systems:
        console.print(f"[red]System '{slug}' saknas i catalog.yaml[/red]")
        sys.exit(1)

    errors, warnings = validate_catalog(systems)
    if slug:
        # Filtrera till rader som rör detta system.
        errors = [e for e in errors if e.startswith(f"{slug}:")]
        warnings = [w for w in warnings if w.startswith(f"{slug}:")]

    target = f"System '{slug}'" if slug else f"Katalogen ({len(systems)} system)"
    for warn in warnings:
        console.print(f"  [yellow]WARN: {warn}[/yellow]")
    if not errors:
        console.print(f"[green]{target} är giltig.[/green]")
    else:
        console.print(f"[red]{target} har {len(errors)} fel:[/red]")
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
    """Create a new system entry in catalog.yaml (nodmodell-teardown #105)."""
    from rich.prompt import Prompt
    from scripts.catalog import load_catalog, upsert_system

    slug = args.slug
    systems = load_catalog()
    if slug in systems:
        console.print(f"[red]System '{slug}' finns redan i catalog.yaml[/red]")
        sys.exit(1)

    fields: dict = {"title": slug.replace("-", " ").title(), "feeds": [], "depends_on": []}

    if not getattr(args, "skip_prompts", False):
        console.print(f"\n[bold]Nytt system:[/bold] [cyan]{slug}[/cyan]  [dim](Enter hoppar över)[/dim]\n")
        fields["title"] = (Prompt.ask("  Title", default=fields["title"]).strip() or fields["title"])
        for label, key in (("Summary", "summary"), ("Part of (slug, tomt = toppnivå)", "part_of"),
                           ("Type", "type"), ("Domain", "domain")):
            val = Prompt.ask(f"  {label}", default="").strip()
            if val:
                fields[key] = val

    upsert_system(slug, fields)
    console.print(f"[green]Skapade system '{slug}' i catalog.yaml.[/green]")
    console.print("[dim]kind härleds ur part_of. Redigera vidare med 'cns update' eller i catalog.yaml. "
                  "Varaktig beslutsprosa → decisions/<slug>.md.[/dim]")


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
# Session commands (AI-arbetspass — lokalt datalager; push sker via MCP)
# ---------------------------------------------------------------------------

def _session_link_str(s: dict) -> str:
    link = s.get("link") or {}
    return f"({link.get('kind', '?')}:{link.get('ref', '?')}) " if link else ""


def cmd_session_list(args: argparse.Namespace) -> None:
    """Lista sessioner (nyast först), valfritt filtrerade på status."""
    from scripts.session_store import list_sessions

    sessions = list_sessions(status=args.status)
    if not sessions:
        console.print("[dim]Inga sessioner bokförda.[/dim]")
        return
    for s in sessions:
        dot = "[bold green]*[/bold green]" if s.get("status") == "running" else "[dim]-[/dim]"
        stype = s.get("session_type") or "-"
        summary = (s.get("summary") or "-")[:70]
        console.print(f"{dot} [cyan]{s.get('id', '?')}[/cyan]  [dim]{stype}[/dim]  {_session_link_str(s)}{summary}")


def cmd_session_show(args: argparse.Namespace) -> None:
    """Visa en session i detalj (rå JSON)."""
    from scripts.session_store import get_session

    s = get_session(args.session_id)
    if s is None:
        console.print(f"[red]Session '{args.session_id}' hittades inte.[/red]")
        sys.exit(1)
    console.print_json(data=s)


def cmd_session_fork(args: argparse.Namespace) -> None:
    """Forka en barn-session under en förälder (bokför i sessionsträdet)."""
    from scripts.session_store import fork_session

    try:
        s = fork_session(args.parent_id, summary=args.summary or "", fork_name=args.name)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)
    console.print(f"[green]Forkade session [cyan]{s.get('id')}[/cyan] under {args.parent_id}.[/green]")


def cmd_session_tree(args: argparse.Namespace) -> None:
    """Visa sessionsträdet (forks-under-forks)."""
    from scripts.session_store import tree

    result = tree(args.root_id)
    roots = ([result] if result else []) if args.root_id is not None else (result or [])
    if not roots:
        console.print("[dim]Inga sessioner.[/dim]")
        return

    def render(node: dict, depth: int = 0) -> None:
        dot = "[bold green]*[/bold green]" if node.get("status") == "running" else "[dim]-[/dim]"
        name = node.get("fork_name") or node.get("id", "?")
        summary = (node.get("summary") or "")[:55]
        console.print(f"{'  ' * depth}{dot} [cyan]{name}[/cyan] [dim]{summary}[/dim]")
        for kid in node.get("children", []):
            render(kid, depth + 1)

    for r in roots:
        render(r)


def cmd_session_set_active(args: argparse.Namespace) -> None:
    """Sätt lokal aktiv sessionstyp-markör (läses av router-hooken)."""
    from scripts.session_store import set_active

    try:
        state = set_active(args.session_type, session_id=args.session_id)
    except Exception as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)
    console.print(f"[green]Aktiv sessionstyp: [bold]{state['type']}[/bold][/green]")


def cmd_session_get_active(args: argparse.Namespace) -> None:
    """Visa aktiv sessionstyp-markör."""
    from scripts.session_store import get_active

    state = get_active()
    if not state:
        console.print("[dim]Ingen aktiv sessionstyp satt.[/dim]")
        return
    console.print(
        f"[bold]{state.get('type')}[/bold]  "
        f"[dim]session_id={state.get('session_id')}  set_at={state.get('set_at')}[/dim]"
    )


def cmd_session_clear_active(args: argparse.Namespace) -> None:
    """Rensa aktiv sessionstyp-markör."""
    from scripts.session_store import clear_active

    clear_active()
    console.print("[dim]Aktiv sessionstyp rensad.[/dim]")


# ---------------------------------------------------------------------------
# btw commands (personlig sessionslogg — lokalt datalager; push via MCP)
# ---------------------------------------------------------------------------

def cmd_btw_list(args: argparse.Namespace) -> None:
    """Lista btw-sessionsloggar (senast uppdaterad först)."""
    from scripts.btw_log import list_sessions

    sessions = list_sessions()
    if not sessions:
        console.print("[dim]Inga btw-loggar.[/dim]")
        return
    for s in sessions:
        n = len(s.get("asides", []))
        console.print(
            f"[cyan]{s.get('session_id', '?')}[/cyan]  "
            f"[dim]{n} asides  {s.get('updated_at', '')}[/dim]"
        )


def cmd_btw_show(args: argparse.Namespace) -> None:
    """Visa asides i en btw-session."""
    from scripts.btw_log import get_session

    s = get_session(args.session_id)
    if s is None:
        console.print(f"[red]btw-session '{args.session_id}' hittades inte.[/red]")
        sys.exit(1)
    asides = s.get("asides", [])
    if not asides:
        console.print("[dim]Inga asides.[/dim]")
        return
    for a in asides:
        fork = a.get("fork") or ""
        console.print(f"[dim]{a.get('ts', '')}[/dim] [yellow]{fork}[/yellow] {a.get('text', '')}")


def cmd_btw_link(args: argparse.Namespace) -> None:
    """Soft-länka en btw-session till quest och/eller idé."""
    from scripts.btw_log import link_session

    try:
        link_session(args.session_id, quest_id=args.quest, idea_id=args.idea)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)
    console.print(f"[green]Länkade btw-session {args.session_id}.[/green]")


# ---------------------------------------------------------------------------
# TUI command (lazy import — textual laddas inte vid varje cns-anrop)
# ---------------------------------------------------------------------------

def cmd_tui(args: argparse.Namespace) -> None:
    """Starta den interaktiva terminal-överblicken (Textual)."""
    from scripts.tui.app import main as tui_main

    tui_main()


def cmd_derive(args: argparse.Namespace) -> None:
    """Härled nodkatalogen ur verkligheten + diffa mot catalog.yaml (Del A, skiva 1)."""
    from scripts import derive_catalog as dc

    derived = dc.derive_from_disk()
    if args.diff:
        report = dc.diff_against_catalog(derived, dc.load_current_catalog())
        print(report.as_text())
        return
    path = dc.write_derived(derived)
    print(f"Härledde {len(derived)} noder → {path}")
    print("Kör 'cns derive --diff' för att se skillnaden mot catalog.yaml.")


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
        help="Interaktiv redigering av ett systems katalogfält",
    )
    sp_update.add_argument("slug", help="System-slug")
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
    sp_new = subparsers.add_parser("new", help="Create a new system in catalog.yaml")
    sp_new.add_argument("slug", help="System-slug (e.g. my-new-system)")
    sp_new.add_argument(
        "--skip-prompts", action="store_true", default=False,
        help="Hoppa interaktiva prompts, skapa en minimal post",
    )
    sp_new.set_defaults(func=cmd_new)

    # cns validate [slug]  — utan slug: hela catalog.yaml
    sp_validate = subparsers.add_parser("validate", help="Validate the catalog (or one system)")
    sp_validate.add_argument("slug", nargs="?", default=None, help="System-slug (utelämna för hela katalogen)")
    sp_validate.set_defaults(func=cmd_validate)

    # cns derive — härled katalogen ur verkligheten + diffa (Del A)
    sp_derive = subparsers.add_parser(
        "derive", help="Härled nodkatalogen ur verkligheten (agents.json, .mcp.json) + diffa"
    )
    sp_derive.add_argument(
        "--diff", action="store_true",
        help="Visa diff mot catalog.yaml i stället för att skriva catalog.derived.yaml",
    )
    sp_derive.set_defaults(func=cmd_derive)

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

    # cns session {list|show|fork|tree|set-active|get-active|clear-active}
    sp_session = subparsers.add_parser("session", help="AI-arbetspass (sessioner) — lokalt datalager")
    session_sub = sp_session.add_subparsers(dest="session_command")

    sp_s_list = session_sub.add_parser("list", help="Lista sessioner (nyast först)")
    sp_s_list.add_argument("--status", default=None, help="Filtrera på status, t.ex. running/done")
    sp_s_list.set_defaults(func=cmd_session_list)

    sp_s_show = session_sub.add_parser("show", help="Visa en session i detalj")
    sp_s_show.add_argument("session_id", help="Sessions-id")
    sp_s_show.set_defaults(func=cmd_session_show)

    sp_s_fork = session_sub.add_parser("fork", help="Forka en barn-session under en förälder")
    sp_s_fork.add_argument("parent_id", help="Förälderns sessions-id")
    sp_s_fork.add_argument("--summary", default=None, help="Sammanfattning för barn-sessionen")
    sp_s_fork.add_argument("--name", default=None, help="Fork-namn (t.ex. agent-slug)")
    sp_s_fork.set_defaults(func=cmd_session_fork)

    sp_s_tree = session_sub.add_parser("tree", help="Visa sessionsträdet")
    sp_s_tree.add_argument("root_id", nargs="?", default=None, help="Valfri rot (annars alla rötter)")
    sp_s_tree.set_defaults(func=cmd_session_tree)

    sp_s_seta = session_sub.add_parser("set-active", help="Sätt lokal aktiv sessionstyp")
    sp_s_seta.add_argument("session_type", help="brainstorm|spec|bygg|triage|review|verktygsladan|retro")
    sp_s_seta.add_argument("--session-id", dest="session_id", default=None, help="Koppla markören till ett sessions-id")
    sp_s_seta.set_defaults(func=cmd_session_set_active)

    sp_s_geta = session_sub.add_parser("get-active", help="Visa aktiv sessionstyp")
    sp_s_geta.set_defaults(func=cmd_session_get_active)

    sp_s_clra = session_sub.add_parser("clear-active", help="Rensa aktiv sessionstyp")
    sp_s_clra.set_defaults(func=cmd_session_clear_active)

    # cns btw {list|show|link}
    sp_btw = subparsers.add_parser("btw", help="Personlig btw-sessionslogg — lokalt datalager")
    btw_sub = sp_btw.add_subparsers(dest="btw_command")

    sp_b_list = btw_sub.add_parser("list", help="Lista btw-loggar")
    sp_b_list.set_defaults(func=cmd_btw_list)

    sp_b_show = btw_sub.add_parser("show", help="Visa asides i en btw-session")
    sp_b_show.add_argument("session_id", help="Sessions-id")
    sp_b_show.set_defaults(func=cmd_btw_show)

    sp_b_link = btw_sub.add_parser("link", help="Soft-länka en btw-session till quest/idé")
    sp_b_link.add_argument("session_id", help="Sessions-id")
    sp_b_link.add_argument("--quest", default=None, help="Quest-id att länka till")
    sp_b_link.add_argument("--idea", default=None, help="Idé-id att länka till")
    sp_b_link.set_defaults(func=cmd_btw_link)

    # cns tui
    sp_tui = subparsers.add_parser("tui", help="Starta interaktiv terminal-överblick (Textual)")
    sp_tui.set_defaults(func=cmd_tui)

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
