"""CnsTuiApp — interaktiv portföljöverblick byggd med textual.

Vänster: part_of-nästlat träd, färgat på stage. Höger: detaljpanel för vald
nod (kind/stage/status/summary/feeds/depends_on). `/` filtrerar på stage/status.
Körs via `python -m scripts.tui`.
"""

from __future__ import annotations

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Static, Tree
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
from scripts.tui.sources import git_branches, load_ideas, open_issues_for_slug


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
    """Rich-markup för detaljpanelen, inkl. länkade idéer och öppna issues."""
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


def _overview_markup() -> str:
    """Portföljbred lägesbild: aktiva git-spår + öppna idéer.

    Syftet är kollisionssynlighet — flera lokala feature-brancher = parallella
    spår som kan krocka (precis det som blindade oss idag).
    """
    lines: list[str] = ["[bold]Aktiva git-spår[/bold]", ""]
    branches = git_branches()
    local = [b for b in branches if not b.remote]
    remote_names = {b.name.split("/", 1)[-1] for b in branches if b.remote}

    if not local:
        lines.append("[dim](kunde inte läsa git)[/dim]")
    for b in local:
        marker = "[green]▶[/green]" if b.current else " "
        pushed = "[dim](pushad)[/dim]" if b.name in remote_names else "[yellow](endast lokal)[/yellow]"
        feature = "" if b.name in ("main", "master") else "  [cyan]← spår[/cyan]"
        lines.append(f"{marker} {b.name} {pushed}{feature}")

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
    lines.append("[dim]esc / o stänger[/dim]")
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


class CnsTuiApp(App):
    """Glanceable portföljöverblick i terminalen."""

    CSS_PATH = "styles.tcss"
    TITLE = "CNS Portföljöverblick"

    BINDINGS = [
        Binding("q", "quit", "Avsluta"),
        Binding("r", "reload", "Ladda om"),
        Binding("o", "overview", "Översikt"),
        Binding("slash", "focus_filter", "Filter"),
        Binding("escape", "clear_filter", "Rensa filter", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._all_nodes: dict[str, NodeView] = {}
        self._ideas: list[dict] = []

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
        filter_input = self.query_one("#filter", Input)
        subset = filter_nodes(self._all_nodes, filter_input.value)
        self._populate_tree(subset)

    def action_overview(self) -> None:
        self.push_screen(OverviewScreen())

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
