"""Session-hub — interaktiv Rich-cockpit för CNS-sessioner (issue #17).

Navigerbar sessionsöversikt med återupptagning via ``claude --resume``.
Startas av ``python -m scripts.dash --hub``.

Tangenter (piltangenter+Enter):
  ↑/↓        flytta markör
  Enter       återuppta markerad session (claude --resume <transcript_id>)
  l           växla loop-markering (.cns-loop-marks)
  n           TODO-stub: ny session via MCP
  q / Esc     avsluta

Input-strategi:
  1. Försöker lazy-importera ``readchar`` (pip install readchar) för tecken-för-tecken.
  2. Faller tillbaka på numrerad inmatning (skriv radnummer + Enter) om readchar saknas.
  Kraschar aldrig — degraderar med ett tydligt meddelande.

TTY-guard: om stdin inte är en TTY skrivs ett meddelande och funktionen returnerar
direkt (så att import + ``run()`` alltid fungerar headless).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOOP_MARKS_FILE = REPO_ROOT / ".cns-loop-marks"

# -- hjälpfunktioner ----------------------------------------------------------


def _age(iso: str) -> str:
    """Tidssträng sedan iso-tidstämpel ('2m', '3h', '5d', '?')."""
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


def _load_loop_marks() -> set[str]:
    """Läs .cns-loop-marks (en session-id per rad). Degraderar till tom mängd."""
    try:
        if LOOP_MARKS_FILE.exists():
            return {
                ln.strip()
                for ln in LOOP_MARKS_FILE.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            }
    except Exception:
        pass
    return set()


def _save_loop_marks(marks: set[str]) -> None:
    """Skriv tillbaka .cns-loop-marks. Read-first (ny mängd ersätter)."""
    try:
        LOOP_MARKS_FILE.write_text(
            "\n".join(sorted(marks)) + ("\n" if marks else ""),
            encoding="utf-8",
        )
    except Exception:
        pass


def _toggle_loop_mark(session_id: str) -> bool:
    """Växla loop-markering. Returnerar ny markerings-status (True = markerad)."""
    marks = _load_loop_marks()
    if session_id in marks:
        marks.discard(session_id)
        _save_loop_marks(marks)
        return False
    else:
        marks.add(session_id)
        _save_loop_marks(marks)
        return True


# -- datahämtning -------------------------------------------------------------


def _load_sessions_with_transcripts() -> list[dict]:
    """Sammanvävda CNS-sessioner + Claude Code-transkript.

    Flöde:
    1. list_sessions() från session_store — nyast först.
    2. list_transcripts() från sources — indexerade på session_id.
    3. Varje CNS-session berikas med transcript_id om ett matchande transkript finns
       (matchar via transcript_id-fältet ELLER session.id mot transkriptets session_id).
    4. Transkript utan matchande CNS-session läggs till sist som "transcript-only"-rader.

    Degraderar helt: returnerar [] om något kärnfel uppstår.
    """
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from scripts.session_store import list_sessions
        from scripts.tui.sources import list_transcripts

        sessions = list_sessions()
    except Exception:
        return []

    try:
        transcripts = list_transcripts()
    except Exception:
        transcripts = []

    # Index: transcript session_id → Transcript
    tr_by_id: dict[str, object] = {}
    for t in transcripts:
        tr_by_id[t.session_id] = t

    used_tr_ids: set[str] = set()
    rows: list[dict] = []

    # Bygg träd: parent_id → [session]
    by_parent: dict[str | None, list[dict]] = {}
    for s in sessions:
        by_parent.setdefault(s.get("parent_id"), []).append(s)

    def _enrich(s: dict, depth: int) -> dict:
        """Lägg till härledd info på en session-dict."""
        tid = s.get("transcript_id")
        tr = None
        if tid and tid in tr_by_id:
            tr = tr_by_id[tid]
            used_tr_ids.add(tid)
        elif s.get("id") in tr_by_id:
            tr = tr_by_id[s["id"]]
            used_tr_ids.add(s["id"])
        return {**s, "_tr": tr, "_depth": depth}

    seen: set[str] = set()

    def _flatten(node: dict, depth: int) -> None:
        sid = node.get("id", "")
        if sid in seen:
            return
        seen.add(sid)
        rows.append(_enrich(node, depth))
        kids = sorted(
            by_parent.get(sid, []), key=lambda c: c.get("created_at", "")
        )
        for kid in kids:
            _flatten(kid, depth + 1)

    # Rötter: sessioner utan parent, nyast först
    roots = sorted(
        [s for s in sessions if not s.get("parent_id")],
        key=lambda s: s.get("created_at", ""),
        reverse=True,
    )
    for root in roots:
        _flatten(root, 0)

    # Waif-sessioner med parent_id men föräldern saknas
    for s in sessions:
        if s.get("id") not in seen:
            rows.append(_enrich(s, 0))

    # Transkript utan CNS-session
    for t in transcripts:
        if t.session_id not in used_tr_ids:
            rows.append(
                {
                    "id": t.session_id,
                    "created_at": t.timestamp,
                    "updated_at": t.timestamp,
                    "status": "transcript",
                    "summary": t.title,
                    "link": None,
                    "fork_name": None,
                    "parent_id": None,
                    "transcript_id": t.session_id,
                    "_tr": t,
                    "_depth": 0,
                }
            )

    return rows


# -- rendering ----------------------------------------------------------------


def _render_rows(
    rows: list[dict],
    cursor: int,
    loop_marks: set[str],
    message: str,
    console,
    use_readchar: bool,
) -> None:
    """Rita om hela skärmen: header + rader + footer."""
    from rich.text import Text

    console.clear()
    console.print()
    console.rule("[bold]CNS Session-hub[/bold]  [dim]q=avsluta  l=loop  n=ny(stub)[/dim]")
    console.print()

    if not rows:
        console.print("[dim]  Inga sessioner hittades.[/dim]")
        console.print()
    else:
        for i, row in enumerate(rows):
            sid = row.get("id", "")
            status = row.get("status", "?")
            created = row.get("created_at", "")
            fork_name = row.get("fork_name") or ""
            summary = (row.get("summary") or "")[:52]
            link = row.get("link") or {}
            tr = row.get("_tr")
            depth = row.get("_depth", 0)
            loop_marked = sid in loop_marks

            # Status-prick
            if status == "running":
                dot = "[bold green]●[/bold green]"
            elif status == "transcript":
                dot = "[dim blue]◦[/dim blue]"
            else:
                dot = "[dim]○[/dim]"

            age = _age(created) if created else "?"
            label = fork_name if fork_name else summary
            if not label:
                label = sid[:12] if sid else "(okänd)"

            link_str = ""
            if link.get("kind"):
                link_str = f"[dim]({link['kind']}:{link.get('ref', '')})[/dim] "

            resume_tag = "[dim green][resumable][/dim green] " if tr else ""
            loop_tag = "[bold cyan][loop][/bold cyan] " if loop_marked else ""

            indent = "  " * depth

            line = Text()
            if i == cursor:
                line.append("▶ ", style="bold yellow")
            else:
                line.append("  ")
            line.append(f"{indent}{dot} ", end="")  # type: ignore[arg-type]
            line.append(f"{age:>5}  ", style="dim")
            line.append(f"{label[:28]:<28}  ")

            # Lägg till markup-strängar som plain (undvik Rich-parse-krasch)
            suffix = f"{link_str}{resume_tag}{loop_tag}"
            if suffix.strip():
                line.append_text(Text.from_markup(suffix))

            console.print(line)

    console.print()

    if message:
        console.print(f"  [yellow]{message}[/yellow]")
        console.print()

    if use_readchar:
        console.print(
            "[dim]  ↑↓ flytta  Enter återuppta  l loop  n ny(stub)  q avsluta[/dim]"
        )
    else:
        console.print(
            "[dim]  Ange radnummer (1–{n}) + Enter  |  l<nr>=loop  n=ny(stub)  q=avsluta[/dim]".format(
                n=len(rows)
            )
        )
    console.print()


# -- input-hantering ----------------------------------------------------------


def _get_readchar():
    """Lazy-importera readchar. Returnerar modulen eller None."""
    try:
        import readchar  # type: ignore[import]

        return readchar
    except ImportError:
        return None


def _readkey_numeric(prompt_console) -> str:
    """Numrerad inmatning som fallback när readchar saknas.

    Returnerar ett "kommando" ur mängden:
      'up', 'down', 'enter', 'l', 'n', 'q', 'raw:<text>'
    """
    prompt_console.print("[dim]  Kommando (nummer/l<nr>/n/q/Enter):[/dim] ", end="")
    try:
        raw = input().strip()
    except (EOFError, KeyboardInterrupt):
        return "q"
    if not raw:
        return "enter"
    if raw.lower() == "q":
        return "q"
    if raw.lower() == "n":
        return "n"
    if raw.lower().startswith("l"):
        return f"raw:l:{raw[1:].strip()}"
    try:
        int(raw)
        return f"raw:goto:{raw}"
    except ValueError:
        return f"raw:{raw}"


# -- resume -------------------------------------------------------------------


def _resume_session(transcript_id: str, console) -> str:
    """Kör claude --resume <transcript_id> i subprocess. Returnerar statusmeddelande."""
    claude = shutil.which("claude")
    if not claude:
        return (
            f"'claude' saknas i PATH. Kör manuellt: claude --resume {transcript_id}"
        )
    try:
        subprocess.run([claude, "--resume", transcript_id], cwd=str(REPO_ROOT))
        return f"Återvände från session {transcript_id[:12]}."
    except Exception as exc:
        return f"Fel vid claude --resume: {exc}"


# -- huvud-loop ---------------------------------------------------------------


def run() -> None:
    """Starta session-hubben. TTY-guard: degraderar om stdin inte är en TTY."""
    import io

    # TTY-guard: kör aldrig en blockerande loop utan TTY.
    if not sys.stdin.isatty():
        sys.stdout.write(
            "[session-hub] Kräver en interaktiv TTY. "
            "Kör: python -m scripts.dash --hub\n"
        )
        sys.stdout.flush()
        return

    from rich.console import Console

    utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    console = Console(file=utf8_stdout, highlight=False)

    readchar = _get_readchar()
    use_readchar = readchar is not None

    if not use_readchar:
        console.print(
            "[yellow]  Obs: readchar saknas (pip install readchar). "
            "Faller tillbaka på numrerad inmatning.[/yellow]"
        )

    rows: list[dict] = _load_sessions_with_transcripts()
    cursor = 0
    message = ""
    loop_marks = _load_loop_marks()

    _render_rows(rows, cursor, loop_marks, message, console, use_readchar)

    while True:
        message = ""

        if use_readchar:
            try:
                key = readchar.readkey()
            except (KeyboardInterrupt, EOFError):
                break
            # Normalisera piltangenter
            up_keys = {readchar.key.UP, "k"}
            down_keys = {readchar.key.DOWN, "j"}
            enter_keys = {readchar.key.ENTER, "\r", "\n"}

            if key in up_keys:
                if rows:
                    cursor = (cursor - 1) % len(rows)
            elif key in down_keys:
                if rows:
                    cursor = (cursor + 1) % len(rows)
            elif key in enter_keys:
                if rows:
                    row = rows[cursor]
                    tr = row.get("_tr")
                    tid = row.get("transcript_id") or (tr.session_id if tr else None)
                    if tid:
                        console.clear()
                        console.print(f"[dim]Återupptar {tid[:16]}...[/dim]")
                        message = _resume_session(tid, console)
                        rows = _load_sessions_with_transcripts()
                        loop_marks = _load_loop_marks()
                    else:
                        message = "Ingen transcript_id — kan inte återuppta."
            elif key in ("l", "L"):
                if rows:
                    sid = rows[cursor].get("id", "")
                    if sid:
                        marked = _toggle_loop_mark(sid)
                        loop_marks = _load_loop_marks()
                        message = (
                            f"[loop] markerad: {sid[:12]}"
                            if marked
                            else f"[loop] borttagen: {sid[:12]}"
                        )
            elif key in ("n", "N"):
                message = "TODO: skapa session via MCP — ej impl. i hubben"
            elif key in ("q", "Q", readchar.key.ESCAPE):
                break
            else:
                # Okänd tangent — ignorera tyst
                _render_rows(rows, cursor, loop_marks, message, console, use_readchar)
                continue

        else:
            # Numrerad fallback
            raw_cmd = _readkey_numeric(console)
            if raw_cmd == "q":
                break
            elif raw_cmd == "up":
                if rows:
                    cursor = (cursor - 1) % len(rows)
            elif raw_cmd == "down":
                if rows:
                    cursor = (cursor + 1) % len(rows)
            elif raw_cmd == "enter":
                if rows:
                    row = rows[cursor]
                    tr = row.get("_tr")
                    tid = row.get("transcript_id") or (tr.session_id if tr else None)
                    if tid:
                        console.clear()
                        console.print(f"[dim]Återupptar {tid[:16]}...[/dim]")
                        message = _resume_session(tid, console)
                        rows = _load_sessions_with_transcripts()
                        loop_marks = _load_loop_marks()
                    else:
                        message = "Ingen transcript_id — kan inte återuppta."
            elif raw_cmd == "n":
                message = "TODO: skapa session via MCP — ej impl. i hubben"
            elif raw_cmd.startswith("raw:goto:"):
                try:
                    idx = int(raw_cmd.split(":")[-1]) - 1
                    if 0 <= idx < len(rows):
                        cursor = idx
                    else:
                        message = f"Ogiltigt radnummer (1–{len(rows)})"
                except ValueError:
                    message = "Ogiltigt kommando."
            elif raw_cmd.startswith("raw:l:"):
                nr_str = raw_cmd.split(":", 2)[-1].strip()
                try:
                    idx = int(nr_str) - 1 if nr_str else cursor
                    if 0 <= idx < len(rows):
                        sid = rows[idx].get("id", "")
                        if sid:
                            marked = _toggle_loop_mark(sid)
                            loop_marks = _load_loop_marks()
                            message = (
                                f"[loop] markerad: {sid[:12]}"
                                if marked
                                else f"[loop] borttagen: {sid[:12]}"
                            )
                    else:
                        message = f"Ogiltigt radnummer."
                except ValueError:
                    message = "Ange l<nummer>, t.ex. l3."
            else:
                message = f"Okänt kommando: {raw_cmd}"

        _render_rows(rows, cursor, loop_marks, message, console, use_readchar)

    console.print("\n[dim]Session-hub avslutad.[/dim]")
