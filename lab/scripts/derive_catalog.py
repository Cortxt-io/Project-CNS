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
ANNOTATIONS_PATH = REPO_ROOT / "catalog.annotations.yaml"
MERGED_PATH = REPO_ROOT / "catalog.merged.yaml"

# Noder i katalogen som är kända grupperings-attrapper (inte system) — spec 3.3.
# De backas inte av någon verklighet; flaggas som phantom i diffen.
KNOWN_PHANTOMS = {"pipeline-intern", "pipeline-extern", "pipeline-review"}

# Identitetsmappning härledd-slug → kanonisk katalog-slug (namn-glapp, spec öppen fråga).
# .mcp.json kallar servern "project-cns"; katalogen kallar samma sak "cns-mcp".
DERIVED_ALIAS = {"project-cns": "cns-mcp"}


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
    """Härled SYSTEM-noder för nod-katalogen (slug → nod).

    **Axel-beslut (Rikard 2026-06-12):** agenter är en EGEN axel (agentur/agents.json),
    inte noder i arkitektur-katalogen. Nod-katalogen härleder *system*-verkligheten
    (MCP-servrar nu; repo-struktur/drift senare). ``agents_data`` ignoreras därför här —
    agent-axeln projiceras separat via ``derive_agent_axis`` (egen vy, ej i kartan).

    Härledda slugs kanoniseras via DERIVED_ALIAS (project-cns → cns-mcp).
    """
    raw: dict[str, dict] = {}
    if mcp_data is not None:
        raw.update(derive_from_mcp(mcp_data))
    return {DERIVED_ALIAS.get(slug, slug): node for slug, node in raw.items()}


def derive_agent_axis(agents_data: dict | list) -> dict[str, dict]:
    """Projektion av AGENT-axeln (agentur) — separat vy, INTE noder i nod-katalogen.

    Behålls för en framtida agent-axel-vy i dashboarden; matas inte in i `merge`/katalogen.
    """
    return derive_from_agents(agents_data)


# -- annoterings-bygge + merge (skiva 2: den sammanslagna kartan) -------------

# Semantiska fält en människa annoterar (resten härleds).
_ANNOTATION_FIELDS = (
    "title", "summary", "part_of", "type", "domain", "owner_agent",
    "contributing_agents", "feeds", "depends_on", "url_repo", "integrations", "tags",
)


def build_annotations_from_catalog(catalog: dict[str, dict]) -> dict[str, dict]:
    """Migrera nuvarande catalog.yaml → annoteringslager (engångs, spec A3).

    Tar bort phantom-attrapperna; deras barn om-föräldras till attrappens förälder och
    får attrappens grupperingsnamn som `tags` i stället (spec 3.3: part_of → tags).
    """
    # phantom-slug → (förälder, grupperingstagg)
    phantom_parent: dict[str, str] = {}
    phantom_tag: dict[str, str] = {}
    for slug in KNOWN_PHANTOMS:
        entry = catalog.get(slug, {})
        phantom_parent[slug] = (entry.get("part_of") or "").strip()
        phantom_tag[slug] = slug.replace("pipeline-", "")  # intern/extern/review

    out: dict[str, dict] = {}
    for slug, entry in catalog.items():
        if slug in KNOWN_PHANTOMS:
            continue  # attrappen själv försvinner
        ann = {k: entry[k] for k in _ANNOTATION_FIELDS if k in entry}
        parent = (entry.get("part_of") or "").strip()
        if parent in KNOWN_PHANTOMS:
            ann["part_of"] = phantom_parent[parent]                 # om-föräldra
            tags = list(ann.get("tags") or [])
            for t in ("pipeline", phantom_tag[parent]):
                if t not in tags:
                    tags.append(t)
            ann["tags"] = tags
        out[slug] = ann
    return out


def merge(derived: dict[str, dict], annotations: dict[str, dict]) -> dict[str, dict]:
    """Slå ihop härlett (struktur) + annoterat (semantik) → full nodmapping.

    Annotering bär semantik och vinner på semantiska fält; härlett bidrar existens +
    `type`/`part_of` när annotering saknar dem, samt `_source`-spår. Unionen av slugs.
    """
    out: dict[str, dict] = {}
    for slug in set(derived) | set(annotations):
        d = derived.get(slug, {})
        a = annotations.get(slug, {})
        node = dict(d)        # härlett som bas (existens, type, _source, status_derived)
        node.update(a)        # annotering vinner på semantiska fält
        if d.get("_source"):  # härledningsspåret överlever annoteringen
            node["_source"] = d["_source"]
        out[slug] = node
    return out


# -- diff mot handkatalogen (A3-grinden) -------------------------------------

# Självflaggande markörer i en nods summary (handskriven av ägaren).
# Bara entydiga död-markörer. "ersatt av X" är medvetet UTE — den kan betyda
# "tillfälligt täckt av X men planerad" (t.ex. mcp-gateway), inte död.
_STALE_MARKERS = (
    "superseded", "deprecated", "död rest", "historical reference", "kept for historical",
)
_ASPIRATIONAL_MARKERS = (
    "planerad", "byggs först", "byggs när", "ej byggd", "inte byggd", "ännu inte",
    "framtida", "aspirational", "idé-nod", "research-plan",
)


def classify_backing(
    slug: str, entry: dict, *, file_stems: set[str], child_slugs: set[str]
) -> tuple[str, str]:
    """Klassa en katalognod mot repo-verkligheten → (status, bevis).

    status ∈ {true, stale, aspirational, grouping}. Heuristik (konservativ — FLAGGAR
    kandidater, raderar inget): nodens egen summary (självflaggning) väger tyngst, sedan
    grupperings-roll, sedan repo-backing (url_repo eller en fil vars namn matchar slugen).
    """
    summary = (entry.get("summary") or "").lower()
    if any(m in summary for m in _STALE_MARKERS):
        return "stale", "summary självflaggar superseded/deprecated"
    if slug in child_slugs:
        return "grouping", "grupperingsnod — andra noder är part_of denna"
    if entry.get("url_repo"):
        return "true", f"url_repo: {entry['url_repo']}"
    token = slug.replace("cns-", "").replace("cortxt-", "").replace("-", "_")
    if token and any(token in stem for stem in file_stems):
        return "true", f"fil matchar '{token}'"
    if any(m in summary for m in _ASPIRATIONAL_MARKERS):
        return "aspirational", "summary självflaggar planerad/ej byggd"
    return "aspirational", "ingen repo-backing hittad"


def classify_catalog(catalog: dict[str, dict], *, file_stems: set[str]) -> dict[str, tuple[str, str]]:
    """Klassa alla katalognoder mot verkligheten → slug → (status, bevis)."""
    child_slugs = {(v.get("part_of") or "").strip() for v in catalog.values()}
    child_slugs.discard("")
    return {
        slug: classify_backing(slug, entry, file_stems=file_stems, child_slugs=child_slugs)
        for slug, entry in catalog.items()
        if slug not in KNOWN_PHANTOMS
    }


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
    """Härled SYSTEM-noder ur repo-källorna på disk (.mcp.json; repo/drift senare).

    Agenter härleds INTE hit (egen axel) — se ``derive`` / ``derive_agent_axis``.
    """
    return derive(mcp_data=_load_json(MCP_JSON))


def repo_file_stems() -> set[str]:
    """Filstammar (utan ändelse, lowercase) ur scripts/ + app/ + repo-roten — backing-bevis."""
    stems: set[str] = set()
    for sub in ("scripts", "app", "."):
        d = REPO_ROOT / sub if sub != "." else REPO_ROOT
        if not d.exists():
            continue
        for p in d.rglob("*.py"):
            stems.add(p.stem.lower())
        for p in d.iterdir():  # mappnamn på toppnivå (t.ex. app, scripts)
            if p.is_dir():
                stems.add(p.name.lower())
    return stems


def verify_from_disk() -> dict[str, tuple[str, str]]:
    """Klassa nuvarande catalog.yaml mot repo-verkligheten."""
    return classify_catalog(load_current_catalog(), file_stems=repo_file_stems())


def render_verify(classified: dict[str, tuple[str, str]]) -> str:
    """Rendera klassningen grupperad per status."""
    buckets: dict[str, list[str]] = {"stale": [], "aspirational": [], "grouping": [], "true": []}
    for slug, (status, why) in sorted(classified.items()):
        buckets.setdefault(status, []).append(f"  {slug} — {why}")
    order = [
        ("stale", "💀 STALE (död rest — kandidat för borttagning)"),
        ("aspirational", "🔶 ASPIRATIONAL (planerad, ej byggd)"),
        ("grouping", "📦 GROUPING (grupperingsnod — tag eller riktig?)"),
        ("true", "✅ TRUE (repo-backing finns)"),
    ]
    lines = ["# Backing-verifiering: katalognoder vs repo-verkligheten", ""]
    for key, label in order:
        rows = buckets.get(key, [])
        lines.append(f"{label}: {len(rows)}")
        lines.extend(rows)
        lines.append("")
    return "\n".join(lines)


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


def load_annotations() -> dict[str, dict]:
    """Läs catalog.annotations.yaml (handannoterad semantik). Tom om filen saknas."""
    if not ANNOTATIONS_PATH.exists():
        return {}
    data = yaml.safe_load(ANNOTATIONS_PATH.read_text(encoding="utf-8")) or {}
    return data.get("systems", {}) or {}


def write_annotations(annotations: dict[str, dict]) -> Path:
    """Skriv annoteringslagret (handkälla — får redigeras för hand)."""
    header = (
        "# HANDKÄLLA — semantik som inte kan härledas (summary/domain/owner/tags m.m.).\n"
        "# Genererad engångs ur catalog.yaml; redigeras sedan för hand. Strukturen\n"
        "# (existens/type för agenter+MCP) härleds separat och mergas ovanpå. Se spec.\n\n"
    )
    ordered = {slug: annotations[slug] for slug in sorted(annotations)}
    ANNOTATIONS_PATH.write_text(
        header + yaml.safe_dump({"systems": ordered}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return ANNOTATIONS_PATH


def build_merged_from_disk() -> dict[str, dict]:
    """Full sammanslagen karta: härlett (agents.json/.mcp.json) + annoterat (de 29)."""
    return merge(derive_from_disk(), load_annotations())


def write_merged(merged: dict[str, dict]) -> Path:
    """Skriv den sammanslagna kartan till en INSPEKTERBAR fil (flippar inte load_catalog)."""
    header = (
        "# GENERERAD (cns derive --apply) — INSPEKTIONS-artefakt, redigera INTE.\n"
        "# Sammanslagning av härlett (verklighet) + annoterat (de 29). Konsumenterna\n"
        "# läser ÄNNU catalog.yaml; detta är förhandsvisningen inför flippen (skiva 2b).\n\n"
    )
    ordered = {slug: merged[slug] for slug in sorted(merged)}
    MERGED_PATH.write_text(
        header + yaml.safe_dump({"systems": ordered}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return MERGED_PATH
