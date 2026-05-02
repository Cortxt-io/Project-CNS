"""Connector mode — generate edit briefs for external LLM workflows."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from scripts.md_parser import project_dir, read_project

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "system_prompt.md"

CHANGE_TYPES = [
    "status_update",
    "content_rewrite",
    "risk_update",
    "cost_revision",
    "general",
]

DETAIL_LEVELS = ["short", "detailed", "patch"]

# Mapping from change type to the fields most likely affected.
_FIELD_CHECKLIST: dict[str, list[str]] = {
    "status_update": ["status", "mvp_stage", "updated_at"],
    "content_rewrite": ["problem", "solution", "target_audience", "mvp_steps", "updated_at"],
    "risk_update": ["risks", "notes_append", "updated_at"],
    "cost_revision": ["cost_sek", "value_sek", "roi_percent", "updated_at"],
    "general": ["(any fields as needed)", "updated_at"],
}


def _build_summary(meta: dict, sections: dict) -> str:
    """Build a short summary of the current project state."""
    lines = [
        f"Title:     {meta.get('title', '?')}",
        f"Slug:      {meta.get('slug', '?')}",
        f"Status:    {meta.get('status', '?')}",
        f"MVP Stage: {meta.get('mvp_stage', '?')}",
        f"Cost SEK:  {meta.get('cost_sek', 0):,}",
        f"Value SEK: {meta.get('value_sek', 0):,}",
        f"ROI:       {meta.get('roi_percent', 0)}%",
        f"Updated:   {meta.get('updated', '?')}",
    ]
    # Include non-empty sections
    filled = [h for h, body in sections.items() if body.strip()]
    if filled:
        lines.append(f"Sections with content: {', '.join(filled)}")
    else:
        lines.append("Sections with content: (none)")
    return "\n".join(lines)


def _build_brief(
    meta: dict,
    sections: dict,
    description: str,
    change_type: str,
    detail: str,
) -> str:
    """Assemble the full edit brief text."""
    summary = _build_summary(meta, sections)
    checklist = _FIELD_CHECKLIST.get(change_type, _FIELD_CHECKLIST["general"])
    checklist_text = "\n".join(f"  - {f}" for f in checklist)

    system_prompt = ""
    if SYSTEM_PROMPT_PATH.exists():
        system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()

    slug = meta.get("slug", "unknown")

    if detail == "short":
        instruction = (
            f'Using the synced file for {slug} as the source of truth, '
            f'{description} '
            f'Return the updated frontmatter and modified sections only.'
        )
    elif detail == "patch":
        instruction = (
            f'Using the synced file for {slug} as the source of truth, '
            f'apply these changes:\n\n{description}\n\n'
            f'Return a JSON object matching the project schema with only the changed fields set '
            f'(all others null).'
        )
    else:  # detailed
        instruction = (
            f'Using the synced file for {slug} as the source of truth, update the project so that:\n\n'
            f'{description}\n\n'
            f'Context: current status is "{meta.get("status", "?")}", '
            f'MVP stage is "{meta.get("mvp_stage", "?")}", '
            f'cost is {meta.get("cost_sek", 0):,} SEK, '
            f'value is {meta.get("value_sek", 0):,} SEK.\n\n'
            f'Return the updated frontmatter and the modified sections only.'
        )

    parts = [
        "--- CURRENT PROJECT SUMMARY ---",
        summary,
        "",
        "--- REQUESTED CHANGES ---",
        description,
        "",
        "--- FIELDS TO UPDATE ---",
        checklist_text,
        "",
        "--- PROMPT FOR PERPLEXITY ---",
        instruction,
    ]

    if system_prompt:
        parts.extend([
            "",
            "--- SYSTEM PROMPT (for reference) ---",
            system_prompt,
        ])

    return "\n".join(parts)


def generate_edit_brief(slug: str, console: Console) -> None:
    """Interactive interview + edit brief generation for connector mode."""
    try:
        meta, sections, _ = read_project(slug)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return

    console.print(f"\n[bold]Preparing edit brief for [cyan]{slug}[/cyan][/bold]\n")

    description = Prompt.ask("What do you want to change?")
    change_type = Prompt.ask(
        "Type of change",
        choices=CHANGE_TYPES,
        default="general",
    )
    detail = Prompt.ask(
        "Prompt detail level",
        choices=DETAIL_LEVELS,
        default="detailed",
    )

    brief = _build_brief(meta, sections, description, change_type, detail)

    # Write brief to project exports folder
    exports_dir = project_dir(slug) / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    brief_path = exports_dir / "ai-brief.md"
    brief_path.write_text(brief + "\n", encoding="utf-8")

    console.print()
    console.print(Panel(
        brief,
        title="[bold]Edit Brief — copy below[/bold]",
        border_style="green",
        padding=(1, 2),
    ))
    console.print(f"\n[green]Brief saved to {brief_path}[/green]")
    console.print("[dim]Paste the prompt section into Perplexity chat or Space.[/dim]")
