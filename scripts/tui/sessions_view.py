"""CnsSessionsScreen — TUI-vy för CNS-sessionsträdet (tangent n).

Visar sessioner från session_store.py i ett träd (parent_id-baserad nästling).
Enter navigerar till ett .jsonl-transkript om transcript_id finns.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Label, ListItem, ListView, Static, Tree
from textual.widgets.tree import TreeNode


def _session_label(s: dict) -> Text:
    """Trädlabel: fork_name/summary + status-badge."""
    name = s.get("fork_name") or ""
    summary = (s.get("summary") or "")[:52]
    display = name if name else summary
    status = s.get("status", "")
    status_colors = {"running": "green", "done": "dim", "error": "red"}
    color = status_colors.get(status, "dim")
    label = Text(display or "(namnlös)")
    if status:
        label.append("  ")
        label.append(f"[{status}]", style=color)
    return label


def _session_detail(s: dict) -> str:
    """Rich-markup för detaljpanelen för en session."""
    lines: list[str] = []
    sid = s.get("id", "?")
    lines.append(f"[bold]{s.get('fork_name') or sid}[/bold]")
    lines.append(f"[dim]{sid}[/dim]")
    lines.append("")

    status = s.get("status", "")
    status_colors = {"running": "green", "done": "dim", "error": "red"}
    color = status_colors.get(status, "dim")
    lines.append(f"Status: [{color}]{status}[/{color}]")

    parent = s.get("parent_id")
    if parent:
        lines.append(f"[dim]parent: {parent}[/dim]")
    else:
        lines.append("[dim]rot-session (ingen parent)[/dim]")

    link = s.get("link") or {}
    if link.get("kind"):
        lines.append(f"Länk: {link['kind']}:{link.get('ref', '')}")

    created = (s.get("created_at") or "")[:16].replace("T", " ")
    updated = (s.get("updated_at") or "")[:16].replace("T", " ")
    if created:
        lines.append(f"[dim]skapad: {created}  uppdaterad: {updated}[/dim]")

    summary = s.get("summary", "")
    if summary:
        lines.append("")
        lines.append(summary)

    tid = s.get("transcript_id")
    if tid:
        lines.append("")
        lines.append(f"[dim]transkript: {tid}[/dim]")
        lines.append("[dim]Enter öppnar transkriptet (claude --resume)[/dim]")

    return "\n".join(lines)


def _load_tree() -> tuple[dict[str, dict], list[dict]]:
    """Ladda alla sessioner, returnera {id: session} och rot-noderna (parent_id=None)."""
    try:
        from scripts import session_store

        sessions = session_store.load_all_sessions()
        by_id = {s["id"]: s for s in sessions}
        roots = [s for s in sessions if not s.get("parent_id")]
        return by_id, roots
    except Exception:
        return {}, []


class CnsSessionsScreen(ModalScreen):
    """CNS-sessionsträd: parent_id-nästlade arbetspass (tangent n).

    Enter återupptar markerat transkript (claude --resume) om transcript_id finns.
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Stäng"),
        Binding("n", "dismiss", "Stäng"),
        Binding("q", "dismiss", "Stäng"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._by_id: dict[str, dict] = {}
        self._selected: dict | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="cnssess-outer"):
            with VerticalScroll(id="cnssess-tree-pane"):
                yield Static(
                    "[bold]CNS-sessionsträd[/bold]  [dim]— n/esc stänger · Enter återupptar[/dim]",
                    id="cnssess-head",
                )
                yield Tree("Sessioner", id="cnssess-tree")
            with VerticalScroll(id="cnssess-detail-pane"):
                yield Static("Välj en session.", id="cnssess-detail")

    def on_mount(self) -> None:
        self._by_id, roots = _load_tree()
        tree = self.query_one("#cnssess-tree", Tree)
        tree.root.expand()

        if not roots and not self._by_id:
            tree.root.set_label("Inga sessioner")
            return

        tree.root.set_label(f"Sessioner ({len(self._by_id)})")
        for root in sorted(roots, key=lambda s: s.get("created_at", ""), reverse=True):
            self._add_session(tree.root, root)

    def _add_session(self, parent: TreeNode, s: dict) -> None:
        children = [
            child
            for child in self._by_id.values()
            if child.get("parent_id") == s["id"]
        ]
        if children:
            branch = parent.add(_session_label(s), data=s, expand=True)
            for child in sorted(children, key=lambda c: c.get("created_at", "")):
                self._add_session(branch, child)
        else:
            parent.add_leaf(_session_label(s), data=s)

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        s = event.node.data
        detail = self.query_one("#cnssess-detail", Static)
        if isinstance(s, dict):
            self._selected = s
            detail.update(_session_detail(s))
        else:
            self._selected = None
            detail.update("Välj en session.")

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        s = event.node.data
        if not isinstance(s, dict):
            return
        tid = s.get("transcript_id")
        if not tid:
            self.app.notify(f"Ingen transcript_id för {s.get('id', '?')}", timeout=4)
            return
        self._resume(tid)

    def _resume(self, transcript_id: str) -> None:
        claude = shutil.which("claude")
        if not claude:
            self.app.notify(
                f"'claude' saknas i PATH. Kör: claude --resume {transcript_id}",
                severity="warning",
                timeout=8,
            )
            return
        with self.app.suspend():
            subprocess.run([claude, "--resume", transcript_id])
