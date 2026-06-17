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
import threading

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


def _badges_markup(state: dict) -> str:
    """C2-badges: dispatch-läge · väntande beslut · FOB. Placeholders tills wirat (o/c/f öppnar)."""
    cmd = state.get("command") or {}
    dispatch = cmd.get("dispatch", "IDLE")
    decisions = cmd.get("decisions", 0)
    fobs = cmd.get("fobs", 0)
    dec = f"[red]⚖ {decisions} beslut[/red]" if decisions else "[dim]⚖ 0 beslut[/dim]"
    return (
        f"[dim]🎖 War Room:[/dim] {dispatch}  ·  {dec}  ·  [dim]🏕 {fobs} FOB[/dim]"
        f"   [dim](o war room · c council · f fob · : radio)[/dim]"
    )


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
        Binding("o", "war_room", "War Room"),
        Binding("c", "council", "Council"),
        Binding("f", "fob", "FOB"),
        Binding("colon", "radio", "Radio"),
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
        self._missions: list[dict] = []
        self._show_operational: bool = True

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="cc-sitrep")
        yield Static("", id="cc-badges")  # dispatch · beslut · FOB (o/c/f/: öppnar lägena)
        yield OptionList(id="cc-missions")  # FRONTLINE — navigerbar (↑↓), Enter = recon-brief
        yield Static("", id="cc-logistics")
        yield Static("[bold]🎯 ORDERS[/bold]  [dim](Tab hit · Enter verkställer)[/dim]", id="cc-orders-label")
        yield OptionList(id="cc-orders")
        yield Static("", id="cc-status")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_view()
        # Fokusera FRONTLINE primärt (huvudytan); Tab växlar till ORDERS.
        self.query_one("#cc-missions", OptionList).focus()

    def _refresh_view(self, status: str = "") -> None:
        """(Om)komponera Command Center ur färsk command_center_state."""
        state = command_center_state()
        self._orders = state.get("orders") or []

        self.query_one("#cc-sitrep", Static).update(_sitrep_markup(state))
        self.query_one("#cc-badges", Static).update(_badges_markup(state))

        # FRONTLINE som navigerbar lista (en option per Mission).
        missions = state.get("missions") or []
        if not self._show_operational:
            missions = [m for m in missions if m.get("readiness") != "operational"]
        self._missions = missions
        front = self.query_one("#cc-missions", OptionList)
        front.clear_options()
        if missions:
            for m in missions:
                front.add_option(Option(Text.from_markup(_mission_markup(m)), id=str(m["number"])))
            front.highlighted = 0
        else:
            front.add_option(Option("inga missioner på fronten (h = visa friska)", id="__none__", disabled=True))

        self.query_one("#cc-logistics", Static).update(_logistics_markup(state))

        orders = self.query_one("#cc-orders", OptionList)
        orders.clear_options()
        if self._orders:
            for i, o in enumerate(self._orders):
                tag = _type_tag(o.get("type"))
                orders.add_option(
                    Option(Text.from_markup(f"{tag + '  ' if tag else ''}{o.get('title', '')}"), id=str(i))
                )
            # Markera första ordern så Enter direkt verkställer (annars highlighted=None → inget händer).
            orders.highlighted = 0
        else:
            orders.add_option(Option("inga orders just nu", id="__none__", disabled=True))

        mode = "alla" if self._show_operational else "endast aktiva"
        self.query_one("#cc-status", Static).update(
            status or f"[dim]↑↓ navigera · Enter recon-brief · Tab→orders · h {mode} · w wiki · r refresh · q[/dim]"
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

    def action_war_room(self) -> None:
        self.app.push_screen(WarRoomScreen())

    def action_council(self) -> None:
        self.app.push_screen(CouncilScreen())

    def action_fob(self) -> None:
        self.app.push_screen(FOBScreen())

    def action_radio(self) -> None:
        self.app.push_screen(RadioScreen())

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Enter: på FRONTLINE → recon-brief (mission-detalj); på ORDERS → verkställ FRAGO."""
        opt_id = event.option.id
        if not opt_id or opt_id == "__none__":
            return

        # FRONTLINE: dyk in i missionen (progressive disclosure).
        if event.option_list.id == "cc-missions":
            mission = next((m for m in self._missions if str(m["number"]) == opt_id), None)
            if mission:
                self.app.push_screen(MissionDetailScreen(mission))
            return

        # ORDERS: verkställ FRAGO.
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


def _mission_detail_markup(m: dict) -> str:
    """Recon-brief för en Mission: readiness, fronter, vem-agerar, contact, order, hävstång."""
    icon = _READINESS_MARK.get(m.get("readiness"), "⚪")
    rcolor = {"operational": "green", "watch": "yellow", "degraded": "red", "dark": "dim"}.get(m.get("readiness"), "dim")
    lines = [
        f"{icon} [bold]{m.get('title', '')}[/bold]   [dim]Mission #{m.get('number')}[/dim]",
        "",
        f"[bold]Readiness:[/bold] [{rcolor}]{m.get('readiness')}[/{rcolor}]",
    ]
    fronts = m.get("fronts") or []
    fronts_txt = " · ".join(_FRONT_LABEL.get(f, f) for f in fronts) if fronts else "[dim]inga aktiva fronter[/dim]"
    lines.append(f"[bold]Aktiva fronter:[/bold] {fronts_txt}")
    if m.get("units"):
        lines.append(f"[bold]Enheter i fält:[/bold] 🤖×{m['units']}")
    elif m.get("commander"):
        lines.append("[bold]Chain of command:[/bold] [yellow]👤 väntar på dig (Commander)[/yellow]")
    lines.append(f"[bold]Hävstång:[/bold] låser upp {m.get('leverage', 0)} nedströms-objekt")
    lines.append(f"[bold]Öppna objectives:[/bold] {m.get('open_objectives', 0)}")
    if m.get("contact"):
        lines.append("")
        lines.append(f"[red]⚠ Contact report:[/red] {m['contact']}")
    if m.get("order"):
        lines.append("")
        lines.append(f"[bold cyan]Order:[/bold cyan] {m['order']}")
    lines.append("")
    lines.append("[dim]esc stänger · (objectives-detalj kräver GitHub-token)[/dim]")
    return "\n".join(lines)


class MissionDetailScreen(ModalScreen):
    """Recon-brief för en Mission (drill-down från FRONTLINE). esc stänger."""

    BINDINGS = [Binding("escape", "dismiss", "Stäng"), Binding("q", "dismiss", "Stäng")]

    def __init__(self, mission: dict) -> None:
        super().__init__()
        self._mission = mission

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="mission-box"):
            yield Static(_mission_detail_markup(self._mission), id="mission-detail")


# ── C2-lägen (egna Screens, ej paneler på hemmet — research-IA). Placeholders tills wirade. ──

class _ModeScreen(ModalScreen):
    """Gemensam bas för C2-lägena: titel + placeholder-text, esc stänger."""

    _TITLE = ""
    _BODY = ""

    BINDINGS = [Binding("escape", "dismiss", "Stäng"), Binding("q", "dismiss", "Stäng")]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="mode-box"):
            yield Static(f"{self._TITLE}\n\n{self._BODY}\n\n[dim]esc stänger[/dim]", id="mode-detail")


class WarRoomScreen(ModalScreen):
    """War Room — dispatch & autonomi (tangent o). Välj Rules of Engagement, Enter = Engage:
    startar ETT gated dispatch-crawl i ett NYTT fönster (kör synligt, gateas per steg där, fryser
    inte TUI:t). dispatch.main kör ett crawl per anrop; default interaktiv y/N-grind."""

    BINDINGS = [Binding("escape", "dismiss", "Stäng"), Binding("q", "dismiss", "Stäng")]

    # (id, label, beskrivning, dispatch-flaggor)
    _ROE = [
        ("recon", "🔭 Recon — read-first", "Föreslår, skriver inget. Säkrast.", ""),
        ("assault", "⚔ Assault — write", "Worktree + draft-PR. Gateas per steg (y/N).", "--write"),
        ("autonomy", "🎲 Autonomy — self-merge", "Self-mergar LÅGRISK (kräver write). Gateas.", "--write --autonomy"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._busy = False

    def compose(self) -> ComposeResult:
        with Vertical(id="war-box"):
            yield Static(
                "[bold]🎖 WAR ROOM[/bold]  [dim]— dispatch & autonomi · körs INLINE (inga fönster)[/dim]\n"
                "[bold]Rules of Engagement[/bold]  [dim](↑↓ välj · Enter = Engage ett crawl här)[/dim]",
                id="war-head",
            )
            yield OptionList(
                *[Option(Text.from_markup(f"{lbl}  [dim]— {desc}[/dim]"), id=rid) for rid, lbl, desc, _ in self._ROE],
                id="roe-list",
            )
            yield RichLog(id="war-log", wrap=True, markup=True)
            yield Static("[dim]Mutation gateas som dialog här (y/n) · esc stänger[/dim]", id="war-status")

    def on_mount(self) -> None:
        ol = self.query_one("#roe-list", OptionList)
        ol.focus()
        ol.highlighted = 0

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if self._busy:
            return
        roe = event.option.id
        if roe not in {rid for rid, *_ in self._ROE}:
            return
        self._busy = True
        log = self.query_one("#war-log", RichLog)
        log.write(f"[bold]🎖 Engaging {roe} (inline)…[/bold]  [dim](kan ta en stund — kör ett pass)[/dim]")
        self.run_worker(lambda: self._run_crawl(roe), thread=True, exclusive=True, name="dispatch")

    def _log(self, text: str) -> None:
        self.query_one("#war-log", RichLog).write(text)

    def _approver(self, roe: str):
        """Recon (read-first): auto-ja (muterar inget). Annars: poppa confirm-dialog i TUI:t."""
        def approve(action: str, ctx: dict) -> bool:
            if roe == "recon":
                return True
            ev = threading.Event()
            box: dict = {}

            def ask() -> None:
                self.app.push_screen(ConfirmScreen(action, ctx), lambda v: (box.__setitem__("v", v), ev.set()))

            self.app.call_from_thread(ask)
            ev.wait()
            return bool(box.get("v"))

        return approve

    def _run_crawl(self, roe: str) -> None:
        """Körs i worker-tråd. Kör ETT crawl via dispatch; loggar steg + resultat i TUI:t."""
        import os

        try:
            from scripts import dispatch, issues_client

            write = roe in ("assault", "autonomy")
            autonomy = roe == "autonomy"
            owner = os.getenv("CNS_AGENT_OWNER") or "command-center"
            res = dispatch.crawl_once(
                owner=owner,
                candidates_fn=lambda: issues_client.list_issues(state="open"),
                closed_numbers_fn=lambda: {int(i["number"]) for i in issues_client.list_issues(state="closed")},
                approve=self._approver(roe),
                worktree_fn=dispatch.default_worktree_fn if write else None,
                open_pr_fn=dispatch.build_open_pr_fn() if write else None,
                autonomy=autonomy and write,
                merge_fn=dispatch.build_merge_fn() if (autonomy and write) else None,
            )
            for step in getattr(res, "log", []) or []:
                self.app.call_from_thread(self._log, f"  [dim]· {step}[/dim]")
            color = {"ran": "green", "no-work": "dim", "blocked": "yellow", "denied": "yellow", "escalated": "yellow"}.get(res.status, "red")
            self.app.call_from_thread(self._log, f"[bold {color}]→ {res.status}[/bold {color}]: {res.detail or ''}")
        except Exception as exc:
            self.app.call_from_thread(self._log, f"[red]⚠ kunde inte köra: {type(exc).__name__}: {exc}[/red]")
        finally:
            self.app.call_from_thread(setattr, self, "_busy", False)


class ConfirmScreen(ModalScreen):
    """Godkännande-dialog för ett muterande dispatch-steg (human-in-the-loop, i TUI:t)."""

    BINDINGS = [
        Binding("y", "yes", "Ja"),
        Binding("j", "yes", "Ja"),
        Binding("n", "no", "Nej"),
        Binding("escape", "no", "Nej"),
    ]

    def __init__(self, action: str, ctx: dict) -> None:
        super().__init__()
        self._text = {
            "claim": f"Claima issue #{ctx.get('issue')} ({ctx.get('type')})?",
            "run_pass": f"Kör pass på #{ctx.get('issue')} som '{ctx.get('agent') or 'generisk'}'?",
            "open_pr": f"Öppna DRAFT-PR för #{ctx.get('issue')}?",
            "merge": f"Self-merga LÅGRISK-PR #{ctx.get('pr')} (#{ctx.get('issue')})?",
        }.get(action, f"Godkänn '{action}'?")

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Static(f"[bold yellow]⚖ Beslut[/bold yellow]\n\n{self._text}\n\n[bold][y][/bold] ja  ·  [bold][n][/bold] nej")

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


class CouncilScreen(ModalScreen):
    """Council — beslutskö (tangent c). Väntande beslut = öppna PR:er agenturen producerat. Ta beslut
    DIREKT här: a=Approve (merge, ready PR) · x=Reject (close) · o=öppna i browser · Enter=öppna.
    Muterande beslut kräver två tryck (bekräfta). esc stänger."""

    BINDINGS = [
        Binding("escape", "dismiss", "Stäng"),
        Binding("q", "dismiss", "Stäng"),
        Binding("a", "approve", "Approve (merge)"),
        Binding("x", "reject", "Reject (close)"),
        Binding("o", "open_pr", "Öppna PR"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._decisions: list[dict] = []
        self._pending: tuple[str, int] | None = None  # (action, pr-number) för två-tryck-bekräftelse

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="council-box"):
            yield Static("[bold]⚖ COUNCIL[/bold]  [dim]— command decisions (väntande PR:er)[/dim]\n", id="council-head")
            yield OptionList(id="council-list")
            yield Static("", id="council-status")

    def on_mount(self) -> None:
        from scripts.command_center import council_decisions

        self._decisions = council_decisions()
        self._load("[dim]↑↓ navigera · a approve(merge) · x reject(close) · o browser · esc stäng[/dim]")
        if self._decisions:
            self.query_one("#council-list", OptionList).focus()

    def _load(self, status: str = "") -> None:
        ol = self.query_one("#council-list", OptionList)
        ol.clear_options()
        if self._decisions:
            for d in self._decisions:
                tag = "[yellow]draft[/yellow]" if d.get("draft") else "[green]ready[/green]"
                title = " ".join((d.get("title", "") or "").split())[:46]
                ol.add_option(
                    Option(
                        Text.from_markup(
                            f"{tag}  [bold]#{d.get('number')}[/bold] {title}  [dim]· {d.get('author', '')} · {d.get('head', '')}[/dim]"
                        ),
                        id=str(d.get("number")),
                    )
                )
            ol.highlighted = 0
        else:
            ol.add_option(Option("inga väntande beslut (inga öppna PR:er, el. token saknas)", id="__none__", disabled=True))
        if status:
            self.query_one("#council-status", Static).update(status)

    def _current(self) -> dict | None:
        ol = self.query_one("#council-list", OptionList)
        if ol.highlighted is None:
            return None
        oid = ol.get_option_at_index(ol.highlighted).id
        return next((x for x in self._decisions if str(x.get("number")) == oid), None)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.action_open_pr()

    def action_open_pr(self) -> None:
        d = self._current()
        if d and d.get("url"):
            import webbrowser

            webbrowser.open(d["url"])
            self.query_one("#council-status", Static).update(f"[green]↗ öppnade PR #{d['number']} i browser[/green]")

    def action_approve(self) -> None:
        d = self._current()
        if not d:
            return
        num = d["number"]
        if d.get("draft"):
            self._pending = None
            self.query_one("#council-status", Static).update(
                f"[yellow]⚠ #{num} är draft — kan ej mergas. Tryck o för att markera ready i browsern.[/yellow]"
            )
            return
        if self._pending == ("merge", num):
            self._execute("merge", d)
        else:
            self._pending = ("merge", num)
            self.query_one("#council-status", Static).update(f"[bold yellow]⚠ Bekräfta MERGE av PR #{num} — tryck a igen[/bold yellow]")

    def action_reject(self) -> None:
        d = self._current()
        if not d:
            return
        num = d["number"]
        if self._pending == ("close", num):
            self._execute("close", d)
        else:
            self._pending = ("close", num)
            self.query_one("#council-status", Static).update(f"[bold red]⚠ Bekräfta CLOSE av PR #{num} — tryck x igen[/bold red]")

    def _execute(self, action: str, d: dict) -> None:
        from scripts import prs_client

        num = d["number"]
        self._pending = None
        try:
            if action == "merge":
                prs_client.merge_pr(num)
                msg = f"[bold green]✅ Mergade PR #{num}[/bold green]"
            else:
                prs_client.close_pr(num)
                msg = f"[bold]🗙 Stängde PR #{num}[/bold]"
            self._decisions = [x for x in self._decisions if x.get("number") != num]
            self._load(msg)
            self.app.notify(f"Council: {action} #{num}", title="Command Center")
        except Exception as exc:
            self.query_one("#council-status", Static).update(f"[red]⚠ {action} #{num} misslyckades: {exc}[/red]")


class FOBScreen(_ModeScreen):
    """FOB — off-host exekveringsbaser / container-sandlådor (tangent f). Placeholder."""

    _TITLE = "[bold]🏕 FOB[/bold]  [dim]— forward operating bases (exekvering)[/dim]"
    _BODY = (
        "[yellow]Inga FOB provisionerade.[/yellow] Här bor den off-host container-exekveringen:\n"
        "  • Sandlådor: kapacitet (CPU/mem) · agenter i fält · uptime\n"
        "  • Drain / Restart / logs\n\n"
        "[dim]Kopplas mot Docker/microVM-spåret (FOB ≠ Command Center: exekvering vs orientering).[/dim]"
    )


class RadioScreen(ModalScreen):
    """Radio — command palette (tangent `:`). Skalbar ingång till alla lägen/kommandon."""

    BINDINGS = [Binding("escape", "dismiss", "Stäng")]

    _COMMANDS = [
        ("war_room", "🎖 War Room — dispatch & autonomi"),
        ("council", "⚖ Council — beslut / approvals"),
        ("fob", "🏕 FOB — exekveringsbaser"),
        ("wiki", "📖 Wiki — nod-/struktur-dyk"),
        ("sessions", "🗂 Sessioner"),
        ("refresh", "↻ Refresh"),
        ("quit", "⏻ Avsluta"),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="radio-box"):
            yield Static("[bold]📻 RADIO[/bold]  [dim]— issue command · Enter[/dim]\n", id="radio-head")
            yield OptionList(*[Option(label, id=cid) for cid, label in self._COMMANDS], id="radio-list")

    def on_mount(self) -> None:
        ol = self.query_one("#radio-list", OptionList)
        ol.focus()
        ol.highlighted = 0

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        cmd = event.option.id
        self.dismiss()
        if cmd == "war_room":
            self.app.push_screen(WarRoomScreen())
        elif cmd == "council":
            self.app.push_screen(CouncilScreen())
        elif cmd == "fob":
            self.app.push_screen(FOBScreen())
        elif cmd == "wiki":
            self.app.push_screen(WikiScreen())
        elif cmd == "sessions":
            self.app.push_screen(SessionsScreen(self.app.transcripts))
        elif cmd == "refresh":
            scr = self.app.screen
            if isinstance(scr, CommandCenterScreen):
                scr._refresh_view(status="[dim]↻ refresh (radio)[/dim]")
        elif cmd == "quit":
            self.app.exit()


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
