"""Agenturens routing-modell (issue #90, FÖRSTA SKIVAN).

``route(node_type, issue_type, station)`` → vilket **flöde** (stationer) arbetet
passerar, vilken **disciplin/department/squad** som bemannar, och vilken **modellnivå**.
Spec: ``plans/agentur-routing-spec.md``.

Ren, testbar funktion (samma mönster som ``agent_eval``/``agent_guardrails``). Plan A-tooling.
**Plan A/B-väggen:** läser den projicerade artefakten ``exports/agents.json`` (genererad av
``gen_agentur.py``), ALDRIG ``.claude/`` direkt.

Detta är **produktutvecklings-agenturens konfig** hårdkodad i modulen. Mekanismen är generisk;
innehållet (flöden, node.type→disciplin, modellnivåer) externaliseras till per-agentur-konfig i
en senare skiva (#90 öppen fråga 1) så research-venture m.fl. slätar in. Squad **parametriserar**
passet — den skapar ingen ny sessionstyp (#90-notering).
"""
from __future__ import annotations

import json
from pathlib import Path

AGENTS_FILE = Path(__file__).resolve().parent.parent / "exports" / "agents.json"

# Stationer en run kan passera (gemensamma för produktutvecklings-agenturen).
STATIONS = ("discovery", "definition", "delivery", "review", "retro")

# Flöde per issue.type — VILKA stationer arbetet passerar. Bestämmer vägen, inte typen.
FLOW_BY_TYPE: dict[str, list[str]] = {
    "spike": ["discovery"],                                  # producerar kunskap, ingen kod
    "bug": ["delivery", "review"],                           # problemet känt → hoppa discovery/definition
    "chore": ["delivery", "review"],
    "story": ["definition", "delivery", "review"],
    "epic": ["discovery", "definition", "review", "retro"],
    "initiative": ["discovery", "definition", "review", "retro"],
}
DEFAULT_FLOW = ["definition", "delivery", "review"]          # okänd typ → story-likt

# node.type → disciplin (= sub_department i agents.json) → bestämmer vilken squad bemannar.
NODE_TYPE_TO_DISCIPLINE: dict[str, str] = {
    "frontend": "Frontend",
    "service": "Backend",
    "mcp-server": "Integrations",
    "pipeline": "Data",
    "cli": "Backend",
    "tool": "DevEx",
    "agent": "Research",
    "infra": "Infra",
    "library": "Backend",
    "dataset": "Data",
    "ai-model": "Research",
}

# Modellnivå per (issue.type, station): mekaniskt→haiku, omdöme→sonnet, syntes/strategi→opus
# (Ekonomen-grinden kodifierad — jfr modell-router #79.) None-station = gäller alla stationer.
MODEL_TIER: dict[tuple[str, str | None], str] = {
    ("chore", None): "haiku",
    ("bug", None): "sonnet",
    ("story", None): "sonnet",
    ("spike", None): "sonnet",
    ("epic", "discovery"): "opus",
    ("epic", "definition"): "opus",
    ("epic", "retro"): "opus",
    ("epic", "delivery"): "sonnet",
    ("epic", "review"): "sonnet",
    ("initiative", "discovery"): "opus",
    ("initiative", "definition"): "opus",
}


def _load_agents() -> list[dict]:
    """Läs agent-projektionen (exports/agents.json). [] om filen saknas (degraderar tyst)."""
    if not AGENTS_FILE.exists():
        return []
    try:
        data = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data.get("agents", []) if isinstance(data, dict) else (data or [])


def _model_tier(issue_type: str, station: str | None) -> str:
    """Modellnivå för (typ, station), med station-oberoende fallback, default sonnet."""
    return (
        MODEL_TIER.get((issue_type, station))
        or MODEL_TIER.get((issue_type, None))
        or "sonnet"
    )


def _squad_for(discipline: str, agents: list[dict]) -> list[dict]:
    """Agenter i disciplinen (sub_department). Aktiva först; faller tillbaka på alla i disciplinen."""
    if not discipline:
        return []
    in_disc = [a for a in agents if a.get("sub_department") == discipline]
    active = [a for a in in_disc if a.get("status") == "active"]
    return active or in_disc


def route(
    node_type: str,
    issue_type: str,
    *,
    station: str | None = None,
    agents: list[dict] | None = None,
) -> dict:
    """Routa ett arbete: (node.type, issue.type[, station]) → flöde, bemanning, modell.

    ``agents`` injiceras för test (default laddas ``exports/agents.json``). ``station``
    default = första stationen i flödet. Degraderar tyst: okänd typ → DEFAULT_FLOW,
    okänd disciplin/tom roster → tom squad (kraschar inte).
    """
    agents = _load_agents() if agents is None else agents
    flow = FLOW_BY_TYPE.get(issue_type, DEFAULT_FLOW)
    station = station or (flow[0] if flow else None)
    discipline = NODE_TYPE_TO_DISCIPLINE.get(node_type, "")
    squad = _squad_for(discipline, agents)
    return {
        "node_type": node_type,
        "issue_type": issue_type,
        "flow": flow,
        "station": station,
        "discipline": discipline,
        "department": squad[0]["department"] if squad else "",
        "squad": [a.get("slug") for a in squad],
        "model": _model_tier(issue_type, station),
    }
