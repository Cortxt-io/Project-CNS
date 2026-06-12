"""Läsare för catalog.yaml — den enda strukturerade källan för nodmodellen.

Del av nodmodell-teardown (epic #11, issue #98). Ersätter nodes/*/node.md som
sanningskälla. `kind` härleds ur part_of-strukturen (lagras inte) — modellen är fraktal:
- framework: toppnivå (inget part_of)
- system: andra system pekar på den via part_of (har barn)
- component: ingen pekar på den (löv)

md_parser.read_node/read_all_nodes är nu tunna wrappers ovanpå load_catalog() som
returnerar samma (meta, sections)-form som förr → konsumenterna (json_exporter,
app/tools/projects, tui, analyst, recommend) är oförändrade.

Fält som inte längre finns (delegerade till board / borttagna): status, stage, risks,
mvp_stage, cost_sek, value_sek, roi_percent, family, layer, pipeline, url_live, tags.
Konsumenter som läser dem får tomt fallback-värde.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog.yaml"
DECISIONS_DIR = REPO_ROOT / "decisions"

# Kanonisk fältordning per system i catalog.yaml (utskriftsordning).
CATALOG_FIELD_ORDER = [
    "title", "summary", "part_of", "type", "domain",
    "owner_agent", "contributing_agents", "feeds", "depends_on", "url_repo",
    "integrations",
]

# Fält som alltid skrivs som listor (även tomma = explicit "inga kanter").
_LIST_FIELDS_ALWAYS = ("feeds", "depends_on")


def load_catalog() -> dict[str, dict[str, Any]]:
    """Returnera systems-mappningen (slug → fält) ur catalog.yaml.

    Tom dict om filen saknas (så verktyg inte kraschar under migreringen).
    """
    if not CATALOG_PATH.exists():
        return {}
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")) or {}
    return data.get("systems", {}) or {}


def _ordered_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Sortera ett systems fält i kanonisk ordning (kända först, okända sist)."""
    out: dict[str, Any] = {}
    for field in CATALOG_FIELD_ORDER:
        if field in entry:
            out[field] = entry[field]
    for field in entry:  # bevara ev. okända fält sist
        if field not in out:
            out[field] = entry[field]
    return out


def dump_catalog(systems: dict[str, dict]) -> str:
    """Serialisera systems-mappningen till catalog.yaml-text (med header)."""
    header = (
        "# Systemkatalog + arkitekturgraf + routing-tabell.\n"
        "# Enda strukturerade källan för nodmodellen (ersätter nodes/*/node.md).\n"
        "# Spec: plans/nodmodell-teardown-spec.md (epic #11).\n\n"
    )
    ordered = {slug: _ordered_entry(systems[slug]) for slug in sorted(systems)}
    body = yaml.safe_dump(
        {"systems": ordered},
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    return header + body


def write_catalog(systems: dict[str, dict]) -> Path:
    """Skriv hela systems-mappningen till catalog.yaml. Returnerar sökvägen."""
    CATALOG_PATH.write_text(dump_catalog(systems), encoding="utf-8")
    return CATALOG_PATH


def upsert_system(slug: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Skapa eller uppdatera ett system i katalogen. Returnerar den nya posten.

    Endast nycklar i *fields* som inte är None skrivs; feeds/depends_on normaliseras
    till listor. Övriga fält på ett befintligt system lämnas orörda.
    """
    systems = load_catalog()
    entry = dict(systems.get(slug, {}))
    for key, value in fields.items():
        if value is None:
            continue
        if key in ("feeds", "depends_on", "contributing_agents"):
            entry[key] = [v for v in (value or []) if v]
        else:
            entry[key] = value
    # feeds/depends_on ska alltid finnas som listor på ett system.
    for key in _LIST_FIELDS_ALWAYS:
        entry.setdefault(key, [])
    systems[slug] = entry
    write_catalog(systems)
    return entry


def set_decision(slug: str, text: str) -> Path:
    """Skriv (eller ersätt) decisions/<slug>.md med fri markdown."""
    DECISIONS_DIR.mkdir(exist_ok=True)
    path = DECISIONS_DIR / f"{slug}.md"
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return path


def derive_kind(slug: str, systems: dict[str, dict] | None = None) -> str:
    """Härled kind ur part_of-strukturen (fraktal modell)."""
    if systems is None:
        systems = load_catalog()
    entry = systems.get(slug, {})
    part_of = (entry.get("part_of") or "").strip()
    has_children = any((v.get("part_of") or "") == slug for v in systems.values())
    if not part_of:
        return "framework"
    if has_children:
        return "system"
    return "component"


def read_decision(slug: str) -> str:
    """Returnera decisions/<slug>.md-innehållet (ADR-prosa) eller tom sträng."""
    path = DECISIONS_DIR / f"{slug}.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def catalog_to_meta(slug: str, entry: dict[str, Any], systems: dict[str, dict]) -> dict[str, Any]:
    """Bygg ett `meta`-dict i samma form som gamla node.md-frontmatter gav.

    Behåller de nycklar konsumenterna läser; delegerade/borttagna fält får tomt
    fallback så json_exporter m.fl. fortsätter producera samma nodes.json-schema.
    """
    return {
        "slug": slug,
        "title": entry.get("title", ""),
        "summary": entry.get("summary", ""),
        "kind": derive_kind(slug, systems),
        "part_of": entry.get("part_of", "") or "",
        "feeds": entry.get("feeds") or [],
        "depends_on": entry.get("depends_on") or [],
        "type": entry.get("type", "") or "",
        "domain": entry.get("domain", "") or "",
        "owner_agent": entry.get("owner_agent", "") or "",
        "contributing_agents": entry.get("contributing_agents") or [],
        "url_repo": entry.get("url_repo", "") or "",
        # Delegerade/borttagna fält — tomt fallback (dashboarden fallbackar):
        "stage": "",
        "status": "",
        "tags": [],
    }


def load_nodes_as_meta() -> list[tuple[dict[str, Any], dict[str, str]]]:
    """Returnera [(meta, sections), ...] för alla system — wrapper-formen.

    sections är tomt: prosan bor numera i decisions/<slug>.md, inte i node-sektioner.
    Konsumenter som läste sektioner (t.ex. json_exporters product-fält) får tomt.
    """
    systems = load_catalog()
    out: list[tuple[dict[str, Any], dict[str, str]]] = []
    for slug in sorted(systems):
        meta = catalog_to_meta(slug, systems[slug], systems)
        out.append((meta, {}))
    return out


def read_node_as_meta(slug: str) -> tuple[dict[str, Any], dict[str, str], str]:
    """Som md_parser.read_node men ur katalogen: (meta, sections, raw).

    raw = decisions-prosan (närmaste motsvarighet till gamla råa node.md).
    Raises KeyError om systemet inte finns i katalogen.
    """
    systems = load_catalog()
    if slug not in systems:
        raise KeyError(f"System '{slug}' saknas i catalog.yaml")
    meta = catalog_to_meta(slug, systems[slug], systems)
    return meta, {}, read_decision(slug)
