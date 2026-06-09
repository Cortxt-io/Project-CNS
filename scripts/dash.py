"""CNS-dashboard — Rich-baserad terminalöverblick.

Kör:               python -m scripts.dash
Live-läge (5 s):   python -m scripts.dash --watch
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
BTW_DIR = REPO_ROOT / "exports" / "btw"


def _age(iso: str) -> str:
    try:
        then = datetime.fromisoformat(iso.rstrip("Z"))
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


def _load_btw_asides(limit: int = 12) -> list[dict]:
    all_asides: list[dict] = []
    if not BTW_DIR.exists():
        return []
    for path in BTW_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for aside in data.get("asides", []):
                all_asides.append({
                    "ts": aside.get("ts", ""),
                    "text": aside.get("text", ""),
                    "fork": aside.get("fork", ""),
                    "session_id": data.get("session_id", ""),
                })
        except Exception:
            continue
    all_asides.sort(key=lambda a: a.get("ts", ""), reverse=True)
    return all_asides[:limit]


def _agent_status_table():
    """Agenter med status baserat på fork_name i sessioner."""
    from rich.table import Table

    sys.path.insert(0, str(REPO_ROOT))
    from scripts.session_store import list_sessions

    sessions = list_sessions()

    # Senaste session per fork_name
    by_agent: dict[str, dict] = {}
    for s in sessions:
        fn = s.get("fork_name")
        if fn and fn not in by_agent:
            by_agent[fn] = s

    agent_names = sorted(p.stem for p in AGENTS_DIR.glob("*.md")) if AGENTS_DIR.exists() else []

    t = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 1))
    t.add_column("", width=2)
    t.add_column("Agent", width=22)
    t.add_column("Senast", width=8)
    t.add_column("Vad")

    running_count = 0
    for name in agent_names:
        sess = by_agent.get(name)
        if sess:
            status = sess.get("status", "?")
            if status == "running":
                dot = "[bold green]●[/bold green]"
                running_count += 1
            else:
                dot = "[dim]○[/dim]"
            age = _age(sess.get("updated_at") or sess.get("created_at", ""))
            summary = (sess.get("summary") or "–")[:60]
        else:
            dot = "[dim]·[/dim]"
            age = "–"
            summary = "[dim]ingen session bokförd ännu[/dim]"
        t.add_row(dot, f"[cyan]{name}[/cyan]", f"[dim]{age}[/dim]", summary)

    return t, len(agent_names), running_count


def _sessions_table():
    from rich.table import Table
    from scripts.session_store import list_sessions

    sessions = list_sessions()[:12]

    t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    t.add_column("", width=2)
    t.add_column("Ålder", width=6)
    t.add_column("Agent/fork", width=20)
    t.add_column("Sammanfattning")

    for s in sessions:
        status = s.get("status", "?")
        if status == "running":
            dot = "[bold green]●[/bold green]"
        else:
            dot = "[dim]○[/dim]"
        age = _age(s.get("created_at", ""))
        fork = (s.get("fork_name") or "–")[:18]
        summary = (s.get("summary") or "–")[:65]
        link = s.get("link") or {}
        if link:
            lstr = f"[dim]({link.get('kind','?')}:{link.get('ref','?')})[/dim] "
        else:
            lstr = ""
        t.add_row(dot, age, f"[dim]{fork}[/dim]", f"{lstr}{summary}")

    return t, len(sessions)


def _btw_feed():
    """Kommunikationslogg — senaste btw-asides från alla sessioner."""
    from rich.table import Table

    asides = _load_btw_asides(10)
    if not asides:
        return None, 0

    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column("Ålder", width=6)
    t.add_column("Fork", width=20)
    t.add_column("Text")

    for a in asides:
        age = _age(a["ts"])
        fork = (a.get("fork") or a.get("session_id", "")[:8] or "–")[:18]
        text = (a.get("text") or "–")[:80]
        t.add_row(f"[dim]{age}[/dim]", f"[yellow]{fork}[/yellow]", text)

    return t, len(asides)


def _ideas_table():
    from rich.table import Table
    from scripts.idea_inbox import list_ideas

    ideas = list_ideas(status="open")[:6]

    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column("•", width=2)
    t.add_column("Text")
    t.add_column("Ålder", width=6)

    for idea in ideas:
        age = _age(idea.get("created_at", ""))
        text = (idea.get("text") or "?")[:70]
        t.add_row("[yellow]•[/yellow]", text, f"[dim]{age}[/dim]")

    return t, len(ideas)


def _render(console) -> None:
    from rich.panel import Panel

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print()
    console.rule(f"[bold]CNS[/bold]  [dim]{now_str}[/dim]")
    console.print()

    # Agenter med status
    try:
        ag_table, ag_count, running = _agent_status_table()
        title = f"[bold]Agenter[/bold] ({ag_count}"
        if running:
            title += f",  [bold green]{running} kör just nu[/bold green]"
        else:
            title += ",  ingen aktiv"
        title += ")"
        console.print(Panel(ag_table, title=title, border_style="magenta"))
    except Exception as exc:
        console.print(f"[red]Agenter: {exc}[/red]")

    # Sessioner
    try:
        s_table, s_count = _sessions_table()
        console.print(
            Panel(s_table, title=f"[bold]Sessioner[/bold] ({s_count})", border_style="cyan")
        )
    except Exception as exc:
        console.print(f"[red]Sessioner: {exc}[/red]")

    # Kommunikationslogg (btw-asides)
    try:
        btw_table, btw_count = _btw_feed()
        if btw_table and btw_count > 0:
            console.print(
                Panel(
                    btw_table,
                    title=f"[bold]Kommunikationslogg[/bold] (btw, {btw_count} senaste)",
                    border_style="yellow",
                )
            )
    except Exception as exc:
        console.print(f"[red]Kommunikationslogg: {exc}[/red]")

    # Idéer
    try:
        i_table, i_count = _ideas_table()
        console.print(
            Panel(i_table, title=f"[bold]Öppna idéer[/bold] ({i_count})", border_style="green")
        )
    except Exception as exc:
        console.print(f"[red]Idéer: {exc}[/red]")

    console.print()


def main() -> None:
    from rich.console import Console

    watch = "--watch" in sys.argv
    console = Console()

    if watch:
        try:
            while True:
                console.clear()
                _render(console)
                console.print("[dim]Uppdateras var 5 s — Ctrl+C för att avsluta[/dim]")
                time.sleep(5)
        except KeyboardInterrupt:
            console.print("\n[dim]Avslutad.[/dim]")
    else:
        _render(console)


if __name__ == "__main__":
    main()
