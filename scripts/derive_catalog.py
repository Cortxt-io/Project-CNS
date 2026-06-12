"""Härled nodkatalogen ur den körande verkligheten (Del A — derived-catalog-spec).

**Varför:** `catalog.yaml` är handunderhållen och speglar inte verkligheten (samma drift
som node.md-teardownen). Den här modulen *härleder* noder ur sanningskällor och ställer dem
mot den handritade katalogen, så lögnen blir synlig (A3:s diff-grind).

**v1-källor (repo-interna, inga credentials):** `exports/agents.json` (agentflottan),
`.mcp.json` (MCP-servrar). Drift-ytor (Railway/Vercel/GitHub Actions/Redis) = senare, var sin
research-spike (spec 3.1b).

**Skiva 1 (denna):** härled + diffa. Modulen *ersätter inte* `catalog.yaml` ännu — den genererar
`catalog.derived.yaml` och en diff-rapport. Mergen i `load_catalog` + pensioneringen av `kind`
görs i skiva 2, efter att diffen granskats.

Ren och testbar: härledarna tar in data (dict), CLI:t laddar filerna. Ingen nätverksåtkomst.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_JSON = REPO_ROOT / "exports" / "agents.json"
MCP_JSON = REPO_ROOT / ".mcp.json"
CATALOG_PATH = REPO_ROOT / "catalog.yaml"
DERIVED_PATH = REPO_ROOT / "catalog.derived.yaml"

# Noder i katalogen som är kända grupperings-attrapper (inte system) — spec 3.3.
# De backas inte av någon verklighet; flaggas som phantom i diffen.
KNOWN_PHANTOMS = {"pipeline-intern", "pipeline-extern", "pipeline-review"}


# -- härledare (rena: tar in data, returnerar slug → nod) --------------------

def derive_from_agents(agents_data: dict | list) -> dict[str, dict]:
    """Härled en nod per agent ur agents.json-strukturen.

    Varje agent (byggd eller roster-skal) är en verklig entitet. Katalogen utelämnar
    nästan hela flottan — det är den största luckan.
    """
    agents = agents_data.get("agents", agents_data) if isinstance(agents_data, dict) else agents_data
    out: dict[str, dict] = {}
    for a in agents or []:
        slug = a.get("slug")
        if not slug:
            continue
        out[slug] = {
            "type": "agent",
            "title": a.get("title", slug),
            "domain": "cortxt",
            "part_of": "agentur",
            "status_derived": a.get("status", ""),     # active | shell
            "department": a.get("department", ""),
            "_source": "exports/agents.json",
        }
    return out


def derive_from_mcp(mcp_data: dict) -> dict[str, dict]:
    """Härled en nod per MCP-server ur .mcp.json (mcpServers-mappningen)."""
    servers = (mcp_data or {}).get("mcpServers", {}) or {}
    out: dict[str, dict] = {}
    for name, cfg in servers.items():
        out[name] = {
            "type": "mcp-server",
            "title": name,
            "domain": "cortxt",
            "transport": (cfg or {}).get("type", ""),
            "url": (cfg or {}).get("url", ""),
            "_source": ".mcp.json",
        }
    return out


def derive(*, agents_data: dict | list | None = None, mcp_data: dict | None = None) -> dict[str, dict]:
    """Slå ihop alla v1-härledare → en härledd nodmappning (slug → nod)."""
    derived: dict[str, dict] = {}
    if agents_data is not None:
        derived.update(derive_from_agents(agents_data))
    if mcp_data is not None:
        derived.update(derive_from_mcp(mcp_data))
    return derived


# -- diff mot handkatalogen (A3-grinden) -------------------------------------

@dataclass
class DiffReport:
    """Diff mellan härledd verklighet och handkatalogen."""
    only_in_reality: list[str] = field(default_factory=list)   # verkligt men saknas i catalog
    only_in_catalog: list[str] = field(default_factory=list)   # i catalog, ej täckt av v1-källor
    phantoms: list[str] = field(default_factory=list)          # i catalog, kända attrapper
    in_both: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        lines = ["# Diff: härledd verklighet vs catalog.yaml (v1-källor: agents.json, .mcp.json)", ""]
        lines.append(f"Verkligt men SAKNAS i katalogen: {len(self.only_in_reality)}")
        for s in self.only_in_reality[:200]:
            lines.append(f"  + {s}")
        lines.append("")
        lines.append(f"PHANTOM i katalogen (grupperings-attrapper, ej system): {len(self.phantoms)}")
        for s in self.phantoms:
            lines.append(f"  ! {s}")
        lines.append("")
        lines.append(
            f"I katalogen men EJ täckt av v1-källor: {len(self.only_in_catalog)} "
            "(obs: inkluderar äkta noder som frontends/tjänster som v1 ännu inte härleder — "
            "INTE automatiskt phantom)"
        )
        for s in self.only_in_catalog:
            lines.append(f"  ? {s}")
        lines.append("")
        lines.append(f"Finns i båda: {len(self.in_both)}")
        return "\n".join(lines)


def diff_against_catalog(derived: dict[str, dict], catalog: dict[str, dict]) -> DiffReport:
    """Ställ härledda noder mot handkatalogen. Ärlig om vad v1 INTE täcker."""
    derived_slugs = set(derived)
    catalog_slugs = set(catalog)
    report = DiffReport()
    report.only_in_reality = sorted(derived_slugs - catalog_slugs)
    report.in_both = sorted(derived_slugs & catalog_slugs)
    only_catalog = catalog_slugs - derived_slugs
    report.phantoms = sorted(s for s in only_catalog if s in KNOWN_PHANTOMS)
    report.only_in_catalog = sorted(s for s in only_catalog if s not in KNOWN_PHANTOMS)
    return report


# -- IO-skal (CLI använder dessa; tester använder de rena ovan) ---------------

def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def derive_from_disk() -> dict[str, dict]:
    """Härled ur repo-källorna på disk (agents.json + .mcp.json)."""
    return derive(agents_data=_load_json(AGENTS_JSON), mcp_data=_load_json(MCP_JSON))


def load_current_catalog() -> dict[str, dict]:
    """Läs nuvarande catalog.yaml (systems-mappningen) för diffen."""
    if not CATALOG_PATH.exists():
        return {}
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")) or {}
    return data.get("systems", {}) or {}


def dump_derived(derived: dict[str, dict]) -> str:
    """Serialisera härledd katalog till catalog.derived.yaml-text (med header)."""
    header = (
        "# GENERERAD av scripts/derive_catalog.py — redigera INTE för hand.\n"
        "# Härledd ur den körande verkligheten (v1: exports/agents.json, .mcp.json).\n"
        "# Semantik (summary/domain/owner) annoteras separat; se derived-catalog-spec.\n\n"
    )
    ordered = {slug: derived[slug] for slug in sorted(derived)}
    body = yaml.safe_dump({"systems": ordered}, allow_unicode=True, sort_keys=False)
    return header + body


def write_derived(derived: dict[str, dict]) -> Path:
    DERIVED_PATH.write_text(dump_derived(derived), encoding="utf-8")
    return DERIVED_PATH
