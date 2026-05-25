"""cns-devlog: AI-powered daily digest from cns-devwatch output.

Reads exports/devwatch_YYYY-MM-DD.json, calls OpenAI for a Swedish summary,
and renders a self-contained static HTML page.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPORTS_DIR = REPO_ROOT / "exports"

console = Console()

# ---------------------------------------------------------------------------
# OpenAI config
# ---------------------------------------------------------------------------

OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "Du är en erfaren produktchef som briefar sig själv. "
    "Praktisk, direkt, ingen fluff. Svara på svenska."
)

# ---------------------------------------------------------------------------
# API key
# ---------------------------------------------------------------------------


def _get_api_key() -> str:
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or key == "your_key_here":
        raise RuntimeError(
            "OpenAI API key not configured. "
            "Add OPENAI_API_KEY to .env to use cns devlog."
        )
    return key


# ---------------------------------------------------------------------------
# DevWatch input helpers
# ---------------------------------------------------------------------------


def _resolve_devwatch_path(today_str: str) -> Path:
    """Resolve the devwatch JSON path for today.

    If exports/devwatch_{today}.json exists, return it directly.
    Otherwise, run devwatch to produce a fresh file and return that path.
    """
    today_file = EXPORTS_DIR / f"devwatch_{today_str}.json"

    if today_file.exists():
        console.print(f"[dim]Using existing devwatch: {today_file.name}[/dim]")
        return today_file

    console.print("[cyan]No devwatch file for today — running devwatch first.[/cyan]")
    from scripts.devwatch import run_devwatch

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    devwatch_path = run_devwatch()

    console.print(f"[dim]Devwatch produced: {devwatch_path.name}[/dim]")
    return devwatch_path


def _load_devwatch(path: Path) -> dict:
    """Load and lightly validate a devwatch JSON file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {path}: {exc}")

    if "meta" not in data:
        raise RuntimeError(f"Missing 'meta' key in {path}")
    if "events" not in data:
        raise RuntimeError(f"Missing 'events' key in {path}")
    return data


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def _build_prompt(events: list[dict]) -> str:
    """Build the user prompt from ChangeEvents."""
    parts: list[str] = [
        "Här är en sammanfattning av ändringar i min projektportfölj:\n"
    ]

    for event in events:
        meta = event.get("meta", {})
        slug = meta.get("slug", "unknown")
        title = meta.get("project_title", slug)
        changed_fields = meta.get("changed_fields", [])
        changed_files = meta.get("changed_files", [])
        raw_content = event.get("rawContent", "")

        parts.append("---")
        parts.append(f"Projekt: {title} (slug: {slug})")
        parts.append(
            f"Ändrade fält: {', '.join(changed_fields) if changed_fields else 'Inga'}"
        )

        if changed_files:
            parts.append("Ändrade filer/sektioner:")
            for cf in changed_files:
                file_name = cf.get("file", "?")
                sections = cf.get("sections", [])
                if sections:
                    parts.append(f"- {file_name}: {', '.join(sections)}")
                else:
                    parts.append(f"- {file_name}")
        else:
            parts.append("Ändrade filer: Inga")

        excerpt = raw_content[:400].strip()
        if len(raw_content) > 400:
            excerpt += "..."
        parts.append(f"Excerpt:\n{excerpt}")
        parts.append("")

    parts.append("---\n")
    parts.append(
        "Svara med en kort analys (max ~400 ord) som innehåller:\n"
        "1. Vad hände igår i portföljen – per projekt, konkret.\n"
        "2. Vad är kvar per projekt baserat på MVP Steps och senaste ändringar.\n"
        "3. Vad borde vara nästa steg för hela portföljen idag.\n\n"
        "Formatera svaret som ren text med rubriker och punktlistor. "
        "Ingen markdown-kodblock."
    )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# OpenAI caller
# ---------------------------------------------------------------------------


def _call_openai(system_prompt: str, user_prompt: str) -> str:
    """Call OpenAI chat completions and return the text content."""
    api_key = _get_api_key()

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 800,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            OPENAI_ENDPOINT, json=payload, headers=headers, timeout=60
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc}")

    if resp.status_code != 200:
        raise RuntimeError(
            f"OpenAI API error {resp.status_code}: {resp.text}"
        )

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected OpenAI response structure: {exc}")

    content = content.strip()
    if not content:
        raise RuntimeError("OpenAI returned empty content.")

    return content


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _inline_format(text: str) -> str:
    """Apply inline formatting: **bold** → <strong>, escape rest."""
    # Split on **...** patterns, format bold segments, escape the rest
    parts: list[str] = []
    remaining = text
    while remaining:
        bold_match = re.search(r"\*\*(.+?)\*\*", remaining)
        if bold_match:
            before = remaining[:bold_match.start()]
            bold_text = bold_match.group(1)
            after = remaining[bold_match.end():]
            if before:
                parts.append(_escape_html(before))
            parts.append(f"<strong>{_escape_html(bold_text)}</strong>")
            remaining = after
        else:
            parts.append(_escape_html(remaining))
            break
    return "".join(parts)


def _text_to_html(text: str) -> str:
    """Convert plain text with simple conventions into HTML.

    Handles: ### / ## / # headings, - / numbered list items,
    **bold** inline, lines ending with : as sub-headings.
    """
    lines = text.splitlines()
    blocks: list[str] = []
    current_list: list[str] = []

    def _flush_list() -> None:
        nonlocal current_list
        if current_list:
            blocks.append("<ul>")
            for item in current_list:
                blocks.append(f"<li>{_inline_format(item)}</li>")
            blocks.append("</ul>")
            current_list = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            _flush_list()
            continue

        # Markdown-style headings: ### / ## / #
        if re.match(r"^#{1,3}\s", stripped):
            _flush_list()
            level = len(re.match(r"^#+", stripped).group())
            heading_text = re.sub(r"^#+\s+", "", stripped)
            tag = "h3" if level >= 3 else "h3" if level == 2 else "h2"
            blocks.append(f"<{tag}>{_inline_format(heading_text)}</{tag}>")
            continue

        # Bullet list items: - text
        if stripped.startswith("- "):
            current_list.append(stripped[2:])
            continue

        # Numbered list items: 1. text
        num_match = re.match(r"^\d+\.\s+(.+)$", stripped)
        if num_match:
            current_list.append(num_match.group(1))
            continue

        _flush_list()

        # Treat short lines ending with : as sub-headings
        if len(stripped) < 60 and stripped.endswith(":"):
            blocks.append(f"<h3>{_inline_format(stripped[:-1])}</h3>")
        else:
            blocks.append(f"<p>{_inline_format(stripped)}</p>")

    _flush_list()
    return "\n".join(blocks)


def _render_html(
    ai_digest: Optional[str],
    devwatch_data: dict,
    no_changes: bool,
) -> str:
    """Render a complete self-contained HTML page."""
    exported_at = devwatch_data.get("exported_at", "")
    source_run_id = devwatch_data.get("run_id", "")
    meta = devwatch_data.get("meta", {})
    event_count = meta.get("events_exported", 0)
    source_file = devwatch_data.get("_source_path", "devwatch.json")

    # Derive display date from exported_at or fallback to today
    try:
        dt = datetime.fromisoformat(exported_at.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    digest_html = ""
    if no_changes:
        digest_html = (
            '<div class="no-activity">'
            "<p>Ingen aktivitet i portföljen idag.</p>"
            "</div>"
        )
    elif ai_digest:
        digest_html = (
            '<section class="card">\n'
            '  <h2>Dagens sammanfattning</h2>\n'
            '  <div class="digest-content">\n'
            f"{_text_to_html(ai_digest)}\n"
            '  </div>\n'
            "</section>"
        )

    return f"""<!DOCTYPE html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CNS DevLog — {date_str}</title>
  <style>
    body {{
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background-color: #f8fafc;
      color: #0f172a;
      margin: 0;
      padding: 0;
      line-height: 1.6;
    }}
    main {{
      max-width: 768px;
      margin: 0 auto;
      padding: 48px 24px;
    }}
    header {{
      margin-bottom: 40px;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 24px;
    }}
    h1 {{
      font-size: 1.875rem;
      font-weight: 700;
      letter-spacing: -0.025em;
      margin: 0 0 8px 0;
      color: #0f172a;
    }}
    .subtitle {{
      font-size: 1.125rem;
      color: #475569;
      margin: 0;
    }}
    .meta {{
      margin-top: 16px;
      font-size: 0.875rem;
      color: #64748b;
    }}
    .meta span {{
      color: #334155;
      font-weight: 500;
    }}
    section.card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 24px;
      margin-bottom: 24px;
    }}
    h2 {{
      font-size: 1.25rem;
      font-weight: 600;
      margin: 0 0 16px 0;
      color: #0f172a;
    }}
    h3 {{
      font-size: 1rem;
      font-weight: 600;
      margin: 16px 0 8px 0;
      color: #334155;
    }}
    .digest-content p {{
      margin: 0 0 12px 0;
      color: #334155;
    }}
    .digest-content ul {{
      margin: 0 0 12px 0;
      padding-left: 20px;
    }}
    .digest-content li {{
      margin-bottom: 6px;
      color: #334155;
    }}
    .no-activity {{
      text-align: center;
      padding: 80px 24px;
      color: #64748b;
      font-size: 1.125rem;
    }}
    footer {{
      margin-top: 48px;
      padding-top: 24px;
      border-top: 1px solid #e2e8f0;
      text-align: center;
      font-size: 0.75rem;
      color: #94a3b8;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>CNS DevLog</h1>
      <p class="subtitle">{date_str}</p>
      <div class="meta">
        <p><span>Antal händelser:</span> {event_count}</p>
        <p><span>Källa:</span> {source_file} ({source_run_id})</p>
      </div>
    </header>

    {digest_html}

    <footer>
      <p>Genererad av cns-devlog &middot; {generated_at}</p>
    </footer>
  </main>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Rich display
# ---------------------------------------------------------------------------


def _print_summary(
    devwatch_data: dict,
    html_path: Path,
    dry_run: bool,
    no_changes: bool,
    event_count: int,
) -> None:
    meta = devwatch_data.get("meta", {})
    run_id = devwatch_data.get("run_id", "")
    baseline = devwatch_data.get("baseline", "")

    header = f"Run: {run_id}  Baseline: {baseline}\n"
    header += f"Events: {event_count}"
    if dry_run:
        header += "  [dim](dry-run)[/dim]"

    console.print(Panel(header, title="[bold cyan]cns-devlog[/bold cyan]", expand=False))

    if no_changes:
        console.print("[dim]No changes detected — generated minimal page.[/dim]")
    elif event_count == 0:
        console.print("[yellow]Warning: no events but no_changes was false.[/yellow]")
    else:
        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
        table.add_column("slug", style="cyan")
        table.add_column("changed files")
        table.add_column("changed fields")

        for event in devwatch_data.get("events", []):
            m = event.get("meta", {})
            files = m.get("changed_files", [])
            files_str = ", ".join(cf.get("file", "?") for cf in files) if files else "[dim]—[/dim]"
            fields = m.get("changed_fields", [])
            fields_str = ", ".join(fields) if fields else "[dim]—[/dim]"
            table.add_row(m.get("slug", "?"), files_str, fields_str)

        console.print(table)

    if not dry_run:
        console.print(f"  Output: [green]{html_path}[/green]")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_devlog(
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
    dry_run: bool = False,
) -> Path:
    """Run the cns-devlog pipeline. Returns path to output HTML file."""

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # Resolve input
    if input_path:
        devwatch_path = Path(input_path)
    else:
        devwatch_path = _resolve_devwatch_path(today_str)

    # Resolve output
    if output_path:
        html_path = Path(output_path)
    else:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        html_path = EXPORTS_DIR / f"devlog_{today_str}.html"

    # Load devwatch data
    try:
        devwatch_data = _load_devwatch(devwatch_path)
    except (FileNotFoundError, RuntimeError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)

    # Stash source path for HTML meta display
    devwatch_data["_source_path"] = devwatch_path.name

    meta = devwatch_data.get("meta", {})
    no_changes = meta.get("no_changes", False)
    events = devwatch_data.get("events", [])
    event_count = len(events)

    ai_digest: Optional[str] = None

    if no_changes:
        ai_digest = None
    else:
        prompt = _build_prompt(events)

        if dry_run:
            console.print(Panel(prompt, title="[dim]Prompt (dry-run)[/dim]", border_style="dim"))
            console.print("[dim]Dry run — skipping API call and file write.[/dim]")
            _print_summary(devwatch_data, html_path, dry_run=True, no_changes=False, event_count=event_count)
            return html_path

        try:
            ai_digest = _call_openai(SYSTEM_PROMPT, prompt)
        except RuntimeError as exc:
            console.print(f"[bold red]API Error:[/bold red] {exc}")
            sys.exit(1)

    html = _render_html(ai_digest, devwatch_data, no_changes=no_changes)

    if not dry_run:
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html, encoding="utf-8")

    _print_summary(devwatch_data, html_path, dry_run, no_changes, event_count)
    return html_path


# ---------------------------------------------------------------------------
# Direct script execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="devlog",
        description="Generate AI digest from devwatch output and render static HTML",
    )
    parser.add_argument(
        "--input", "-i", default=None,
        help="Override devwatch JSON path (default: latest exports/devwatch_YYYY-MM-DD.json)",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Override HTML output path (default: exports/devlog_YYYY-MM-DD.html)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Print prompt and skip OpenAI call + file write",
    )
    args = parser.parse_args()
    run_devlog(input_path=args.input, output_path=args.output, dry_run=args.dry_run)
