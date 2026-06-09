"""CNS-dashboard — Rich-baserad terminalöverblick.

Kör: python -m scripts.dash
Visar sessioner, öppna idéer och tillgängliga agenter. Ingen Textual.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _age(iso: str) -> str:
    """Mänsklig ålderstext från ISO-tidsstämpel."""
    try:
        then = datetime.fromisoformat(iso)
        if then.tzinfo is None:
            then = then.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        delta = int((now - then).total_seconds())
    except Exception:
        return "?"
    if delta < 60:
        return f"{delta}s"
    if delta < 3600:
        return f"{delta // 60}m"
    if delta < 86400:
        return f"{delta // 3600}h"
    return f"{delta // 86400}d"


def _sessions_table():
    from rich.table import Table

    sys.path.insert(0, str(REPO_ROOT))
    from scripts.session_store import list_sessions

    sessions = list_sessions()[:10]  # senaste 10

    t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    t.add_column("St")
    t.add_column("Ålder")
    t.add_column("Sammanfattning")
    t.add_column("Länk")

    for s in sessions:
        status = s.get("status", "?")
        dot = "[green]●[/green]" if status == "running" else "[dim]○[/dim]"
        age = _age(s.get("created_at", ""))
        summary = (s.get("summary") or "–")[:55]
        link = s.get("link") or {}
        link_str = f"{link.get('kind','?')}:{link.get('ref','?')}" if link else "–"
        t.add_row(dot, age, summary, f"[dim]{link_str}[/dim]")

    return t, len(sessions)


def _ideas_table():
    from rich.table import Table

    from scripts.idea_inbox import list_ideas

    ideas = list_ideas(status="open")[:8]

    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column("•", width=2)
    t.add_column("Text")
    t.add_column("Ålder")

    for idea in ideas:
        age = _age(idea.get("created_at", ""))
        text = (idea.get("text") or "?")[:70]
        t.add_row("[yellow]•[/yellow]", text, f"[dim]{age}[/dim]")

    return t, len(ideas)


def _agents_list() -> tuple[list[str], int]:
    agents_dir = REPO_ROOT / ".claude" / "agents"
    if not agents_dir.exists():
        return [], 0
    names = sorted(p.stem for p in agents_dir.glob("*.md"))
    return names, len(names)


def main() -> None:
    from rich.columns import Columns
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    console = Console()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    console.print()
    console.rule(f"[bold]CNS[/bold]  [dim]{now_str}[/dim]")
    console.print()

    # Sessioner
    try:
        s_table, s_count = _sessions_table()
        console.print(
            Panel(s_table, title=f"[bold]Sessioner[/bold] ({s_count})", border_style="cyan")
        )
    except Exception as exc:
        console.print(f"[red]Sessioner: {exc}[/red]")

    # Idéer
    try:
        i_table, i_count = _ideas_table()
        console.print(
            Panel(i_table, title=f"[bold]Öppna idéer[/bold] ({i_count})", border_style="yellow")
        )
    except Exception as exc:
        console.print(f"[red]Idéer: {exc}[/red]")

    # Agenter
    try:
        agent_names, a_count = _agents_list()
        agent_markup = "  ".join(f"[cyan]{n}[/cyan]" for n in agent_names)
        console.print(
            Panel(agent_markup, title=f"[bold]Agenter[/bold] ({a_count})", border_style="magenta")
        )
    except Exception as exc:
        console.print(f"[red]Agenter: {exc}[/red]")

    console.print()


if __name__ == "__main__":
    main()
