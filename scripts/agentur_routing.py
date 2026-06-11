"""Agenturens routing-modell (issue #90).

``route(node_type, issue_type, *, domain, station)`` → vilket **flöde** (stationer) arbetet
passerar, vilken **disciplin/department/squad** som bemannar, och vilken **modellnivå**.
Spec: ``plans/agentur-routing-spec.md``.

**Mekanism vs innehåll (skiva 2):** denna modul är den GENERISKA mekanismen. INNEHÅLLET (flöden,
node.type→disciplin, modellnivåer) bor i per-agentur-konfig under ``config/agenturer/<slug>.json``.
``node.domain`` väljer agentur (venture→agentur). Ett research-venture = en ny konfigfil, inte kod
— mekanismen rörs aldrig. Squad **parametriserar** passet, skapar ingen ny sessionstyp (#90-notering).

**Plan A/B-väggen:** läser den projicerade artefakten ``exports/agents.json`` (roster) och
``config/agenturer/`` (produktrymd-konfig) — ALDRIG ``.claude/`` direkt.

Ren, testbar funktion (samma mönster som ``agent_eval``/``agent_guardrails``). Plan A-tooling.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_FILE = ROOT / "exports" / "agents.json"
AGENTURER_DIR = ROOT / "config" / "agenturer"

# Yttersta fallback om ingen konfig hittas (mekanismen får aldrig krascha på saknad konfig).
DEFAULT_FLOW = ["definition", "delivery", "review"]
_BUILTIN_AGENTUR = {
    "slug": "(builtin-default)",
    "flows": {},
    "default_flow": DEFAULT_FLOW,
    "disciplines": {},
    "model_tiers": {"_default": "sonnet"},
}


# ---------------------------------------------------------------------------
# Konfig-laddning (per-agentur)
# ---------------------------------------------------------------------------


def load_agenturer() -> list[dict]:
    """Läs alla per-agentur-konfigar ur ``config/agenturer/*.json``. [] om katalogen saknas."""
    if not AGENTURER_DIR.exists():
        return []
    out: list[dict] = []
    for path in sorted(AGENTURER_DIR.glob("*.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def resolve_agentur(
    *, domain: str | None = None, slug: str | None = None, agenturer: list[dict] | None = None
) -> dict:
    """Välj agentur-konfig: explicit ``slug`` → ``domain`` (matchar ``domains``) → första → builtin.

    Det här är venture→agentur-väljaren: ``node.domain`` bestämmer vilken agentur som äger arbetet.
    """
    agenturer = load_agenturer() if agenturer is None else agenturer
    if not agenturer:
        return _BUILTIN_AGENTUR
    if slug:
        for a in agenturer:
            if a.get("slug") == slug:
                return a
    if domain:
        for a in agenturer:
            if domain in (a.get("domains") or []):
                return a
    return agenturer[0]  # default = första konfigurerade agenturen


# ---------------------------------------------------------------------------
# Roster + bemanning
# ---------------------------------------------------------------------------


def _load_agents() -> list[dict]:
    """Läs agent-projektionen (exports/agents.json). [] om filen saknas (degraderar tyst)."""
    if not AGENTS_FILE.exists():
        return []
    try:
        data = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data.get("agents", []) if isinstance(data, dict) else (data or [])


def _squad_for(discipline: str, agents: list[dict]) -> list[dict]:
    """Agenter i disciplinen (sub_department). Aktiva först; faller tillbaka på alla i disciplinen."""
    if not discipline:
        return []
    in_disc = [a for a in agents if a.get("sub_department") == discipline]
    active = [a for a in in_disc if a.get("status") == "active"]
    return active or in_disc


def _model_tier(agentur: dict, issue_type: str, station: str | None) -> str:
    """Modellnivå ur agenturens ``model_tiers``: per-typ kan vara sträng eller {station: nivå, _default}."""
    tiers = agentur.get("model_tiers", {}) or {}
    spec = tiers.get(issue_type)
    if isinstance(spec, dict):
        return spec.get(station) or spec.get("_default") or tiers.get("_default", "sonnet")
    if isinstance(spec, str):
        return spec
    return tiers.get("_default", "sonnet")


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def route(
    node_type: str,
    issue_type: str,
    *,
    domain: str | None = None,
    station: str | None = None,
    agents: list[dict] | None = None,
    agentur: dict | None = None,
) -> dict:
    """Routa ett arbete: (node.domain, node.type, issue.type[, station]) → flöde, bemanning, modell.

    ``domain`` väljer agentur-konfig (venture→agentur). ``agentur``/``agents`` injiceras för test
    (default laddas ur config/agenturer + exports/agents.json). ``station`` default = första i flödet.
    Degraderar tyst: okänd typ → konfigens default_flow; okänd disciplin/tom roster → tom squad.
    """
    cfg = agentur if agentur is not None else resolve_agentur(domain=domain)
    agents = _load_agents() if agents is None else agents

    flow = cfg.get("flows", {}).get(issue_type) or cfg.get("default_flow", DEFAULT_FLOW)
    station = station or (flow[0] if flow else None)
    discipline = cfg.get("disciplines", {}).get(node_type, "")
    squad = _squad_for(discipline, agents)

    return {
        "agentur": cfg.get("slug"),
        "domain": domain,
        "node_type": node_type,
        "issue_type": issue_type,
        "flow": flow,
        "station": station,
        "discipline": discipline,
        "department": squad[0]["department"] if squad else "",
        "squad": [a.get("slug") for a in squad],
        "model": _model_tier(cfg, issue_type, station),
    }
