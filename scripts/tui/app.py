"""CnsTuiApp — interaktiv wiki-överblick byggd med textual.

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
    cockpit_state,
    filter_nodes,
    load_nodes,
)
from scripts.tui.sources import (
    Transcript,
    list_transcripts,
    load_ideas,
    load_memory_cards,
    load_skills,
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
) -> str:
    """Rich-markup för detaljpanelen, inkl. länkade idéer och issues."""
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

    if node.tags:
        lines.append("")
        lines.append("[dim]tags: " + ", ".join(node.tags) + "[/dim]")

    return "\n".join(lines).rstrip()


# Sessionstyp → rich-färg (speglar recommend.SESSION_ICONS/SESSION_COLORS, men
# rich-färgnamn i stället för ANSI-koder så TUI och statusrad ser likadana ut).
_TYPE_RICH: dict[str, str] = {
    "discovery": "magenta",
    "definition": "orange3",
    "delivery": "green",
    "triage": "yellow",
    "review": "blue",
    "enablement": "cyan",
    "retro": "grey50",
}
_TYPE_ICON: dict[str, str] = {
    "discovery": "🟣",
    "definition": "🟠",
    "delivery": "🟢",
    "triage": "🟡",
    "review": "🔵",
}


def _link_label(link: dict | None) -> str:
    """Läsbar etikett för en sessions link ({kind, ref})."""
    if not link or not link.get("ref"):
        return ""
    kind, ref = link.get("kind"), str(link.get("ref"))
    return {"node": ref, "quest": f"quest #{ref}", "issue": f"#{ref}", "idea": f"idé {ref}"}.get(kind, ref)


def _type_tag(session_type: str | None) -> str:
    """Färgad typ-badge med ikon (tom om typ saknas)."""
    if not session_type:
        return ""
    icon = _TYPE_ICON.get(session_type, "⚪")
    color = _TYPE_RICH.get(session_type, "dim")
    return f"{icon} [{color}]{session_type}[/{color}]"


def _short_when(iso: str | None) -> str:
    return (iso or "")[:16].replace("T", " ")


def _human_elapsed(seconds: float | None) -> str:
    if not seconds or seconds < 0:
        return ""
    mins = int(seconds // 60)
    if mins < 60:
        return f"{mins} min"
    return f"{mins // 60}h {mins % 60}m"


def _freshness_label(freshness: dict | None) -> str:
    """Synlig färskhetsmarkör — lokal data kan driva från GitHub-sanningen."""
    f = freshness or {}
    if not f.get("reachable"):
        return "[dim]lokal · GitHub onåbar[/dim]"
    age = f.get("age_s")
    if age is None:
        return "[dim]lokal[/dim]"
    mins = int(age // 60)
    when = "nyss" if mins < 1 else f"{mins} min sen"
    return f"[dim]färsk · {when}[/dim]"


def _overview_markup() -> str:
    """Orienteringsytan (idea-7548a67a / epic #8): EN läsning, ingen hopsättning.

    Fyra block ur ``cockpit_state()`` — var du slutade · igång · härnäst · i fokus
    — så lägesbilden där man står inte behöver pusslas ihop ur flera datalager.
    """
    state = cockpit_state()
    lines: list[str] = [f"[bold]📍 Lägesbild[/bold]   {_freshness_label(state.get('freshness'))}", ""]

    # — Var du slutade —
    lines.append("[bold]Var du slutade[/bold]")
    last = state.get("last_done")
    if not last:
        lines.append("  [dim]inget avslutat pass än[/dim]")
    else:
        tag = _type_tag(last.get("type"))
        link = _link_label(last.get("link"))
        meta = "  [dim]→ " + " · ".join(x for x in (link, _short_when(last.get("when"))) if x) + "[/dim]"
        summ = " ".join((last.get("summary", "") or "").split())[:68] or "[dim](utan sammanfattning)[/dim]"
        lines.append(f"  {tag + '  ' if tag else ''}{summ}{meta}")
    lines.append("")

    # — Igång —
    active = state.get("active") or {}
    active_tag = f"  [dim](aktiv: {active.get('type')})[/dim]" if active.get("type") else ""
    lines.append(f"[bold]Igång[/bold]{active_tag}")
    running = state.get("running") or []
    if not running:
        lines.append("  [dim]inget pass igång[/dim]")
    for r in running:
        tag = _type_tag(r.get("type"))
        elapsed = _human_elapsed(r.get("elapsed"))
        phantom = "  [red]⚠ fantom[/red]" if r.get("phantom") else ""
        summ = " ".join((r.get("summary", "") or "").split())[:56] or _link_label(r.get("link")) or "(pass)"
        age = f"  [dim]({elapsed})[/dim]" if elapsed else ""
        lines.append(f"  {tag + '  ' if tag else ''}{summ}{age}{phantom}")
    lines.append("")

    # — Härnäst —
    lines.append("[bold]Härnäst[/bold]")
    recs = state.get("recommendations") or []
    if not recs:
        lines.append("  [dim]inga rekommendationer just nu[/dim]")
    for rec in recs:
        tag = _type_tag(rec.get("type"))
        title = rec.get("title", "")
        lines.append(f"  {tag + '  ' if tag else ''}{title}")
        if rec.get("motivation"):
            lines.append(f"     [dim]{rec['motivation'][:80]}[/dim]")
    lines.append("")

    # — I fokus —
    focus = state.get("focus")
    if not focus:
        lines.append("[bold]I fokus[/bold]")
        lines.append("  [dim]ingen fokus satt — `cns session set-focus <kind> <ref>`[/dim]")
    else:
        ref = focus.get("ref")
        kind = focus.get("kind") or ""
        lines.append(f"[bold]I fokus[/bold]   📍 [cyan]{ref}[/cyan] [dim]{kind}[/dim]")
        issues = focus.get("issues") or []
        if not issues:
            lines.append("  [dim]inga öppna issues[/dim]")
        for it in issues[:6]:
            num = it.get("number") or it.get("id") or "?"
            title = it.get("title", "")
            lines.append(f"  🔧 #{num} {title[:56]}")

    lines.append("")
    lines.append("[dim]esc / o stänger · s sessioner · k kunskap[/dim]")
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
    """Glanceable wiki-överblick i terminalen."""

    CSS_PATH = "styles.tcss"
    TITLE = "CNS Wiki"

    BINDINGS = [
        Binding("q", "quit", "Avsluta"),
        Binding("r", "reload", "Ladda om"),
        Binding("o", "overview", "Översikt"),
        Binding("s", "sessions", "Sessioner"),
        Binding("k", "knowledge", "Kunskap"),
        Binding("c", "agent", "Fråga Claude"),
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
            yield Tree("Wiki", id="tree")
            with Vertical(id="detail-pane"):
                yield Input(placeholder="Filtrera på stage/status…", id="filter")
                with VerticalScroll(id="detail-scroll"):
                    yield Static("Välj en nod i trädet.", id="detail")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#filter", Input).display = False
        self._all_nodes = load_nodes()
        self._ideas = load_ideas()
        self._transcripts = list_transcripts()
        self._populate_tree(self._all_nodes)
        # Orienteringsytan först (epic #8): lägesbilden öppnas vid start så man
        # ser var man står direkt; esc/o tar fram nodträdet. Deferred så skärmen
        # hinner monteras innan modalen pushas.
        self.call_after_refresh(self.action_overview)

    # -- trädbygge ---------------------------------------------------------

    def _populate_tree(self, nodes: dict[str, NodeView]) -> None:
        tree = self.query_one("#tree", Tree)
        tree.clear()
        tree.root.expand()
        roots = build_forest(nodes)
        if not roots:
            tree.root.set_label("Inga noder matchar")
            return
        tree.root.set_label(f"Wiki ({len(nodes)} noder)")
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
            detail.update(_detail_markup(node, ideas, issue_status, issues))
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
        self._transcripts = list_transcripts()
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
