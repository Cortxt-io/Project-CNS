#!/usr/bin/env python3
"""CNS (Central Node Store) - CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scripts.md_parser import (
    read_node,
    read_all_nodes,
)
# NB: xlsx_exporter/json_exporter live in lab/scripts (dashboard/agency exports)
# and are imported lazily inside their command functions, so Core runs without lab/.

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


def _deploy_entry(slug: str, target: str = "vercel") -> Optional[dict]:
    """Plocka nodens deploy-post för en target ur catalog.integrations (#77/#78).

    Returnerar ett normaliserat ``{"target", "project"}``-dict (project tomt om platt str-form),
    eller ``None`` om noden saknar/inte deployar till target. Robust mot alla integrations-former.
    """
    from scripts.catalog import load_catalog

    systems = load_catalog()
    if slug not in systems:
        return None
    deploy = (systems[slug].get("integrations") or {}).get("deploy") or {}
    items = list(deploy.keys()) if isinstance(deploy, dict) else deploy
    for item in items:
        if isinstance(item, dict) and item.get("target") == target:
            return {"target": target, "project": item.get("project", "")}
        if isinstance(item, str) and item == target:
            return {"target": target, "project": ""}
    return None


def cmd_deploy_connect(args: argparse.Namespace) -> None:
    """`cns deploy connect` — verifiera Vercel-token (read-only)."""
    from scripts.adapters import vercel

    out = vercel.connect()
    if out.get("ok"):
        console.print(f"[green]Vercel: ansluten som {out.get('user', '')}[/green]")
    else:
        console.print(f"[yellow]Vercel ej ansluten: {out.get('error', '')}[/yellow]")


def cmd_deploy_status(args: argparse.Namespace) -> None:
    """`cns deploy status <slug>` — senaste Vercel-deployment-status för en nod (read-only)."""
    from scripts.adapters import vercel

    entry = _deploy_entry(args.slug, "vercel")
    if entry is None:
        console.print(f"[yellow]'{args.slug}' har ingen vercel-deploy i catalog.integrations[/yellow]")
        return
    project = entry.get("project") or args.slug
    out = vercel.status(project)
    if out.get("ok"):
        console.print(f"[green]{args.slug} → vercel/{project}: {out.get('state')}[/green] {out.get('url', '')}")
    else:
        console.print(f"[yellow]Vercel-status otillgänglig: {out.get('error', '')}[/yellow]")


def cmd_deploy_deploy(args: argparse.Namespace) -> None:
    """`cns deploy deploy <slug> --yes` — trigga en Vercel-deployment (MUTATING, gated)."""
    from scripts.adapters import vercel

    entry = _deploy_entry(args.slug, "vercel")
    if entry is None:
        console.print(f"[yellow]'{args.slug}' har ingen vercel-deploy i catalog.integrations[/yellow]")
        return
    if not getattr(args, "yes", False):
        console.print("[red]deploy är muterande — kräver --yes för att köras.[/red]")
        sys.exit(1)
    project = entry.get("project") or args.slug
    out = vercel.deploy(project, ref=getattr(args, "ref", "main"))
    if out.get("ok"):
        console.print(f"[green]Deploy triggad: {project} ({out.get('state')}) {out.get('url', '')}[/green]")
    else:
        console.print(f"[red]Deploy misslyckades: {out.get('error', '')}[/red]")
        sys.exit(1)


def cmd_project_sync(args: argparse.Namespace) -> None:
    """Sync open issues → the org Project 'Backlog' (GitHub Projects v2). [Lab: board]"""
    from scripts.gh_project_sync import sync, _cli_token

    if not _cli_token():
        console.print(
            "[red]Ingen token. Sätt CNS_GITHUB_TOKEN (project-scope) eller kör "
            "`gh auth refresh -s project`.[/red]"
        )
        sys.exit(1)
    try:
        res = sync(dry_run=getattr(args, "dry_run", False))
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)
    tag = " (dry-run)" if res["dry_run"] else ""
    console.print(
        f"[green]Issues: {res['issues']} | tillagda: {res['added']} | "
        f"fält satta: {res['field_values_set']}{tag}[/green]"
    )
    if res["missing_options"]:
        console.print("[yellow]Saknade single-select-options (lägg dem på fältet i UI):[/yellow]")
        for o in res["missing_options"]:
            console.print(f"  - {o}")


def cmd_export_xlsx(_args: argparse.Namespace) -> None:
    """Export all nodes to an xlsx file. [Lab: dashboard export]"""
    from scripts.xlsx_exporter import export_xlsx
    try:
        path = export_xlsx()
        console.print(f"[green]Exported to {path}[/green]")
    except Exception as exc:
        console.print(f"[red]Export failed: {exc}[/red]")
        sys.exit(1)


def cmd_export_json(args: argparse.Namespace) -> None:
    """Export all nodes to a JSON file. [Lab: dashboard nodes.json]"""
    from scripts.json_exporter import export_json
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


def _node_export_payload(slug: str) -> dict:
    """Gather a node's catalog fields + decision prose into one dict.

    Pure local read — no network, no agency. Used by `cns export <slug>`.
    """
    from scripts.catalog import load_catalog, CATALOG_FIELD_ORDER, DECISIONS_DIR

    systems = load_catalog()
    if slug not in systems:
        console.print(f"[red]System '{slug}' saknas i catalog.yaml[/red]")
        sys.exit(1)

    entry = systems[slug]
    decision_path = DECISIONS_DIR / f"{slug}.md"
    decision = decision_path.read_text(encoding="utf-8").strip() if decision_path.exists() else None

    # Behåll kanonisk fältordning för stabil output.
    fields = {f: entry[f] for f in CATALOG_FIELD_ORDER if f in entry}
    for k, v in entry.items():  # ev. okända fält sist
        fields.setdefault(k, v)

    return {"slug": slug, "fields": fields, "decision": decision}


def _render_node_markdown(payload: dict) -> str:
    """Render an export payload as a structured decision brief (Markdown)."""
    f = payload["fields"]
    lines = [f"# {f.get('title', payload['slug'])}", ""]
    if f.get("summary"):
        lines += [f["summary"].strip(), ""]

    lines += ["## Structure", ""]
    for key, label in (
        ("type", "Type"), ("domain", "Domain"), ("entity_type", "Entity type"),
        ("part_of", "Part of"), ("owner_agent", "Owner agent"), ("url_repo", "Repo"),
    ):
        if f.get(key):
            lines.append(f"- **{label}:** {f[key]}")
    for key, label in (("depends_on", "Depends on"), ("feeds", "Feeds")):
        vals = f.get(key) or []
        if vals:
            lines.append(f"- **{label}:** {', '.join(vals)}")
    lines.append("")

    lines += ["## Decision", ""]
    lines.append(payload["decision"] or "_No decision recorded (decisions/%s.md missing)._" % payload["slug"])
    lines.append("")
    return "\n".join(lines)


def cmd_export_node(args: argparse.Namespace) -> None:
    """Export ONE node as a decision brief — Markdown (default) or JSON.

    Core command: pure local read of catalog.yaml + decisions/<slug>.md.
    `--with-llm` is a reserved hook for Lab/Agency enrichment (e.g. an agent
    that turns this brief into a report or course module); not implemented in
    Core v1 — see lab/cns_lab.py.
    """
    if getattr(args, "with_llm", False):
        console.print(
            "[yellow]--with-llm is a reserved Lab/Agency hook and is not "
            "implemented in Core v1.[/yellow] Run the plain export and enrich it "
            "via the Lab layer (lab/). Continuing with the plain export below.\n"
        )

    payload = _node_export_payload(args.slug)
    if getattr(args, "format", "md") == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(_render_node_markdown(payload))


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
    """PENSIONERAD (teardown #11) — bevakade borttagna nodes/<slug>/node.md."""
    console.print("[yellow]cns watch är pensionerad (teardown #11): node.md-filerna revs, "
                  "det finns inget att bevaka. Sanningen bor i catalog.yaml.[/yellow]")


def cmd_cookbook(args: argparse.Namespace) -> None:
    """Generate/refresh a product's living build cookbook (AI-maintained per product)."""
    from scripts.cookbook import run_cookbook
    res = run_cookbook(args.domain, dry_run=args.dry_run)
    if args.dry_run:
        print(res["prompt"])
    else:
        print(f"Cookbook for {res['domain']} regenerated: {res['steps']} steps ({res['generated_at']}).")


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
    """PENSIONERAD (teardown #11) — skapade döda nodes/<slug>/-mappar."""
    console.print("[yellow]cns scaffold är pensionerad (teardown #11): nodes/<slug>/-mapparna revs. "
                  "Nya system bor i catalog.yaml (cns new <slug>) + decisions/.[/yellow]")


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
# Agentur-lagret — fryst 2026-07-12 (lab/frozen/)
# ---------------------------------------------------------------------------

def _frozen(command: str) -> None:
    """Avvisa ett kommando vars lager är fryst. Ett tydligt nej slår ett ImportError."""
    console.print(
        f"[yellow]'{command}' tillhör agentur-lagret, som är fryst sedan 2026-07-12.[/yellow]\n"
        "Koden ligger kvar i [cyan]lab/frozen/[/cyan] — se [cyan]lab/frozen/FROZEN.md[/cyan] "
        "för varför den frystes och vad som krävs för att väcka den."
    )
    sys.exit(2)


def cmd_tui(args: argparse.Namespace) -> None:
    """Fryst: den interaktiva terminal-överblicken (Textual)."""
    _frozen("cns tui")


def cmd_triage(args: argparse.Namespace) -> None:
    """Gruppera den öppna idé-inkorgen i åtgärdbara hinkar (#39, Control Tower)."""
    import json as _json
    import sys as _sys

    from scripts.idea_inbox import list_ideas
    from scripts.triage import group_ideas, render_triage

    if hasattr(_sys.stdout, "reconfigure"):
        _sys.stdout.reconfigure(encoding="utf-8")  # Windows-konsol klarar inte å-ä-ö/emoji
    grouping = group_ideas(list_ideas(status="open"))
    if getattr(args, "json", False):
        print(_json.dumps(grouping, ensure_ascii=False, indent=2))
    else:
        print(render_triage(grouping))


def cmd_derive(args: argparse.Namespace) -> None:
    """Härled nodkatalogen ur verkligheten; diffa eller bygg den sammanslagna kartan."""
    from scripts import derive_catalog as dc

    derived = dc.derive_from_disk()
    if args.diff:
        report = dc.diff_against_catalog(derived, dc.load_current_catalog())
        print(report.as_text())
        return
    if args.verify:
        print(dc.render_verify(dc.verify_from_disk()))
        return
    if args.apply:
        # Säkra annoteringslagret (engångs ur catalog.yaml om det saknas).
        annotations = dc.load_annotations()
        if not annotations:
            annotations = dc.build_annotations_from_catalog(dc.load_current_catalog())
            ann_path = dc.write_annotations(annotations)
            print(f"Skapade annoteringslager ({len(annotations)} noder) → {ann_path}")
        merged = dc.merge(derived, annotations)
        path = dc.write_merged(merged)
        print(f"Sammanslagen SYSTEM-karta: {len(merged)} noder "
              f"({len(derived)} härledda ur verkligheten, {len(annotations)} annoterade) → {path}")
        print("Agenter är en egen axel (ej noder här). Konsumenterna läser fortfarande catalog.yaml.")
        return
    path = dc.write_derived(derived)
    print(f"Härledde {len(derived)} noder → {path}")
    print("Kör 'cns derive --diff' för diff, 'cns derive --apply' för sammanslagen karta.")


def cmd_mcp_servers(_args: argparse.Namespace) -> None:
    """Fryst: MCP-routern för agenturens lokala pass."""
    _frozen("cns mcp-servers")


def cmd_agent_tools(args: argparse.Namespace) -> None:
    """Fryst: en rolls härledda effektiva verktyg (C1)."""
    _frozen("cns agent-tools")


def cmd_status(args: argparse.Namespace) -> None:
    """Fryst: berodde på scripts.tui.viewmodel, som aldrig har funnits i repot."""
    _frozen("cns status")


def cmd_health(args: argparse.Namespace) -> None:
    """Härledd hälso-scorecard för en nod (samma härledning som /api/nodes)."""
    from scripts.health import health_for_node

    sc = health_for_node(args.slug)
    if getattr(args, "json", False):
        print(json.dumps(sc, ensure_ascii=False, indent=2, default=str))
        return
    colors = {"healthy": "green", "attention": "yellow", "degraded": "red", "unknown": "dim"}
    lvl = sc.get("level", "unknown")
    console.print(f"[bold]{args.slug}[/bold] — [{colors.get(lvl, 'dim')}]{lvl}[/{colors.get(lvl, 'dim')}]")
    for ch in sc.get("checks", []):
        cc = colors.get(ch.get("level"), "dim")
        console.print(f"  [{cc}]{ch.get('level')}[/{cc}]  {ch.get('name')}: {ch.get('feedback', '')}")


def _github_guard() -> bool:
    """True om GitHub-credentials är satta; annars skriv en vänlig pekare och returnera False."""
    if os.getenv("GITHUB_REPO") and os.getenv("CNS_GITHUB_TOKEN"):
        return True
    console.print("[yellow]GitHub-credentials saknas[/yellow] — sätt [bold]GITHUB_REPO[/bold] + [bold]CNS_GITHUB_TOKEN[/bold] (User-env) och försök igen.")
    return False


def cmd_pr_list(args: argparse.Namespace) -> None:
    if not _github_guard():
        return
    from scripts import prs_client

    try:
        prs = prs_client.list_prs(state=getattr(args, "state", "open"))
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Kunde inte hämta PR:er:[/red] {exc}")
        return
    if getattr(args, "json", False):
        print(json.dumps(prs, ensure_ascii=False, indent=2, default=str))
        return
    if not prs:
        console.print("[dim]inga PR:er[/dim]")
        return
    for p in prs:
        tag = "[yellow]utkast[/yellow]" if p.get("draft") else "[green]klar[/green]"
        console.print(
            f"  {tag}  #{p.get('number')} {(p.get('title') or '')[:54]}  "
            f"[dim]{p.get('author', '')} · {p.get('head', '')}[/dim]"
        )


def cmd_pr_merge(args: argparse.Namespace) -> None:
    if not _github_guard():
        return
    from scripts import prs_client

    try:
        prs_client.merge_pr(args.number)
        console.print(f"[green]✅ Mergade PR #{args.number}[/green]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Merge misslyckades:[/red] {exc}")


def cmd_pr_close(args: argparse.Namespace) -> None:
    if not _github_guard():
        return
    from scripts import prs_client

    try:
        prs_client.close_pr(args.number)
        console.print(f"[bold]🗙 Stängde PR #{args.number}[/bold]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Close misslyckades:[/red] {exc}")


def cmd_dispatch(args: argparse.Namespace) -> None:
    """Fryst: dispatch-loopen (agenturens puls)."""
    _frozen("cns dispatch")


def cmd_agent_ask(args: argparse.Namespace) -> None:
    """Fryst: agent-host (lokala Claude-pass)."""
    _frozen("cns agent-ask")


def cmd_skill_export(args: argparse.Namespace) -> None:
    """Skriv (eller verifiera) skill-exporten. Vaulten är källan; .claude/skills/ är härlett."""
    from scripts import skill_export

    sys.exit(skill_export.main(["--check"] if getattr(args, "check", False) else []))


def cmd_memory_export(args: argparse.Namespace) -> None:
    """Vaulten äger minnet; ~/.claude/…/memory/ är härlett.

    Minnena styr hur Claude arbetar och läses vid varje sessionsstart. Låg de bara i ~/.claude/ var
    de osynliga för Rikard — och ett minne han inte kan se kan vara fel i veckor. Det hände
    2026-07-13. Nu kan han läsa och rätta dem.
    """
    from scripts import memory_export

    sys.exit(memory_export.main(["--check"] if getattr(args, "check", False) else []))


def cmd_skill_usage(args: argparse.Namespace) -> None:
    """Avfyras skillsen faktiskt? Läser Claude Code-transkripten. Deterministiskt → kod, ej skill."""
    from scripts import skill_usage

    sys.exit(skill_usage.main(["--json"] if getattr(args, "json", False) else []))


def cmd_selftest(args: argparse.Namespace) -> None:
    """Förtroende-loop: kör varje kärn-förmåga → grönt/rött. Default = rena checkar (ingen mutation);
    --live = läs-only-pingar mot GitHub/LLM-seamen (bevisar de osäkra lagren)."""
    results: list[tuple[str, bool, str]] = []

    def check(name: str, fn) -> None:
        try:
            results.append((name, True, str(fn() or "")[:70]))
        except Exception as exc:  # noqa: BLE001 — selftest fångar ALLT med flit
            results.append((name, False, f"{type(exc).__name__}: {exc}"[:90]))

    def _catalog():
        return f"{len(read_all_nodes())} noder"

    def _validate():
        from scripts.validator import validate_catalog

        errors, warnings = validate_catalog()
        if errors:
            raise ValueError(f"{len(errors)} fel: {errors[0]}")
        return f"{len(warnings)} varningar"

    def _orientering():
        # Bevisar samtidigt att cockpit-seamet degraderar utan agentur-lagret (fryst 2026-07-12):
        # command_center_state() får inte kasta bara för att scripts.recommend saknas.
        from scripts.command_center import command_center_state

        state = command_center_state()
        return f"{len(state.get('missions', []))} missions, {len(state.get('orders', []))} orders"

    def _triage():
        from scripts.idea_inbox import list_ideas
        from scripts.triage import group_ideas

        group_ideas(list_ideas(status="open"))
        return "ok"

    def _sessions():
        from scripts import session_store

        return f"{len(session_store.list_sessions())} sessioner"

    def _health():
        from scripts.health import health_for_node

        nodes = read_all_nodes()
        if not nodes:
            return "inga noder"
        slug = nodes[0][0].get("slug") or "?"
        return f"{slug}: {health_for_node(slug).get('level')}"

    def _node_seam_gated():
        # Den rivna node.md-disk-modellen (teardown #11) ska resa fel, ej degradera tyst.
        from scripts.md_parser import write_node, list_node_files, scaffold_node_dirs
        for fn in (lambda: write_node("x", {}, {}),
                   lambda: list_node_files(),
                   lambda: scaffold_node_dirs("x")):
            try:
                fn()
            except NotImplementedError:
                continue
            raise AssertionError("död node.md-seam degraderar tyst — grinden saknas")
        return "grindad ✓"

    check("katalog-läs (read_all_nodes)", _catalog)
    check("node.md-dödseam grindad (teardown #11)", _node_seam_gated)
    check("katalog-validering (validate_catalog)", _validate)
    check("orientering (command_center)", _orientering)
    check("triage (group_ideas)", _triage)
    check("sessioner (session_store)", _sessions)
    check("hälsa (health_for_node)", _health)

    if getattr(args, "live", False):
        def _gh_prs():
            from scripts import prs_client

            return f"{len(prs_client.list_prs(state='open'))} öppna PR:er"

        def _gh_issues():
            from scripts import issues_client

            return f"{len(issues_client.list_issues(state='open'))} öppna issues"

        check("GitHub: PR-läs (live)", _gh_prs)
        check("GitHub: issue-läs (live)", _gh_issues)

    if getattr(args, "json", False):
        print(json.dumps([{"check": n, "ok": ok, "detail": d} for n, ok, d in results], ensure_ascii=False, indent=2))
    else:
        for n, ok, d in results:
            mark = "[green]✓[/green]" if ok else "[red]✗[/red]"
            console.print(f"  {mark} {n}  [dim]{d}[/dim]")
        n_ok = sum(1 for _, ok, _ in results if ok)
        color = "green" if n_ok == len(results) else "red"
        console.print(f"\n[bold {color}]{n_ok}/{len(results)} gröna[/bold {color}]")
    sys.exit(0 if all(ok for _, ok, _ in results) else 1)


# ---------------------------------------------------------------------------
# CLI setup
# ---------------------------------------------------------------------------

def register_core(subparsers) -> None:
    """Register the three CNS Core commands: validate, new, export.

    Core is the daily minimal flow — model nodes in catalog.yaml, write decision
    prose in decisions/, validate, and export a brief. No agency, no network.
    """
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

    # cns export <slug> [--format md|json] [--with-llm]
    sp_export = subparsers.add_parser("export", help="Export a node's decision brief (Markdown/JSON)")
    sp_export.add_argument("slug", help="System slug")
    sp_export.add_argument("--format", choices=["md", "json"], default="md", help="Output format (default: md)")
    sp_export.add_argument(
        "--with-llm", action="store_true", dest="with_llm",
        help="Reserved hook: Lab/Agency enrichment (not implemented in Core v1)",
    )
    sp_export.set_defaults(func=cmd_export_node)


def _load_env() -> None:
    # Plocka upp GITHUB_REPO/CNS_GITHUB_TOKEN m.m. ur den otrackade .env (samma flöde som
    # scripts/dispatch.py) — Windows fryser processens miljöblock vid start, så User-env satt
    # efteråt syns inte i $env; .env gör credentials synliga för ALLA cns-kommandon ändå.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass


def main() -> None:
    """CNS Core entrypoint — exposes only validate / new / export.

    Lab/Agency commands (tui, dispatch, sessions, …) live behind a separate
    entrypoint: `python lab/cns_lab.py`.
    """
    _load_env()
    parser = argparse.ArgumentParser(
        prog="cns",
        description="CNS Core — local-first node modelling (validate / new / export)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Core commands")
    register_core(subparsers)

    args = parser.parse_args()
    if not args.command or not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)


def register_lab(subparsers) -> None:
    """Register Lab/Agency commands (advanced/R&D — invoked via lab/cns_lab.py)."""
    # cns venture {status|checklist|list} — fas, grindar, checklistor.
    # Lazy import: Core får aldrig bero på Lab (namespace-splitten).
    from lab.scripts import venture_cli
    venture_cli.register(subparsers)

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

    # cns export-xlsx / export-json — Lab: dashboard/portfolio exports
    sp_xlsx = subparsers.add_parser("export-xlsx", help="[Lab] Export all nodes to Excel")
    sp_xlsx.set_defaults(func=cmd_export_xlsx)

    sp_json = subparsers.add_parser("export-json", help="[Lab] Export nodes.json for the dashboard")
    sp_json.add_argument(
        "--output", "-o", default=None,
        help="Override output path (default: exports/nodes.json)",
    )
    sp_json.set_defaults(func=cmd_export_json)

    # cns derive — härled katalogen ur verkligheten + diffa (Del A)
    sp_derive = subparsers.add_parser(
        "derive", help="Härled nodkatalogen ur verkligheten (agents.json, .mcp.json) + diffa"
    )
    sp_derive.add_argument(
        "--diff", action="store_true",
        help="Visa diff mot catalog.yaml i stället för att skriva catalog.derived.yaml",
    )
    sp_derive.add_argument(
        "--apply", action="store_true",
        help="Bygg sammanslagen karta (härlett + annoterat) → catalog.merged.yaml (flippar inte)",
    )
    sp_derive.add_argument(
        "--verify", action="store_true",
        help="Klassa katalognoder mot repo-verkligheten (true/stale/aspirational/grouping)",
    )
    sp_derive.set_defaults(func=cmd_derive)

    # cns mcp-servers — lista MCP-routerns servrar + konfig-status
    sp_mcp = subparsers.add_parser(
        "mcp-servers", help="Lista MCP-servrarna agenturen kan nå + om de är konfigurerade"
    )
    sp_mcp.set_defaults(func=cmd_mcp_servers)

    # cns agent-tools <roll> — visa en rolls härledda effektiva verktyg (C1)
    sp_atools = subparsers.add_parser(
        "agent-tools", help="Visa en rolls härledda effektiva verktyg (matris + override → lokala namn)"
    )
    sp_atools.add_argument("role", help="Roll-slug (t.ex. backend-utvecklare)")
    sp_atools.set_defaults(func=cmd_agent_tools)

    # cns deploy {connect|status|deploy} — drift-ekrar (#78). Läser nodens integrations.deploy.
    sp_deploy = subparsers.add_parser("deploy", help="Drift-adaptrar (Vercel): connect/status/deploy")
    deploy_sub = sp_deploy.add_subparsers(dest="deploy_cmd")
    sp_dc = deploy_sub.add_parser("connect", help="Verifiera Vercel-token (read-only)")
    sp_dc.set_defaults(func=cmd_deploy_connect)
    sp_ds = deploy_sub.add_parser("status", help="Senaste deployment-status för en nod (read-only)")
    sp_ds.add_argument("slug", help="System-slug (måste ha vercel i integrations.deploy)")
    sp_ds.set_defaults(func=cmd_deploy_status)
    sp_dd = deploy_sub.add_parser("deploy", help="Trigga en deployment (MUTATING — kräver --yes)")
    sp_dd.add_argument("slug", help="System-slug")
    sp_dd.add_argument("--ref", default="main", help="Git-ref att deploya (default main)")
    sp_dd.add_argument("--yes", action="store_true", help="Bekräfta den muterande deployen")
    sp_dd.set_defaults(func=cmd_deploy_deploy)

    # cns project sync  (board-synk: issues → org-Projektet "Backlog", epic #13)
    sp_project = subparsers.add_parser("project", help="GitHub Projects-synk (board)")
    project_sub = sp_project.add_subparsers(dest="project_cmd")
    sp_psync = project_sub.add_parser("sync", help="Synka issues → org-Projektet 'Backlog'")
    sp_psync.add_argument("--dry-run", action="store_true", help="Visa utan att skriva")
    sp_psync.set_defaults(func=cmd_project_sync)

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

    # cns cookbook — AI-maintained per-product build guide
    sp_cookbook = subparsers.add_parser(
        "cookbook",
        help="Generate/refresh a product's living build cookbook (AI)",
    )
    sp_cookbook.add_argument("domain", help="Product domain (juvahem/bkfinans/orgkomp/crusade/cortxt)")
    sp_cookbook.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Build context + prompt without calling the model (free)",
    )
    sp_cookbook.set_defaults(func=cmd_cookbook)

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

    sp_triage = subparsers.add_parser("triage", help="Gruppera öppna idéer i åtgärdbara hinkar (#39)")
    sp_triage.add_argument("--json", action="store_true", help="Skriv grupperingen som JSON")
    sp_triage.set_defaults(func=cmd_triage)

    # cns skill-export — vaulten äger skills, .claude/skills/ är en härledd artefakt
    sp_skx = subparsers.add_parser(
        "skill-export", help="Exportera Studio/Skills/ (vaulten) → .claude/skills/. En riktning."
    )
    sp_skx.add_argument("--check", action="store_true",
                        help="Falla om exporten drivit isär från vaulten (CI-grinden)")
    sp_skx.set_defaults(func=cmd_skill_export)

    # cns memory-export — vaulten äger minnena, ~/.claude/…/memory/ är en härledd artefakt.
    # Du kan inte rätta det du inte kan se.
    sp_mem = subparsers.add_parser(
        "memory-export", help="Exportera Studio/Memory/ (vaulten) → ~/.claude/…/memory/. En riktning."
    )
    sp_mem.add_argument("--check", action="store_true",
                        help="Falla om exporten drivit isär från vaulten")
    sp_mem.set_defaults(func=cmd_memory_export)

    # cns skill-usage — svaret på "används skillsen?". Utan mätning fyller gissningar tomrummet.
    sp_sku = subparsers.add_parser(
        "skill-usage", help="Vilka skills avfyras faktiskt (och vilka aldrig)? Ur transkripten."
    )
    sp_sku.add_argument("--json", action="store_true")
    sp_sku.set_defaults(func=cmd_skill_usage)

    # cns status — orientering/arbetslista headless
    sp_status = subparsers.add_parser("status", help="Orientering: arbetslista + statusräkning (headless)")
    sp_status.add_argument("--json", action="store_true", help="Skriv command_center_state som JSON")
    sp_status.set_defaults(func=cmd_status)

    # cns health <slug>
    sp_health = subparsers.add_parser("health", help="Härledd hälso-scorecard för en nod")
    sp_health.add_argument("slug", help="Nod-slug")
    sp_health.add_argument("--json", action="store_true")
    sp_health.set_defaults(func=cmd_health)

    # cns pr {list|merge|close}
    sp_pr = subparsers.add_parser("pr", help="Pull requests: list/merge/close (review headless)")
    pr_sub = sp_pr.add_subparsers(dest="pr_cmd")
    sp_pr_list = pr_sub.add_parser("list", help="Lista PR:er")
    sp_pr_list.add_argument("--state", default="open", help="open|closed|all (default open)")
    sp_pr_list.add_argument("--json", action="store_true")
    sp_pr_list.set_defaults(func=cmd_pr_list)
    sp_pr_merge = pr_sub.add_parser("merge", help="Merga en PR")
    sp_pr_merge.add_argument("number", type=int, help="PR-nummer")
    sp_pr_merge.set_defaults(func=cmd_pr_merge)
    sp_pr_close = pr_sub.add_parser("close", help="Stäng en PR")
    sp_pr_close.add_argument("number", type=int, help="PR-nummer")
    sp_pr_close.set_defaults(func=cmd_pr_close)

    # cns dispatch — kör ETT pass (read-first default)
    sp_dispatch = subparsers.add_parser("dispatch", help="Kör ETT dispatch-pass (read-first default)")
    sp_dispatch.add_argument("--write", action="store_true", help="Skriv-läge: worktree + draft-PR")
    sp_dispatch.add_argument("--autonomy", action="store_true", help="Self-merga lågrisk (kräver --write)")
    sp_dispatch.add_argument("--yes", action="store_true", help="Auto-ja på grindar")
    sp_dispatch.add_argument("--dry-run", action="store_true", dest="dry_run", help="Tvinga read-first (ignorera --write/--autonomy)")
    sp_dispatch.set_defaults(func=cmd_dispatch)

    # cns agent-ask <slug>
    sp_aa = subparsers.add_parser("agent-ask", help="Fråga Claude om en nod (agent-host, läs-först)")
    sp_aa.add_argument("slug", help="Nod-slug")
    sp_aa.add_argument("-q", "--question", default=None, help="Frågan (default: sammanfatta noden)")
    sp_aa.set_defaults(func=cmd_agent_ask)

    # cns selftest — förtroende-loop
    sp_self = subparsers.add_parser("selftest", help="Kör varje kärn-förmåga → grönt/rött")
    sp_self.add_argument("--live", action="store_true", help="Inkl. läs-only GitHub/LLM-pingar")
    sp_self.add_argument("--json", action="store_true")
    sp_self.set_defaults(func=cmd_selftest)


if __name__ == "__main__":
    main()
