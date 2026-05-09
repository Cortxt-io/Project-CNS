"""Interactive local editor for CNS project updates."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "project_schema.json"

# Fields offered in the interactive menu.
MENU_FIELDS = [
    ("status", "Status"),
    ("mvp_stage", "MVP Stage"),
    ("tags", "Tags"),
    ("cost_sek", "Cost (SEK)"),
    ("value_sek", "Value (SEK)"),
    ("primary_audience", "Primary Audience"),
    ("secondary_audience", "Secondary Audience"),
    ("notes_append", "Add Note"),
    ("risks", "Add Risk"),
    ("why_buy_not_build", "Why Buy Instead of Build?"),
]


def _load_enum(field_path: list[str]) -> list[str]:
    """Load allowed enum values from the JSON schema."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    node = schema
    for key in field_path:
        node = node.get("properties", {}).get(key, {})
    values = node.get("enum", [])
    return [v for v in values if v is not None]


def _select_fields(console: Console) -> list[str]:
    """Show numbered menu and return selected field keys."""
    console.print("\n[bold]Select fields to change:[/bold]")
    for i, (key, label) in enumerate(MENU_FIELDS, 1):
        console.print(f"  [cyan]{i:>2}[/cyan]. {label}")
    console.print()

    raw = Prompt.ask("Enter field numbers (comma-separated, e.g. 1,3,8)")
    selected = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(MENU_FIELDS):
                selected.append(MENU_FIELDS[idx][0])
    return selected


def _ask_status(meta: dict, console: Console) -> str:
    choices = _load_enum(["changes", "status"])
    current = meta.get("status", "idea")
    console.print(f"  Current status: [dim]{current}[/dim]")
    return Prompt.ask("  New status", choices=choices, default=current)


def _ask_mvp_stage(meta: dict, console: Console) -> str:
    choices = _load_enum(["changes", "mvp_stage"])
    current = meta.get("mvp_stage", "hypothesis")
    console.print(f"  Current MVP stage: [dim]{current}[/dim]")
    return Prompt.ask("  New MVP stage", choices=choices, default=current)


def _ask_tags(meta: dict, console: Console) -> list[str]:
    current = meta.get("tags", [])
    console.print(f"  Current tags: [dim]{', '.join(current) if current else '(none)'}[/dim]")
    raw = Prompt.ask("  Tags (comma-separated)")
    return [t.strip() for t in raw.split(",") if t.strip()]


def _ask_number(field_name: str, meta: dict, console: Console) -> int:
    current = meta.get(field_name, 0)
    console.print(f"  Current {field_name}: [dim]{current:,}[/dim]")
    return IntPrompt.ask(f"  New {field_name}", default=current)


def _ask_text(field_name: str, label: str, sections: dict, console: Console) -> str:
    # Try to show current value from Target Audience section
    audience = sections.get("Target Audience", "")
    marker = "Primary" if "primary" in field_name else "Secondary"
    current = ""
    for line in audience.splitlines():
        if marker in line:
            current = line.split(":", 1)[-1].strip().strip("*")
    if current:
        console.print(f"  Current {label}: [dim]{current}[/dim]")
    return Prompt.ask(f"  {label}")


def _ask_note(console: Console) -> str:
    return Prompt.ask("  Note to append")


def _ask_risk(console: Console) -> dict:
    categories = ["technical", "market", "legal", "ops", "competition"]
    console.print("  Risk categories: " + ", ".join(categories))
    category = Prompt.ask("  Risk category", choices=categories)
    description = Prompt.ask("  Risk description")
    score = IntPrompt.ask("  Risk score (1-5)", default=3)
    score = max(1, min(5, score))
    return {"category": category, "description": description, "score": score}


def _ask_why_buy(console: Console) -> list[str]:
    console.print('  Enter up to 3 items (start with "Saves...", "Eliminates...", or "Reduces risk of...")')
    items = []
    for i in range(3):
        item = Prompt.ask(f"  Item {i + 1} (or press Enter to finish)", default="")
        if not item:
            break
        items.append(item)
    return items


def run_local_edit(
    meta: dict[str, Any],
    sections: dict[str, str],
    console: Console,
) -> dict[str, Any] | None:
    """Run interactive local edit session.

    Returns a changes dict compatible with md_parser.apply_changes(),
    or None if the user selects no fields.
    """
    selected = _select_fields(console)
    if not selected:
        console.print("[yellow]No fields selected.[/yellow]")
        return None

    changes: dict[str, Any] = {}

    for field in selected:
        console.print()
        if field == "status":
            changes["status"] = _ask_status(meta, console)
        elif field == "mvp_stage":
            changes["mvp_stage"] = _ask_mvp_stage(meta, console)
        elif field == "tags":
            changes["tags"] = _ask_tags(meta, console)
        elif field == "cost_sek":
            changes["cost_sek"] = _ask_number("cost_sek", meta, console)
        elif field == "value_sek":
            changes["value_sek"] = _ask_number("value_sek", meta, console)
        elif field == "primary_audience":
            changes["primary_audience"] = _ask_text("primary_audience", "Primary Audience", sections, console)
        elif field == "secondary_audience":
            changes["secondary_audience"] = _ask_text("secondary_audience", "Secondary Audience", sections, console)
        elif field == "notes_append":
            changes["notes_append"] = _ask_note(console)
        elif field == "risks":
            changes["risks"] = [_ask_risk(console)]
        elif field == "why_buy_not_build":
            items = _ask_why_buy(console)
            if items:
                changes["why_buy_not_build"] = items

    # Auto-compute ROI if cost or value changed
    cost = changes.get("cost_sek", meta.get("cost_sek", 0))
    value = changes.get("value_sek", meta.get("value_sek", 0))
    if "cost_sek" in changes or "value_sek" in changes:
        if cost > 0:
            changes["roi_percent"] = round((value - cost) / cost * 100)
        else:
            changes["roi_percent"] = 0

    changes["updated_at"] = date.today().isoformat()
    return changes


# ---------------------------------------------------------------------------
# New-project interview
# ---------------------------------------------------------------------------


def run_new_project_interview(
    meta: dict[str, Any],
    sections: dict[str, str],
    console: Console,
) -> tuple[dict[str, Any], dict[str, str]] | None:
    """Run interactive interview for a new project.

    Prompts for essential fields (title, problem, solution, audience, tags).
    All prompts are skippable by pressing Enter.

    Returns (meta, sections) with user input applied, or None if the user
    cancels at the confirmation step or presses Ctrl+C.
    """
    try:
        console.print()
        console.print(f"[bold]Setting up project:[/bold] [cyan]{meta['slug']}[/cyan]")
        console.print("[dim]Press Enter to skip any field.[/dim]\n")

        # --- Title ---
        title = Prompt.ask("  Title", default=meta["title"])
        if title.strip():
            meta["title"] = title.strip()

        # --- Problem ---
        problem = Prompt.ask("  What problem does this solve?", default="")
        if problem.strip():
            sections["Problem"] = problem.strip()

        # --- Solution ---
        solution = Prompt.ask("  Solution in one sentence", default="")
        if solution.strip():
            sections["Solution"] = solution.strip()

        # --- Target Audience ---
        audience = Prompt.ask("  Primary audience", default="")
        if audience.strip():
            sections["Target Audience"] = f"**Primary:** {audience.strip()}"

        # --- Tags ---
        tags_raw = Prompt.ask("  Tags (comma-separated)", default="")
        if tags_raw.strip():
            meta["tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()]

        # --- Summary panel ---
        console.print()
        summary = _build_new_project_summary(meta, sections)
        console.print(Panel(
            summary,
            title=f"[bold cyan]New Project: {meta['slug']}[/bold cyan]",
            border_style="blue",
        ))

        # --- Confirmation ---
        if not Confirm.ask("  Create project with these details?", default=True):
            console.print("[yellow]  Cancelled — project will use blank template.[/yellow]")
            return None

        return meta, sections

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]  Interrupted — project will use blank template.[/yellow]")
        return None


def _build_new_project_summary(
    meta: dict[str, Any],
    sections: dict[str, str],
) -> str:
    """Format a summary string for the new-project confirmation panel."""
    dim_empty = "[dim](empty)[/dim]"

    lines = [
        f"  [bold]Title:[/bold]    {meta.get('title', dim_empty)}",
        f"  [bold]Status:[/bold]   {meta.get('status', 'idea')}",
        f"  [bold]Tags:[/bold]     {', '.join(meta.get('tags', [])) or dim_empty}",
        "",
        f"  [bold]Problem:[/bold]  {sections.get('Problem', '').strip() or dim_empty}",
        f"  [bold]Solution:[/bold] {sections.get('Solution', '').strip() or dim_empty}",
        f"  [bold]Audience:[/bold] {sections.get('Target Audience', '').strip() or dim_empty}",
    ]
    return "\n".join(lines)
