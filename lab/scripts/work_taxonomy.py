"""Kanonisk arbetstaxonomi — enkälla för CNS arbetsobjekt-lager och deras typer.

Ren data, inga REST/SDK-importer. Gör den taxonomi explicit som tidigare bara levde i
kommentarer + prosa (CLAUDE.md "Begreppsmodell", den saknade ``plans/work-model-taxonomy-spec.md``):
objekt-hierarkin **initiative > epic > story > todo** (AXEL 1) och issue-typerna.

Den här filen säger **VAD** som finns. **VAR** det speglas (GitHub/Linear/Vercel) bor i
``scripts/projections.py``. Mönster: frozen dataclasses + uppslag, som ``scripts/tools/registry.py``.

``VALID_ISSUE_TYPES``/``DEFAULT_ISSUE_TYPE`` re-exporteras härifrån så ``issues_client`` har
EN källa (issues schemavalideras inte mot ``enums.json`` — därför inte där).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Layer:
    """Ett lager i objekt-hierarkin. ``parent`` = närmaste lager ovanför (None = toppen)."""

    name: str
    parent: str | None
    summary: str


@dataclass(frozen=True)
class WorkType:
    """En issue-typ. ``is_default`` = fallback för otaggade issues (gamla utan ``type:``-label)."""

    name: str
    is_default: bool = False


# Objekt-hierarkin (AXEL 1), ordnad topp→botten. ``sprint`` är medvetet INTE med — den läggs
# som ett rent datatillägg (en rad här + en rad/plattform i projections.py) när sprint-nivån
# införs; se sprint-acceptanstestet i tests/test_projections.py.
LAYERS: tuple[Layer, ...] = (
    Layer("initiative", None, "Strategisk satsning som spänner över flera epics."),
    Layer("epic", "initiative", "Sammanhållet spår (= GitHub Milestone)."),
    Layer("story", "epic", "En konkret uppgift (= GitHub Issue, type:story)."),
    Layer("todo", "story", "Sub-task: task-list-checkbox i issue-body."),
)

ISSUE_TYPES: tuple[WorkType, ...] = (
    WorkType("story", is_default=True),
    WorkType("bug"),
    WorkType("spike"),
    WorkType("chore"),
)

# Re-exporter: behåller exakt de historiska värdena issues_client ägde tidigare.
VALID_ISSUE_TYPES: frozenset[str] = frozenset(t.name for t in ISSUE_TYPES)
DEFAULT_ISSUE_TYPE: str = next(t.name for t in ISSUE_TYPES if t.is_default)

_LAYER_BY_NAME = {layer.name: layer for layer in LAYERS}


def layer(name: str) -> Layer | None:
    """Slå upp ett lager på namn, eller None."""
    return _LAYER_BY_NAME.get(name)


def layer_names() -> tuple[str, ...]:
    """Lagernamnen, topp→botten."""
    return tuple(layer_.name for layer_ in LAYERS)
