"""CnsTuiApp — interaktiv portföljöverblick byggd med textual.

Vänster: part_of-nästlat träd, färgat på stage. Höger: detaljpanel för vald
nod (kind/stage/status/summary/feeds/depends_on). `/` filtrerar på stage/status.
Körs via `python -m scripts.tui`.
"""

from __future__ import annotations

import shutil
import subprocess

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    RichLog,
    Static,
    Tree,
)
from textual.widgets.tree import TreeNode

from scripts.tui.data import (
    KIND_COLORS,
    STAGE_COLORS,
    STATUS_COLORS,
    NodeView,
    build_forest,
    filter_nodes,
    load_nodes,
)
from scripts.tui.sessions_view import CnsSessionsScreen
from scripts.tui.sources import (
    Transcript,
    git_branches,
    list_transcripts,
    load_ideas,
    load_memory_cards,
    load_skills,
    merged_branches,
    open_issues_for_slug,
)


def _tree_label(node: NodeView) -> Text:
    """Trädlabel: titel + stage-badge, färgad på stage."""
    color = STAGE_COLORS.get(node.stage, "")
    label = Text(node.title or node.slug)
    if node.stage:
        label.append("  ")
        label.append(f"[{node.stage}]", style=color or "dim")
    return label


def _detail_markup(
    node: NodeView,
    ideas: list[dict],
    issue_status: str | None,
    issues: list[dict],
    sessions: list[Transcript],
) -> str:
    """Rich-markup för detaljpanelen, inkl. länkade idéer, issues och sessioner."""
    kind_c = KIND_COLORS.get(node.kind, "dim")
    stage_c = STAGE_COLORS.get(node.stage, "dim")
    status_c = STATUS_COLORS.get(node.status, "dim")

    lines: list[str] = []
    lines.append(f"[bold]{node.title or node.slug}[/bold]")
    lines.append(f"[dim]{node.slug}[/dim]")
    lines.append("")
    lines.append(
        f"[{kind_c}]{node.kind or '—'}[/{kind_c}]  ·  "
        f"[{stage_c}]{node.stage or '—'}[/{stage_c}]  ·  "
        f"[{status_c}]{node.status or '—'}[/{status_c}]"
    )
    if node.part_of:
        lines.append(f"[dim]part_of →[/dim] {node.part_of}")
    lines.append("")

    if node.summary:
        lines.append(node.summary)
        lines.append("")

    if node.feeds:
        lines.append("[bold]feeds →[/bold]")
        lines.extend(f"  • {t}" for t in node.feeds)
        lines.append("")
    if node.depends_on:
        lines.append("[bold]depends_on →[/bold]")
        lines.extend(f"  • {t}" for t in node.depends_on)
        lines.append("")

    # Länkade idéer (idé-inkorgen, filtrerad på slug).
    if ideas:
        lines.append("[bold]💡 Idéer (öppna)[/bold]")
        for i in ideas:
            text = " ".join((i.get("text", "") or "").split())
            lines.append(f"  • {text[:72]}")
        lines.append("")

    # Öppna issues (grindade — degraderar tyst om klient/token saknas).
    if issue_status:
        lines.append(f"[dim]issues: {issue_status}[/dim]")
    elif issues:
        lines.append("[bold]🔧 Öppna issues[/bold]")
        for it in issues:
            num = it.get("number") or it.get("id") or "?"
            title = it.get("title", "")
            lines.append(f"  • #{num} {title[:60]}")
    else:
        lines.append("[dim]issues: inga öppna[/dim]")

    # Sessioner som rört noden (transkript-skanning, heuristisk).
    if sessions:
        lines.append("")
        lines.append("[bold]🗒 Sessioner som rört noden[/bold]")
        for t in sessions[:6]:
            when = t.timestamp[:10]
            lines.append(f"  • [dim]{when}[/dim] {t.title[:54]}")

    if node.tags:
        lines.append("")
        lines.append("[dim]tags: " + ", ".join(node.tags) + "[/dim]")

    return "\n".join(lines).rstrip()


def _overview_markup() -> str:
    """Portföljbred lägesbild: aktiva git-spår + öppna idéer.

    Syftet är kollisionssynlighet — flera lokala feature-brancher = parallella
    spår som kan krocka (precis det som blindade oss idag).
    """
    lines: list[str] = ["[bold]Aktiva git-spår[/bold]", ""]
    branches = git_branches()
    local = [b for b in branches if not b.remote]
    remote_names = {b.name.split("/", 1)[-1] for b in branches if b.remote}
    merged = merged_branches()

    if not local:
        lines.append("[dim](kunde inte läsa git)[/dim]")
    for b in local:
        marker = "[green]▶[/green]" if b.current else " "
        pushed = "[dim](pushad)[/dim]" if b.name in remote_names else "[yellow](endast lokal)[/yellow]"
        is_feature = b.name not in ("main", "master")
        if is_feature and b.name in merged:
            state = "  [green]✓ klar (merge:ad i main)[/green]"
        elif is_feature:
            state = "  [cyan]← spår (ej merge:at)[/cyan]"
        else:
            state = ""
        lines.append(f"{marker} {b.name} {pushed}{state}")

    lines.append("")
    lines.append("[bold]Senaste sessioner[/bold]")
    lines.append("")
    sessions = list_transcripts()
    if not sessions:
        lines.append("[dim]inga sessioner hittade[/dim]")
    for t in sessions[:8]:
        when = t.timestamp[:16].replace("T", " ")
        branch = f"[dim][{t.git_branch}][/dim] " if t.git_branch else ""
        lines.append(f"  • [dim]{when}[/dim] {branch}{t.title[:46]}")

    lines.append("")
    lines.append("[bold]Öppna idéer[/bold]")
    lines.append("")
    ideas = load_ideas()
    if not ideas:
        lines.append("[dim]inga öppna idéer lokalt[/dim]")
    for i in ideas:
        text = " ".join((i.get("text", "") or "").split())
        slug = i.get("slug")
        tag = f" [dim]→ {slug}[/dim]" if slug else ""
        lines.append(f"  • {text[:64]}{tag}")

    lines.append("")
    lines.append("[dim]esc / o stänger · s = bläddra/öppna sessioner[/dim]")
    return "\n".join(lines)


class OverviewScreen(ModalScreen):
    """Modal lägesbild över brancher och idéer (tangent o)."""

    BINDINGS = [
        Binding("escape", "dismiss", "Stäng"),
        Binding("o", "dismiss", "Stäng"),
        Binding("q", "dismiss", "Stäng"),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="overview-box"):
            yield Static(_overview_markup(), id="overview")


class SessionsScreen(ModalScreen):
    """Bläddra Claude Code-sessioner; Enter återupptar markerad (claude --resume)."""

    BINDINGS = [
        Binding("escape", "dismiss", "Stäng"),
        Binding("s", "dismiss", "Stäng"),
        Binding("q", "dismiss", "Stäng"),
    ]

    def __init__(self, transcripts: list[Transcript]) -> None:
        super().__init__()
        self._transcripts = transcripts

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="sessions-box"):
            yield Static(
                "[bold]Sessioner[/bold]  [dim]— Enter återupptar (claude --resume), esc stänger[/dim]\n",
                id="sessions-head",
            )
            items = []
            for t in self._transcripts:
                when = t.timestamp[:16].replace("T", " ") or "?"
                branch = f"[{t.git_branch}] " if t.git_branch else ""
                items.append(ListItem(Label(f"{when}  {branch}{t.title[:50]}")))
            yield ListView(*items, id="sessions-list")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is None or idx >= len(self._transcripts):
            return
        self._resume(self._transcripts[idx])

    def _resume(self, t: Transcript) -> None:
        claude = shutil.which("claude")
        if not claude:
            self.app.notify(
                f"'claude' saknas i PATH. Kör manuellt: claude --resume {t.session_id}",
                severity="warning",
                timeout=8,
            )
            return
        # Suspenda TUI:t, kör claude --resume i samma terminal, återuppta sedan.
        with self.app.suspend():
            subprocess.run([claude, "--resume", t.session_id])


def _knowledge_markup() -> str:
    """Skills (repo) + memory-cards (harness, cross-boundary)."""
    lines: list[str] = ["[bold]Skills[/bold]  [dim](skills/*/SKILL.md)[/dim]", ""]
    skills = load_skills()
    if not skills:
        lines.append("[dim]inga skills[/dim]")
    for s in skills:
        lines.append(f"  • [cyan]{s['name']}[/cyan]")
        if s.get("description"):
            lines.append(f"    [dim]{s['description'][:88]}[/dim]")

    lines.append("")
    lines.append("[bold]Memory-cards[/bold]  [dim](~/.claude/…/memory — ej GitHub-sanning)[/dim]")
    lines.append("")
    cards = load_memory_cards()
    if not cards:
        lines.append("[dim]inga memory-cards[/dim]")
    type_color = {
        "feedback": "yellow",
        "project": "green",
        "reference": "cyan",
        "user": "magenta",
    }
    for c in cards:
        col = type_color.get(c.get("type", ""), "dim")
        tag = f"[{col}]{c.get('type') or '—'}[/{col}]"
        lines.append(f"  • {tag} [bold]{c['name']}[/bold]")
        if c.get("description"):
            lines.append(f"    [dim]{c['description'][:88]}[/dim]")

    lines.append("")
    lines.append("[dim]esc / k stänger[/dim]")
    return "\n".join(lines)


class KnowledgeScreen(ModalScreen):
    """Skills + memory-cards på ett ställe (tangent k)."""

    BINDINGS = [
        Binding("escape", "dismiss", "Stäng"),
        Binding("k", "dismiss", "Stäng"),
        Binding("q", "dismiss", "Stäng"),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="knowledge-box"):
            yield Static(_knowledge_markup(), id="knowledge")


class AgentScreen(ModalScreen):
    """Fråga Claude om markerad nod (agent-host, read-first). Tangent c."""

    BINDINGS = [
        Binding("escape", "dismiss", "Stäng"),
    ]

    def __init__(self, slug: str | None) -> None:
        super().__init__()
        self._slug = slug
        self._session_id: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="agent-box"):
            head = f"[bold]Fråga Claude[/bold]  [dim]— nod: {self._slug or '(ingen)'} · read-first · esc stänger[/dim]"
            yield Static(head, id="agent-head")
            yield RichLog(id="agent-log", wrap=True, markup=True)
            yield Input(placeholder="Fråga om noden… (Enter skickar)", id="agent-input")

    def on_mount(self) -> None:
        self.query_one("#agent-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "agent-input":
            return
        prompt = event.value.strip()
        if not prompt:
            return
        log = self.query_one("#agent-log", RichLog)
        log.write(f"[bold cyan]› {prompt}[/bold cyan]")
        event.input.value = ""
        event.input.disabled = True
        self.run_worker(self._run(prompt), exclusive=True)

    async def _run(self, prompt: str) -> None:
        from scripts.tui.agent_host import run_turn

        log = self.query_one("#agent-log", RichLog)
        got_text = False
        async for kind, payload in run_turn(prompt, slug=self._slug):
            if kind == "session":
                self._session_id = payload
            elif kind == "text":
                got_text = True
                log.write(str(payload))
            elif kind == "tool":
                log.write(f"[dim]· verktyg: {payload}[/dim]")
            elif kind == "error":
                log.write(f"[red]fel: {payload}[/red]")
            elif kind == "result":
                if not got_text and payload:
                    log.write(str(payload))
        self._record_session(prompt)
        inp = self.query_one("#agent-input", Input)
        inp.disabled = False
        inp.focus()

    def _record_session(self, prompt: str) -> None:
        """Bokför passet som CNS-session-post länkad till noden (sessions-spåret)."""
        if not self._session_id:
            return
        try:
            from scripts import session_store

            session_store.save_session(
                summary=f"Agent-host: {prompt[:80]}",
                link_kind="node" if self._slug else None,
                link_ref=self._slug,
                transcript_id=self._session_id,
            )
        except Exception:
            pass


class CnsTuiApp(App):
    """Glanceable portföljöverblick i terminalen."""

    CSS_PATH = "styles.tcss"
    TITLE = "CNS Portföljöverblick"

    BINDINGS = [
        Binding("q", "quit", "Avsluta"),
        Binding("r", "reload", "Ladda om"),
        Binding("o", "overview", "Översikt"),
        Binding("s", "sessions", "Sessioner"),
        Binding("k", "knowledge", "Kunskap"),
        Binding("c", "agent", "Fråga Claude"),
        Binding("n", "cns_sessions", "CNS-sessioner"),
        Binding("slash", "focus_filter", "Filter"),
        Binding("escape", "clear_filter", "Rensa filter", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._all_nodes: dict[str, NodeView] = {}
        self._ideas: list[dict] = []
        self._transcripts: list[Transcript] = []
        self._current_slug: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Tree("Portfölj", id="tree")
            with Vertical(id="detail-pane"):
                yield Input(placeholder="Filtrera på stage/status…", id="filter")
                with VerticalScroll(id="detail-scroll"):
                    yield Static("Välj en nod i trädet.", id="detail")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#filter", Input).display = False
        self._all_nodes = load_nodes()
        self._ideas = load_ideas()
        self._transcripts = list_transcripts(known_slugs=set(self._all_nodes))
        self._populate_tree(self._all_nodes)

    # -- trädbygge ---------------------------------------------------------

    def _populate_tree(self, nodes: dict[str, NodeView]) -> None:
        tree = self.query_one("#tree", Tree)
        tree.clear()
        tree.root.expand()
        roots = build_forest(nodes)
        if not roots:
            tree.root.set_label("Inga noder matchar")
            return
        tree.root.set_label(f"Portfölj ({len(nodes)} noder)")
        for root in roots:
            self._add_node(tree.root, root)

    def _add_node(self, parent: TreeNode, node: NodeView) -> None:
        if node.children:
            branch = parent.add(_tree_label(node), data=node, expand=True)
            for child in node.children:
                self._add_node(branch, child)
        else:
            parent.add_leaf(_tree_label(node), data=node)

    # -- händelser ---------------------------------------------------------

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        node = event.node.data
        detail = self.query_one("#detail", Static)
        if isinstance(node, NodeView):
            self._current_slug = node.slug
            ideas = [i for i in self._ideas if i.get("slug") == node.slug]
            issue_status, issues = open_issues_for_slug(node.slug)
            sessions = [t for t in self._transcripts if node.slug in t.slugs]
            detail.update(_detail_markup(node, ideas, issue_status, issues, sessions))
        else:
            detail.update("Välj en nod i trädet.")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "filter":
            return
        subset = filter_nodes(self._all_nodes, event.value)
        self._populate_tree(subset)

    # -- actions -----------------------------------------------------------

    def action_reload(self) -> None:
        self._all_nodes = load_nodes()
        self._ideas = load_ideas()
        self._transcripts = list_transcripts(known_slugs=set(self._all_nodes))
        filter_input = self.query_one("#filter", Input)
        subset = filter_nodes(self._all_nodes, filter_input.value)
        self._populate_tree(subset)

    def action_overview(self) -> None:
        self.push_screen(OverviewScreen())

    def action_sessions(self) -> None:
        self.push_screen(SessionsScreen(self._transcripts))

    def action_knowledge(self) -> None:
        self.push_screen(KnowledgeScreen())

    def action_agent(self) -> None:
        self.push_screen(AgentScreen(self._current_slug))

    def action_cns_sessions(self) -> None:
        self.push_screen(CnsSessionsScreen())

    def action_focus_filter(self) -> None:
        filter_input = self.query_one("#filter", Input)
        filter_input.display = True
        filter_input.focus()

    def action_clear_filter(self) -> None:
        filter_input = self.query_one("#filter", Input)
        filter_input.value = ""
        filter_input.display = False
        self._populate_tree(self._all_nodes)
        self.query_one("#tree", Tree).focus()


def main() -> None:
    CnsTuiApp().run()


if __name__ == "__main__":
    main()
