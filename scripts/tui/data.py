"""Datalager-adapter för CNS-TUI:t.

Rena funktioner utan textual-import — testbara fristående. Läser noder via
det stabila datalagret (`scripts.md_parser.read_all_nodes`) och bygger en
part_of-nästlad skog. Ingen sidoeffekt (till skillnad från `export_json`,
som alltid skriver en fil).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scripts.md_parser import read_all_nodes

# Färgkodning — återanvänds av träd-labels och detaljpanel.
# Speglar färgkartorna i cns.py:s cmd_list så TUI och CLI ser likadana ut.
STAGE_COLORS: dict[str, str] = {
    "idea": "dim",
    "building": "yellow",
    "working": "green",
    "maturing": "bold green",
}

STATUS_COLORS: dict[str, str] = {
    "idea": "dim",
    "early_mvp": "yellow",
    "mvp": "green",
    "live": "bold green",
    "shelved": "dim red",
}

KIND_COLORS: dict[str, str] = {
    "framework": "bold magenta",
    "system": "cyan",
    "component": "green",
}


@dataclass
class NodeView:
    """Platt vy av en nod, plus barn-länkar som build_forest fyller i."""

    slug: str
    title: str
    kind: str
    stage: str
    status: str
    part_of: str
    feeds: list[str]
    depends_on: list[str]
    summary: str
    tags: list[str]
    children: list["NodeView"] = field(default_factory=list)


def _as_list(value: Any) -> list[str]:
    """Normalisera ett frontmatter-fält till en lista av strängar."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v]
    return [str(value)]


def _node_from_meta(meta: dict[str, Any]) -> NodeView:
    return NodeView(
        slug=str(meta.get("slug", "") or ""),
        title=str(meta.get("title", "") or ""),
        kind=str(meta.get("kind", "") or ""),
        stage=str(meta.get("stage", "") or ""),
        status=str(meta.get("status", "") or ""),
        part_of=str(meta.get("part_of", "") or ""),
        feeds=_as_list(meta.get("feeds")),
        depends_on=_as_list(meta.get("depends_on")),
        summary=str(meta.get("summary", "") or ""),
        tags=_as_list(meta.get("tags")),
    )


def load_nodes() -> dict[str, NodeView]:
    """Läs alla noder via read_all_nodes() → dict slug -> NodeView (platt)."""
    nodes: dict[str, NodeView] = {}
    for meta, _sections in read_all_nodes():
        node = _node_from_meta(meta)
        if not node.slug:
            continue
        nodes[node.slug] = node
    return nodes


def build_forest(nodes: dict[str, NodeView]) -> list[NodeView]:
    """Bygg part_of-nästling till en lista rot-noder.

    Rot = nod vars part_of är tom ELLER pekar på en slug som inte finns
    (hemlös → rot). Skyddar mot self-parent och cykler så en trasig
    part_of-kedja inte ger oändlig loop eller försvunna noder.

    Muterar `children` på NodeView-objekten i `nodes` — anropa load_nodes()
    på nytt vid reload så listorna inte dubbleras.
    """
    # Nollställ barn-länkar (idempotent om samma objekt återanvänds).
    for node in nodes.values():
        node.children = []

    roots: list[NodeView] = []
    for slug, node in nodes.items():
        parent_slug = node.part_of
        # Hemlös eller self-parent → behandla som rot.
        if not parent_slug or parent_slug == slug or parent_slug not in nodes:
            roots.append(node)
            continue
        if _creates_cycle(nodes, child_slug=slug, parent_slug=parent_slug):
            # Trasig cyklisk part_of — bryt loopen, gör noden till rot.
            roots.append(node)
            continue
        nodes[parent_slug].children.append(node)

    _sort_recursive(roots)
    return roots


def _creates_cycle(
    nodes: dict[str, NodeView], child_slug: str, parent_slug: str
) -> bool:
    """True om att hänga child under parent skulle sluta i en cykel.

    Dvs om child redan är en (transitiv) förälder till parent via part_of.
    """
    seen: set[str] = set()
    cursor = parent_slug
    while cursor and cursor in nodes and cursor not in seen:
        if cursor == child_slug:
            return True
        seen.add(cursor)
        cursor = nodes[cursor].part_of
    return False


# Sorteringsordning: frameworks/system före components, sen på stage-mognad.
_KIND_RANK = {"framework": 0, "system": 1, "component": 2}
_STAGE_RANK = {"maturing": 0, "working": 1, "building": 2, "idea": 3}


def _sort_key(node: NodeView) -> tuple[int, int, str]:
    return (
        _KIND_RANK.get(node.kind, 9),
        _STAGE_RANK.get(node.stage, 9),
        node.slug,
    )


def _sort_recursive(nodes: list[NodeView]) -> None:
    nodes.sort(key=_sort_key)
    for node in nodes:
        _sort_recursive(node.children)


def filter_nodes(nodes: dict[str, NodeView], query: str) -> dict[str, NodeView]:
    """Returnera delmängd som matchar query, plus alla anfäder till matchande.

    Matchning: substring (case-insensitive) mot stage ELLER status. Anfäder
    tas med via part_of-kedjan så föräldrar inte försvinner och barnen blir
    hemlösa. Tom query → hela uppsättningen oförändrad.
    """
    q = query.strip().lower()
    if not q:
        return nodes

    keep: dict[str, NodeView] = {}
    for slug, node in nodes.items():
        if q in node.stage.lower() or q in node.status.lower():
            keep[slug] = node
            # Lägg till hela anfäderskedjan (cykelsäkrad via seen).
            cursor = node.part_of
            seen: set[str] = set()
            while cursor and cursor in nodes and cursor not in seen:
                seen.add(cursor)
                keep[cursor] = nodes[cursor]
                cursor = nodes[cursor].part_of
    return keep
