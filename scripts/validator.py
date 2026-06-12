"""Validering av catalog.yaml (nodmodell-teardown #100/#105).

node.md-validering (validate_node) och Perplexity-svarsvalidering (validate_response)
borttagna i #105 — node.md-modellen finns inte längre.
"""

from __future__ import annotations

import json
from pathlib import Path

# Allowed enum values — single source of truth: schemas/enums.json
# (also consumed by the JS package cortxt/packages/cns-schema via its generator).
# Loaded as sets; all consumers use only membership (`in`) and `sorted()`.
ENUMS_PATH = Path(__file__).resolve().parent.parent / "schemas" / "enums.json"
_ENUMS = json.loads(ENUMS_PATH.read_text(encoding="utf-8"))

VALID_STATUSES = set(_ENUMS["statuses"])
VALID_MVP_STAGES = set(_ENUMS["mvp_stages"])
VALID_RISK_CATEGORIES = set(_ENUMS["risk_categories"])
VALID_KINDS = set(_ENUMS["kinds"])
VALID_STAGES = set(_ENUMS["stages"])
VALID_TYPES = set(_ENUMS.get("types", []))
VALID_DOMAINS = set(_ENUMS.get("domains", []))

AGENTS_PATH = Path(__file__).resolve().parent.parent / "exports" / "agents.json"

# Legacy enum constants kept for reference but no longer validated:
# VALID_LAYERS, VALID_PIPELINES, VALID_FAMILIES

VALID_LAYERS = {
    "pipeline",
    "infrastructure",
    "interface",
    "concept",
}

VALID_PIPELINES = {
    "pipeline-intern",
    "pipeline-extern",
    "pipeline-review",
}

VALID_FAMILIES = {
    "developer-tools", "digest-pipeline", "internal-monitoring",
    "cns-core", "ideas", "cns-platform", "monitoring-pipeline",
}

# ---------------------------------------------------------------------------
# Catalog-level validation (nodmodell-teardown #100) — catalog.yaml är källan
# ---------------------------------------------------------------------------

def _detect_part_of_cycle(systems: dict[str, dict]) -> list[str]:
    """Returnera en lista slugs som ingår i en part_of-cykel (tom = ingen cykel)."""
    in_cycle: list[str] = []
    for start in systems:
        seen: set[str] = set()
        node = start
        while node:
            if node in seen:
                in_cycle.append(start)
                break
            seen.add(node)
            node = (systems.get(node, {}).get("part_of") or "").strip()
            if node not in systems:
                break
    return in_cycle


def validate_catalog(systems: dict[str, dict] | None = None) -> tuple[list[str], list[str]]:
    """Validera hela catalog.yaml. Returnerar (errors, warnings).

    Errors: trasiga part_of/feeds/depends_on-referenser, part_of-cykel, fel typform.
    Warnings: okänd type/domain/owner_agent (mjuk validering, som tidigare).
    """
    if systems is None:
        from scripts.catalog import load_catalog
        systems = load_catalog()

    errors: list[str] = []
    warnings: list[str] = []
    known = set(systems)

    # Referensintegritet: alla part_of/feeds/depends_on måste peka på existerande system.
    for slug, entry in sorted(systems.items()):
        part_of = (entry.get("part_of") or "").strip()
        if part_of and part_of not in known:
            errors.append(f"{slug}: part_of='{part_of}' refererar ett okänt system")
        for rel in ("feeds", "depends_on"):
            val = entry.get(rel)
            if val is None:
                continue
            if not isinstance(val, list):
                errors.append(f"{slug}: {rel} måste vara en lista, fick {type(val).__name__}")
                continue
            for target in val:
                if not isinstance(target, str):
                    errors.append(f"{slug}: {rel} måste vara strängar")
                elif target not in known:
                    errors.append(f"{slug}: {rel} → '{target}' refererar ett okänt system")

        # Mjuk validering av type/domain.
        node_type = entry.get("type")
        if node_type and VALID_TYPES and node_type not in VALID_TYPES:
            warnings.append(f"{slug}: okänd type '{node_type}'")
        domain = entry.get("domain")
        if domain and VALID_DOMAINS and domain not in VALID_DOMAINS:
            warnings.append(f"{slug}: okänd domain '{domain}'")

    # Cykelkoll i part_of.
    for slug in sorted(set(_detect_part_of_cycle(systems))):
        errors.append(f"{slug}: ingår i en part_of-cykel")

    # owner_agent mot agents.json (warn).
    if AGENTS_PATH.exists():
        try:
            raw = json.loads(AGENTS_PATH.read_text(encoding="utf-8"))
            known_agents = set(raw.keys()) if isinstance(raw, dict) else set(raw)
        except (json.JSONDecodeError, TypeError):
            known_agents = set()
        if known_agents:
            for slug, entry in sorted(systems.items()):
                owner = entry.get("owner_agent")
                if owner and owner not in known_agents:
                    warnings.append(f"{slug}: okänd owner_agent '{owner}'")

    return errors, warnings

