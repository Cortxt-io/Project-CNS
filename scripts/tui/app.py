"""CnsTuiApp — CNS Command Center i terminalen, byggt med textual.

Hemskärm = **Command Center** (militär doktrin, spec: cns-internal/plans/command-center-spec.md):
en rad-vy (INTE kanban, INTE fyra-block) ur `command_center.command_center_state()`. SITREP-header
(beredskap) · FRONTLINE (Missioner sorterade degraded→operational, sen hävstång; readiness-färg +
multi-fas-fronter + vem-agerar + contact report + order) · LOGISTICS (enablement) · ORDERS-footer
(hävstångs-rankad FRAGO, Enter verkställer dra-loop). Wiki-trädet bakom `w` (recon-dyk).
Körs via `python -m scripts.tui`.
"""

from __future__ import annotations

import shutil
import subprocess

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    OptionList,
    RichLog,
    Static,
    Tree,
)
from textual.widgets.option_list import Option
from textual.widgets.tree import TreeNode

from scripts.command_center import command_center_state
from scripts.tui.data import (
    KIND_COLORS,
    STAGE_COLORS,
    STATUS_COLORS,
    NodeView,
    build_forest,
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

    if ideas:
        lines.append("[bold]💡 Idéer (öppna)[/bold]")
        for i in ideas:
            text = " ".join((i.get("text", "") or "").split())
            lines.append(f"  • {text[:72]}")
        lines.append("")

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


def _link_label(link: dict | None) -> str:
    """Läsbar etikett för en sessions link ({kind, ref})."""
    if not link or not link.get("ref"):
        return ""
    kind, ref = link.get("kind"), str(link.get("ref"))
    return {"node": ref, "quest": f"quest #{ref}", "issue": f"#{ref}", "idea": f"idé {ref}"}.get(kind, ref)


def _type_tag(session_type: str | None) -> str:
    """Färgad typ-badge med ikon (tom om typ saknas). Färg/ikon ur enkällan (#41)."""
    if not session_type:
        return ""
    from scripts.session_store import type_style

    style = type_style(session_type)
    icon = style.get("icon", "⚪")
    color = style.get("rich", "dim")
    return f"{icon} [{color}]{session_type}[/{color}]"


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


# — Command Center-doktrin: readiness-färg + fas-skin (Triage→Recon→…→Debrief) —
_READINESS_MARK = {"operational": "🟢", "watch": "🟡", "degraded": "🔴", "dark": "⚪"}
_FRONT_LABEL = {
    "triage": "Triage", "discovery": "Recon", "definition": "Briefing",
    "delivery": "Assault", "review": "Hold", "retro": "Debrief",
}


def _sitrep_markup(state: dict) -> str:
    """SITREP-header: beredskaps-rollup i siffror + färskhet."""
    s = state.get("sitrep") or {}
    return (
        f"[bold]SITREP[/bold]   [green]{s.get('operational', 0)} operational[/green] · "
        f"[yellow]{s.get('watch', 0)} watch[/yellow] · [red]{s.get('degraded', 0)} degraded[/red]"
        f"   {_freshness_label(state.get('freshness'))}"
    )


def _mission_markup(m: dict) -> str:
    """En Mission (epic) som ~3 rader: readiness + namn + fronter + vem-agerar · contact · order."""
    icon = _READINESS_MARK.get(m.get("readiness"), "⚪")
    fronts = m.get("fronts") or []
    fronts_badge = (
        "  [cyan]\\[" + "|".join(_FRONT_LABEL.get(f, f) for f in fronts) + "][/cyan]" if fronts else ""
    )
    units = m.get("units", 0)
    if units:
        actor = f"  🤖×{units}"
    elif m.get("commander"):
        actor = "  [yellow]👤 väntar på dig[/yellow]"
    else:
        actor = ""
    lev = f"  [green]↑{m['leverage']}[/green]" if m.get("leverage") else ""
    title = " ".join((m.get("title", "") or "").split())[:54]
    lines = [f"{icon} [bold]{title}[/bold]{fronts_badge}{actor}{lev}"]
    if m.get("contact"):
        lines.append(f"   [red]↳ contact:[/red] {m['contact'][:72]}")
    if m.get("order"):
        lines.append(f"   [dim]↳ order:[/dim] {m['order']}")
    return "\n".join(lines)


def _frontline_markup(state: dict, show_operational: bool) -> str:
    """FRONTLINE: Missioner (redan sorterade degraded→operational, sen hävstång)."""
    missions = state.get("missions") or []
    if not show_operational:
        missions = [m for m in missions if m.get("readiness") != "operational"]
    if not missions:
        return "[dim]inga missioner på fronten (h = visa friska)[/dim]"
    return "\n\n".join(_mission_markup(m) for m in missions)


def _logistics_markup(state: dict) -> str:
    """LOGISTICS: enablement-spåret (agenturen underhåller sig själv)."""
    items = state.get("logistics") or []
    if not items:
        return "[dim]Logistics: —[/dim]"
    parts = [" ".join((e.get("summary", "") or "").split())[:40] or "(pass)" for e in items]
    return "[bold]⚙ Logistics[/bold]  [dim](försörjning)[/dim]  " + " · ".join(parts)


def _rec_link(rec: dict) -> tuple[str | None, str | None]:
    """Härled (link_kind, link_ref) ur en rekommendations ``refs`` för dra-loopen.

    Rekommendationsmotorn refererar quests som "quest #N", issues som "#N" och
    idéer som "idea-…". None när inget spår finns."""
    refs = rec.get("refs") or []
    if not refs:
        return (None, None)
    ref = str(refs[0]).strip()
    if ref.startswith("quest #"):
        return ("quest", ref.split("#", 1)[1].strip())
    if ref.startswith("idea"):
        return ("idea", ref)
    if ref.startswith("#") and ref[1:].isdigit():
        return ("issue", ref[1:])
    return (None, None)


class CommandCenterScreen(Screen):
    """Command Center — **hemskärmen** (militär doktrin, rad-vy). SITREP-header · FRONTLINE
    (Missioner sorterade degraded→operational, sen hävstång) · LOGISTICS · ORDERS-footer
    (hävstångs-rankad FRAGO: Enter verkställer dra-loop). `h` döljer friska. Wiki bakom `w`."""

    BINDINGS = [
        Binding("h", "toggle_healthy", "Dölj/visa friska"),
        Binding("w", "wiki", "Wiki"),
        Binding("s", "sessions", "Sessioner"),
        Binding("k", "knowledge", "Kunskap"),
        Binding("r", "reload", "Refresh"),
        Binding("q", "quit", "Avsluta"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._orders: list[dict] = []
        self._show_operational: bool = True

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="cc-sitrep")
        with VerticalScroll(id="cc-frontline"):
            yield Static("", id="cc-missions")
        yield Static("", id="cc-logistics")
        yield Static("[bold]🎯 ORDERS[/bold]  [dim](hävstångs-rankat nästa drag · Enter verkställer)[/dim]", id="cc-orders-label")
        yield OptionList(id="cc-orders")
        yield Static("", id="cc-status")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_view()
        if self._orders:
            self.query_one("#cc-orders", OptionList).focus()

    def _refresh_view(self, status: str = "") -> None:
        """(Om)komponera Command Center ur färsk command_center_state."""
        state = command_center_state()
        self._orders = state.get("orders") or []

        self.query_one("#cc-sitrep", Static).update(_sitrep_markup(state))
        self.query_one("#cc-missions", Static).update(_frontline_markup(state, self._show_operational))
        self.query_one("#cc-logistics", Static).update(_logistics_markup(state))

        orders = self.query_one("#cc-orders", OptionList)
        orders.clear_options()
        if self._orders:
            for i, o in enumerate(self._orders):
                tag = _type_tag(o.get("type"))
                orders.add_option(
                    Option(Text.from_markup(f"{tag + '  ' if tag else ''}{o.get('title', '')}"), id=str(i))
                )
        else:
            orders.add_option(Option("inga orders just nu", id="__none__", disabled=True))

        mode = "alla" if self._show_operational else "endast aktiva"
        self.query_one("#cc-status", Static).update(
            status or f"[dim]frontline: {mode} (h växlar) · Enter verkställ order · w wiki · s sessioner · r refresh[/dim]"
        )

    def action_toggle_healthy(self) -> None:
        self._show_operational = not self._show_operational
        self._refresh_view()

    def action_reload(self) -> None:
        self._refresh_view(status="[dim]↻ refresh[/dim]")

    def action_wiki(self) -> None:
        self.app.push_screen(WikiScreen())

    def action_sessions(self) -> None:
        self.app.push_screen(SessionsScreen(self.app.transcripts))

    def action_knowledge(self) -> None:
        self.app.push_screen(KnowledgeScreen())

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Verkställ ORDER (FRAGO): starta passet (markör + pass + fokus), idempotent."""
        opt_id = event.option.id
        if not opt_id or opt_id == "__none__":
            return
        try:
            order = self._orders[int(opt_id)]
        except (ValueError, TypeError, IndexError):
            return
        from scripts.session_store import find_running, set_active, set_focus, start_session

        rtype = order.get("type")
        title = order.get("title", "")
        link_kind, link_ref = _rec_link(order)
        try:
            existing = find_running(rtype, link_ref)
            set_active(rtype)
            if link_kind:
                set_focus(link_kind, link_ref)
            ref_txt = f" · [cyan]{_link_label({'kind': link_kind, 'ref': link_ref})}[/cyan]" if link_ref else ""
            if existing:
                self.notify(f"{rtype}-pass redan igång — återupptog fokus", title="Command Center")
                self._refresh_view(
                    status=f"[bold yellow]↻ Redan i fält:[/bold yellow] {_type_tag(rtype)}{ref_txt}"
                )
                return
            start_session(link_kind=link_kind, link_ref=link_ref, summary=title, session_type=rtype)
            self.notify(f"Order verkställd: {rtype}", title="Command Center")
            self._refresh_view(
                status=f"[bold green]✅ Order verkställd:[/bold green] {_type_tag(rtype)}{ref_txt}  [dim]— jobba i fliken[/dim]"
            )
        except Exception as exc:  # degradera synligt, krascha inte vyn
            self.notify(f"Kunde inte verkställa: {exc}", severity="error", title="Command Center")
            self._refresh_view(status=f"[red]⚠ kunde inte verkställa order: {exc}[/red]")


class WikiScreen(Screen):
    """Wiki-överblick (sekundär yta, tangent w). Vänster: part_of-nästlat träd färgat på
    stage. Höger: detaljpanel för vald nod. `/` filtrerar, `c` frågar Claude, esc/w tillbaka."""

    BINDINGS = [
        Binding("escape", "back", "Tillbaka"),
        Binding("w", "back", "Tillbaka"),
        Binding("r", "reload", "Ladda om"),
        Binding("c", "agent", "Fråga Claude"),
        Binding("s", "sessions", "Sessioner"),
        Binding("k", "knowledge", "Kunskap"),
        Binding("slash", "focus_filter", "Filter"),
        Binding("q", "quit", "Avsluta"),
    ]

    def __init__(self) -> None:
        super().__init__()
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
        self._populate_tree(self.app.all_nodes)

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

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        node = event.node.data
        # Trädet auto-markerar sin första nod medan det fylls i (on_mount), vilket kan
        # avfyra denna händelse innan detaljpanelen monterats. Hoppa tyst då.
        try:
            detail = self.query_one("#detail", Static)
        except NoMatches:
            return
        if isinstance(node, NodeView):
            self._current_slug = node.slug
            ideas = [i for i in self.app.ideas if i.get("slug") == node.slug]
            issue_status, issues = open_issues_for_slug(node.slug)
            detail.update(_detail_markup(node, ideas, issue_status, issues))
        else:
            detail.update("Välj en nod i trädet.")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "filter":
            return
        subset = filter_nodes(self.app.all_nodes, event.value)
        self._populate_tree(subset)

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_reload(self) -> None:
        self.app.reload_data()
        filter_input = self.query_one("#filter", Input)
        subset = filter_nodes(self.app.all_nodes, filter_input.value)
        self._populate_tree(subset)

    def action_sessions(self) -> None:
        self.app.push_screen(SessionsScreen(self.app.transcripts))

    def action_knowledge(self) -> None:
        self.app.push_screen(KnowledgeScreen())

    def action_agent(self) -> None:
        self.app.push_screen(AgentScreen(self._current_slug))

    def action_focus_filter(self) -> None:
        filter_input = self.query_one("#filter", Input)
        filter_input.display = True
        filter_input.focus()


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
    type_color = {"feedback": "yellow", "project": "green", "reference": "cyan", "user": "magenta"}
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
    """CNS Control Tower. Hemskärm = lägesbilden (CockpitScreen); wiki bakom `w`.

    Appen äger delad data (noder/idéer/transkript) som båda skärmarna läser, så en
    reload på ett ställe slår igenom överallt."""

    CSS_PATH = "styles.tcss"
    TITLE = "CNS Control Tower"

    def __init__(self) -> None:
        super().__init__()
        self.all_nodes: dict[str, NodeView] = {}
        self.ideas: list[dict] = []
        self.transcripts: list[Transcript] = []

    def get_default_screen(self) -> Screen:
        return CommandCenterScreen()

    def on_mount(self) -> None:
        self.reload_data()

    def reload_data(self) -> None:
        """Läs om delad data (noder/idéer/transkript) från datalagret."""
        self.all_nodes = load_nodes()
        self.ideas = load_ideas()
        self.transcripts = list_transcripts()


def main() -> None:
    CnsTuiApp().run()


if __name__ == "__main__":
    main()
