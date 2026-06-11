"""Verifiering av agenturens routing-modell (scripts/agentur_routing.py, #90 första skivan).

Ren logik — ingen agents.json/disk behövs (agenter injiceras). Körs fristående
(``python tests/test_agentur_routing.py``) ELLER under pytest.

Testar att route() väljer rätt flöde (ur issue.type), rätt disciplin/squad (ur node.type)
och rätt modellnivå (ur typ+station) — och degraderar tyst på okänt.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.agentur_routing import route, _model_tier  # noqa: E402

# Liten agent-roster (= exports/agents.json-form, fältdelmängd).
_AGENTS = [
    {"slug": "frontend-utvecklare", "department": "Engineering", "sub_department": "Frontend", "status": "active"},
    {"slug": "ux-designer", "department": "Engineering", "sub_department": "Frontend", "status": "shell"},
    {"slug": "backend-utvecklare", "department": "Engineering", "sub_department": "Backend", "status": "active"},
    {"slug": "sre", "department": "Platform", "sub_department": "Infra", "status": "shell"},
]


def test_flow_by_type() -> None:
    assert route("frontend", "spike", agents=_AGENTS)["flow"] == ["discovery"]
    assert route("frontend", "bug", agents=_AGENTS)["flow"] == ["delivery", "review"]
    assert route("frontend", "story", agents=_AGENTS)["flow"] == ["definition", "delivery", "review"]
    assert route("frontend", "epic", agents=_AGENTS)["flow"] == ["discovery", "definition", "review", "retro"]
    # Okänd typ → DEFAULT_FLOW (story-likt)
    assert route("frontend", "mystery", agents=_AGENTS)["flow"] == ["definition", "delivery", "review"]


def test_station_defaults_to_first_in_flow() -> None:
    assert route("frontend", "bug", agents=_AGENTS)["station"] == "delivery"
    assert route("frontend", "epic", agents=_AGENTS)["station"] == "discovery"
    # Explicit station respekteras
    assert route("frontend", "epic", station="retro", agents=_AGENTS)["station"] == "retro"


def test_discipline_and_squad_from_node_type() -> None:
    r = route("frontend", "story", agents=_AGENTS)
    assert r["discipline"] == "Frontend"
    assert r["department"] == "Engineering"
    # Aktiva först: frontend-utvecklare (active), ux-designer (shell) faller bort när active finns
    assert r["squad"] == ["frontend-utvecklare"]

    r2 = route("service", "bug", agents=_AGENTS)
    assert r2["discipline"] == "Backend" and r2["squad"] == ["backend-utvecklare"]

    # Disciplin utan aktiva → fallback på alla i disciplinen (sre är shell)
    r3 = route("infra", "chore", agents=_AGENTS)
    assert r3["discipline"] == "Infra" and r3["squad"] == ["sre"]

    # Okänd node.type → tom disciplin/squad, kraschar ej
    r4 = route("okänd-typ", "story", agents=_AGENTS)
    assert r4["discipline"] == "" and r4["squad"] == [] and r4["department"] == ""


def test_model_tier() -> None:
    assert route("infra", "chore", agents=_AGENTS)["model"] == "haiku"      # mekaniskt
    assert route("frontend", "story", agents=_AGENTS)["model"] == "sonnet"  # omdöme
    assert route("frontend", "epic", station="discovery", agents=_AGENTS)["model"] == "opus"   # syntes
    assert route("frontend", "epic", station="delivery", agents=_AGENTS)["model"] == "sonnet"  # delivery på epic
    # Fallbacks
    assert _model_tier("bug", "delivery") == "sonnet"       # station-oberoende fallback
    assert _model_tier("okänd", None) == "sonnet"           # default


def test_degrades_without_agents() -> None:
    r = route("frontend", "bug", agents=[])  # tom roster
    assert r["squad"] == [] and r["flow"] == ["delivery", "review"] and r["model"] == "sonnet"


if __name__ == "__main__":
    test_flow_by_type()
    test_station_defaults_to_first_in_flow()
    test_discipline_and_squad_from_node_type()
    test_model_tier()
    test_degrades_without_agents()
    print("OK — agentur_routing: flöde + disciplin/squad + modellnivå + degradering gröna")
