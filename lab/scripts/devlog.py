"""cns-devlog: AI-powered daily digest from cns-devwatch output.

Reads exports/devwatch_YYYY-MM-DD.json, calls Anthropic Claude for a Swedish summary,
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
# Anthropic config
# ---------------------------------------------------------------------------

ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-5"

SYSTEM_PROMPT = (
    "Du är en produktchef som skriver en daglig brief till sig själv. "
    "Du jobbar ensam – inga team, inga intressenter, inga demos att planera. "
    "Var konkret och kortfattad. Fokusera på faktiska framsteg och nästa steg. "
    "Ignorera administrativa ändringar som datumfält och kostnadsestimat om "
    "inget substantiellt innehåll ändrats. "
    "Svara på svenska."
)

# ---------------------------------------------------------------------------
# API key
# ---------------------------------------------------------------------------


def _get_api_key() -> str:
    load_dotenv()
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key == "your_key_here":
        raise RuntimeError(
            "Anthropic API key not configured. "
            "Add ANTHROPIC_API_KEY to .env to use cns devlog."
        )
    return key


# ---------------------------------------------------------------------------
# Eventstream input helpers
# ---------------------------------------------------------------------------


def _load_eventstream_events() -> list[dict]:
    """Load recent events from eventstream.

    Priority: Redis live-buffer > aggregate JSON > regenerate from .jsonl.
    """
    from scripts.eventstream import read_from_redis, generate_aggregate

    # 1. Try Redis first
    events = read_from_redis(limit=500)
    if events:
        return events

    # 2. Fallback to aggregate JSON
    agg_path = EXPORTS_DIR / "eventstream_latest.json"
    if agg_path.exists():
        try:
            with open(agg_path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass

    # 3. Last resort: regenerate aggregate from .jsonl files
    try:
        generate_aggregate()
        with open(agg_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass

    return []


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def _build_prompt(events: list[dict]) -> str:
    """Build the user prompt from eventstream events."""
    parts: list[str] = [
        "Här är en sammanfattning av aktivitet i min projektportfölj:\n"
    ]

    for event in events:
        slug = event.get("slug", "unknown")
        what = event.get("what", "")
        why = event.get("why", "")
        how = event.get("how", "")
        meta = event.get("meta", {})
        node_title = meta.get("node_title", slug)
        stage_from = meta.get("stage_from")
        stage_to = meta.get("stage_to")
        changed_fields = meta.get("changed_fields", [])

        parts.append("---")
        parts.append(f"Projekt: {node_title} (slug: {slug})")
        parts.append(f"Händelsetyp: {what}")
        if stage_from is not None and stage_to is not None:
            parts.append(f"Stage-övergång: {stage_from} → {stage_to}")
        if changed_fields:
            parts.append(f"Ändrade fält: {', '.join(changed_fields)}")
        if why:
            parts.append(f"Beskrivning: {why}")
        if how:
            parts.append(f"Sammanfattning: {how}")
        parts.append("")

    parts.append("---\n\n")
    parts.append(
        "Skriv en daglig portföljbrief på svenska. Max 400 ord totalt.\n\n"
        "Prioritering av ändringar (högst till lägst):\n"
        "1. stage_change – avgörande signal\n"
        "2. Nya noder eller ändrade relationer (part_of, feeds, depends_on)\n"
        "3. Deploy-events och mergade PRs\n"
        "4. Ändringar i Syfte, Status, eller Nästa steg\n"
        "5. Endast frontmatter-fält som updated – ignorera\n\n"
        "Regler:\n"
        "- Börja direkt med analysen. Upprepa inte listan ovan.\n"
        "- Ignorera projekt där bara README-filer eller scaffold-mappar ändrats – det är infrastruktur, inte progress.\n"
        "- Ignorera projekt där bara frontmatter-fält som updated ändrats utan sektionsinnehåll.\n"
        "- Fokusera på projekt där faktiskt innehåll ändrats.\n"
        "- Om inga meningsfulla ändringar finns: skriv 'Ingen meningsfull aktivitet idag.' och inget mer.\n\n"
        "Format:\n"
        "## Vad hände igår\n"
        "Per projekt med faktisk aktivitet – vad ändrades konkret.\n\n"
        "## Vad är kvar\n"
        "Per projekt – nästa konkreta steg.\n\n"
        "## Nästa steg idag\n"
        "Max 3 punkter för hela portföljen."
    )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Anthropic Claude caller
# ---------------------------------------------------------------------------


def _call_claude(system_prompt: str, user_prompt: str) -> str:
    """Call Anthropic Claude Messages API and return the text content."""
    api_key = _get_api_key()

    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 800,
        "temperature": 0.4,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
    }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    try:
        resp = requests.post(
            ANTHROPIC_ENDPOINT, json=payload, headers=headers, timeout=60
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Anthropic API request failed: {exc}")

    if resp.status_code != 200:
        raise RuntimeError(
            f"Anthropic API error {resp.status_code}: {resp.text}"
        )

    data = resp.json()
    try:
        content = data["content"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected Anthropic response structure: {exc}")

    content = content.strip()
    if not content:
        raise RuntimeError("Anthropic returned empty content.")

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

        # Numbered headings: "1. Lång rubriktext..." → <h3>
        numbered_heading = re.match(r"^\d+\.\s+(.{40,})$", stripped)
        if numbered_heading:
            _flush_list()
            blocks.append(f"<h3>{_inline_format(numbered_heading.group(1))}</h3>")
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
    event_count: int,
    date_str: str,
) -> str:
    """Render a complete self-contained HTML page."""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    digest_html = ""
    if not ai_digest:
        digest_html = (
            '<div class="no-activity">'
            "<p>Ingen aktivitet i portföljen idag.</p>"
            "</div>"
        )
    else:
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
        <p><span>Källa:</span> eventstream</p>
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
    events: list[dict],
    html_path: Optional[Path],
    json_path: Path,
    dry_run: bool,
    no_changes: bool,
    event_count: int,
) -> None:
    header = f"Events: {event_count}"
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
        table.add_column("what")
        table.add_column("why")

        for event in events:
            slug = event.get("slug", "?")
            what = event.get("what", "")
            why = event.get("why", "")[:40]
            table.add_row(slug, what, why)

        console.print(table)

    if not dry_run:
        console.print(f"  JSON: [green]{json_path}[/green]")
        if html_path:
            console.print(f"  HTML: [green]{html_path}[/green]")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_devlog(
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
    dry_run: bool = False,
    html: bool = False,
) -> dict:
    """Run the cns-devlog pipeline. Returns digest dict.

    Args:
        input_path: Ignored (kept for backwards compatibility).
        output_path: Override output path for HTML (if html=True).
        dry_run: Print prompt and skip API call + file writes.
        html: Also generate deprecated HTML output.

    Returns:
        {"text": str, "generated_at": str, "event_count": int, "html_path": str|None}
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # Load eventstream events
    events = _load_eventstream_events()

    # Inclusive source filter: allow devwatch, github, manual, quest
    # Exclude workflow_run noise. Deploy sources added when adapters implement.
    allowed_sources = {"devwatch", "github", "manual", "quest"}

    cutoff = now - timedelta(hours=24)
    cutoff_iso = cutoff.isoformat()

    filtered = [
        e for e in events
        if e.get("source") in allowed_sources and e.get("when", "") >= cutoff_iso
    ]

    event_count = len(filtered)
    no_changes = event_count == 0

    ai_digest: Optional[str] = None

    if not no_changes:
        prompt = _build_prompt(filtered)

        if dry_run:
            console.print(Panel(prompt, title="[dim]Prompt (dry-run)[/dim]", border_style="dim"))
            console.print("[dim]Dry run — skipping API call and file write.[/dim]")
            return {
                "text": "",
                "generated_at": now.isoformat(),
                "event_count": event_count,
                "html_path": None,
            }

        try:
            ai_digest = _call_claude(SYSTEM_PROMPT, prompt)
        except RuntimeError as exc:
            console.print(f"[bold red]API Error:[/bold red] {exc}")
            sys.exit(1)

    # Build result dict
    result = {
        "text": ai_digest or "",
        "generated_at": now.isoformat(),
        "event_count": event_count,
        "html_path": None,
    }

    # Resolve output paths
    html_path: Optional[Path] = None
    if html:
        if output_path:
            html_path = Path(output_path)
        else:
            EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
            html_path = EXPORTS_DIR / f"devlog_{today_str}.html"
        result["html_path"] = str(html_path)

    # Save JSON digest always
    json_path = EXPORTS_DIR / f"devlog_{today_str}.json"
    if not dry_run:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    # Render HTML if requested
    if html and html_path:
        html_content = _render_html(ai_digest, event_count, today_str)
        if not dry_run:
            html_path.write_text(html_content, encoding="utf-8")

    if not dry_run:
        _print_summary(filtered, html_path, json_path, dry_run, no_changes, event_count)

    return result


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
        help="Deprecated: eventstream is now the default input",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Override HTML output path (default: exports/devlog_YYYY-MM-DD.html)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Print prompt and skip Claude call + file write",
    )
    parser.add_argument(
        "--html", action="store_true", default=False,
        help="Also generate deprecated HTML output",
    )
    args = parser.parse_args()
    run_devlog(input_path=args.input, output_path=args.output, dry_run=args.dry_run, html=args.html)
