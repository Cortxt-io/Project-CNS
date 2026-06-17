"""Deklarativ projektion av den kanoniska taxonomin mot externa plattformar.

Anti-Corruption Layer som data: en tabell ``kanoniskt-begrepp × plattform → hur det speglas``.
CNS äger originalet (``scripts/work_taxonomy.py``); varje plattform får en **partiell** spegel.

- ``native=None`` → **no-op**: begreppet har inget hem på plattformen. Ett giltigt, deklarerat
  utfall — inte ett TODO och inte ett fel.
- **Single-writer per fält:** ``direction`` säger åt vilket håll fältet skrivs
  (``"out"`` CNS→plattform · ``"in"`` plattform→CNS, skrivskyddat i CNS · ``None`` no-op).
  Inget fält skrivs från två håll. ``field_owner`` = vem som äger sanningen för fältet.

GitHub formaliserar dagens beteende + org-Project-ytan. Linear/Vercel är **deklarerade men
EJ byggda** (``mechanism=None`` = inte wirad). Ingen motor — uppslagstabell + getters; att
lägga ett nytt begrepp (t.ex. "sprint") eller en ny plattform = rader till i tabellen, ingen
kärnändring. Se sprint-acceptanstestet i ``tests/test_projections.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from scripts.work_taxonomy import layer_names


@dataclass(frozen=True)
class Projection:
    """Hur ett kanoniskt begrepp speglas på EN plattform."""

    canonical: str
    platform: str
    native: Optional[str]       # plattformens begrepp, eller None = no-op
    mechanism: Optional[str]    # HUR: "milestone"|"issue"|"single_select_field"|... None = ej wirad
    direction: Optional[str]    # "out" | "in" | None (no-op)
    field_owner: str            # "cns" | "github" | "linear" | "vercel"
    note: str = ""


# Icke-lager-begrepp som ändå projiceras (status/fält, inte egna hierarki-lager).
FIELD_CANONICALS: tuple[str, ...] = ("pr_status",)

# GitHub formaliserar dagens beteende + org-Project v2-ytan (cross-repo).
GITHUB: tuple[Projection, ...] = (
    Projection("initiative", "github", "single_select_field", "org_project_field", "out", "cns",
               "Org-Project v2 single-select; ersätter Initiative:-textprefix (filtrerbart, cross-repo)."),
    Projection("epic", "github", "milestone", "milestone", "out", "cns",
               "Per-repo lagring; cross-repo-vy via att issues läggs i org-Project."),
    Projection("story", "github", "issue", "issue", "out", "cns",
               "GitHub Issue + label type:<v>; additem i org-Project."),
    Projection("todo", "github", "checkbox", "task_list", "out", "cns",
               "Task-list-checkbox i issue-body (GitHub = sanning)."),
    Projection("pr_status", "github", "pull_request", "rest", "in", "github",
               "PR/merge-status läses IN, skrivskyddat i CNS (single-writer: GitHub äger)."),
)

# Linear: DEKLARERAD, EJ BYGGD (mechanism=None). Native-hem finns för hela hierarkin.
LINEAR: tuple[Projection, ...] = (
    Projection("initiative", "linear", "Initiative", None, "out", "cns", "förberedd"),
    Projection("epic", "linear", "Project", None, "out", "cns", "förberedd"),
    Projection("story", "linear", "Issue", None, "out", "cns", "förberedd"),
    Projection("todo", "linear", "sub-issue", None, "out", "cns", "förberedd"),
)

# Vercel: speglar NODLAGRET (drift), inte arbetstaxonomin → hela arbetslagret är no-op.
# Nod→Vercel-projektionen (catalog-system → deployment) deklareras i nodspegeln, ej här.
VERCEL: tuple[Projection, ...] = (
    Projection("initiative", "vercel", None, None, None, "vercel", "no-op: Vercel ser inte arbetslager"),
    Projection("epic", "vercel", None, None, None, "vercel", "no-op"),
    Projection("story", "vercel", None, None, None, "vercel", "no-op"),
    Projection("todo", "vercel", None, None, None, "vercel", "no-op"),
)

PROJECTIONS: tuple[Projection, ...] = GITHUB + LINEAR + VERCEL

PLATFORMS: tuple[str, ...] = ("github", "linear", "vercel")


def projection(
    canonical: str, platform: str, table: tuple[Projection, ...] = PROJECTIONS
) -> Optional[Projection]:
    """Slå upp projektionen för (begrepp, plattform). None = odeklarerat par (implicit no-op).

    ``table`` är injicerbar så utbyggbarhet kan testas utan att röra modulens globala tabell.
    """
    for p in table:
        if p.canonical == canonical and p.platform == platform:
            return p
    return None


def is_noop(canonical: str, platform: str, table: tuple[Projection, ...] = PROJECTIONS) -> bool:
    """True om begreppet saknar hem på plattformen (odeklarerat ELLER ``native=None``)."""
    p = projection(canonical, platform, table)
    return p is None or p.native is None


def for_platform(platform: str, table: tuple[Projection, ...] = PROJECTIONS) -> tuple[Projection, ...]:
    """Alla projektioner för en plattform."""
    return tuple(p for p in table if p.platform == platform)


def known_canonicals() -> frozenset[str]:
    """Begrepp som får projiceras: hierarki-lager + deklarerade fält-begrepp."""
    return frozenset(layer_names()) | frozenset(FIELD_CANONICALS)
