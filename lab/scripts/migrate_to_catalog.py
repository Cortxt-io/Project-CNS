"""Engångsmigrering: nodes/<slug>/node.md  →  catalog.yaml + decisions/<slug>.md

Del av nodmodell-teardown (epic #11, issue #97). Läser alla node.md via
md_parser.read_all_nodes(), plockar de fält som ÖVERLEVER teardownen och skriver dem
till en enda catalog.yaml. Substantiell ADR-prosa (## Anteckningar > 40 ord) flyttas
till glesa decisions/<slug>.md — system utan sådan prosa får ingen fil.

Fält som dör (skrivs INTE till katalogen): status, stage, risks, audience, alla legacy
(mvp_stage/cost_sek/value_sek/roi_percent/family/layer/pipeline), tags, url_live,
current_slice. Spec: plans/nodmodell-teardown-spec.md.

Idempotent: kör om → skriver om catalog.yaml och decisions/ deterministiskt.

Användning:
    python -m scripts.migrate_to_catalog            # skriv filerna
    python -m scripts.migrate_to_catalog --dry-run  # visa vad som skulle skrivas
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from scripts.md_parser import read_all_nodes

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog.yaml"
DECISIONS_DIR = REPO_ROOT / "decisions"

# Fält som följer med till katalogen (slug blir nyckeln, inte ett fält).
# Ordningen styr utskriftsordningen per system.
SURVIVING_FIELDS = [
    "title", "summary", "part_of", "type", "domain",
    "owner_agent", "contributing_agents", "feeds", "depends_on", "url_repo",
]

# Tröskel för att en Anteckningar-sektion ska räknas som varaktig ADR-prosa.
DECISION_WORD_THRESHOLD = 40
DECISION_SECTION = "Anteckningar"


def _clean_value(field: str, value: Any) -> Any:
    """Normalisera ett fältvärde för katalogen; returnera None för 'tomt'."""
    if value is None:
        return None
    if field in ("feeds", "depends_on", "contributing_agents"):
        items = [v for v in (value or []) if v]
        return items
    if isinstance(value, str):
        v = value.strip()
        return v or None
    return value


def build_catalog(nodes: list[tuple[dict, dict]]) -> dict[str, dict]:
    """Bygg systems-mappningen (slug → fält) sorterad på slug."""
    systems: dict[str, dict] = {}
    for meta, _sections in nodes:
        slug = meta.get("slug")
        if not slug:
            continue
        entry: dict[str, Any] = {}
        for field in SURVIVING_FIELDS:
            cleaned = _clean_value(field, meta.get(field))
            # feeds/depends_on tas alltid med (även tom lista) = explicit "inga kanter".
            if field in ("feeds", "depends_on"):
                entry[field] = cleaned
            # contributing_agents tas med bara om icke-tom; övriga bara om satt.
            elif field == "contributing_agents":
                if cleaned:
                    entry[field] = cleaned
            elif cleaned is not None:
                entry[field] = cleaned
        systems[slug] = entry
    return {s: systems[s] for s in sorted(systems)}


def _word_count(text: str) -> int:
    return len([w for w in text.split() if w.strip()])


def build_decisions(nodes: list[tuple[dict, dict]]) -> dict[str, str]:
    """Plocka ut substantiell Anteckningar-prosa → slug → markdown-innehåll."""
    decisions: dict[str, str] = {}
    for meta, sections in nodes:
        slug = meta.get("slug")
        if not slug:
            continue
        note = (sections.get(DECISION_SECTION) or "").strip()
        if _word_count(note) < DECISION_WORD_THRESHOLD:
            continue
        title = meta.get("title") or slug
        decisions[slug] = f"# {title} — beslut & anteckningar\n\n{note}\n"
    return decisions


def _dump_catalog(systems: dict[str, dict]) -> str:
    header = (
        "# Systemkatalog + arkitekturgraf + routing-tabell.\n"
        "# Enda strukturerade källan för nodmodellen (ersätter nodes/*/node.md).\n"
        "# Genererad av scripts/migrate_to_catalog.py — får sedan redigeras för hand.\n"
        "# Spec: plans/nodmodell-teardown-spec.md (epic #11).\n\n"
    )
    body = yaml.safe_dump(
        {"systems": systems},
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    return header + body


def migrate(dry_run: bool = False) -> tuple[int, int]:
    nodes = read_all_nodes()
    systems = build_catalog(nodes)
    decisions = build_decisions(nodes)

    catalog_text = _dump_catalog(systems)

    if dry_run:
        print(catalog_text)
        print(f"\n# {len(systems)} system, {len(decisions)} decisions-filer:")
        for slug in decisions:
            print(f"#   decisions/{slug}.md ({_word_count(decisions[slug])} ord)")
        return len(systems), len(decisions)

    CATALOG_PATH.write_text(catalog_text, encoding="utf-8")
    DECISIONS_DIR.mkdir(exist_ok=True)
    for slug, content in decisions.items():
        (DECISIONS_DIR / f"{slug}.md").write_text(content, encoding="utf-8")

    print(f"Skrev {CATALOG_PATH.relative_to(REPO_ROOT)} ({len(systems)} system).")
    print(f"Skrev {len(decisions)} decisions-filer till {DECISIONS_DIR.relative_to(REPO_ROOT)}/:")
    for slug in decisions:
        print(f"  decisions/{slug}.md")
    return len(systems), len(decisions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Visa utan att skriva filer")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
