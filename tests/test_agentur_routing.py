"""Verifiering av agenturens routing-modell (scripts/agentur_routing.py, #90).

Ren logik — agenter OCH agentur-konfig injiceras (ingen disk behövs). Körs fristående
(``python tests/test_agentur_routing.py``) ELLER under pytest.

Skiva 2: mekanismen är generisk, innehållet bor i per-agentur-konfig. Testet bevisar att
SAMMA route() ger produktutvecklings-flöden för en produkt-agentur OCH helt andra flöden för
en research-agentur — utan kodändring (research-venturet är bara en annan konfig).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import agentur_routing as ar  # noqa: E402
from scripts.agentur_routing import resolve_agentur, route  # noqa: E402

# --- Produktutvecklings-agenturen (= config/agenturer/produktutveckling.json, delmängd) ---
PRODUKT = {
    "slug": "produktutveckling",
    "domains": ["cortxt", "shopify-venture", "agency"],
    "flows": {
        "spike": ["discovery"],
        "bug": ["delivery", "review"],
        "story": ["definition", "delivery", "review"],
        "epic": ["discovery", "definition", "review", "retro"],
    },
    "default_flow": ["definition", "delivery", "review"],
    "disciplines": {"frontend": "Frontend", "service": "Backend", "infra": "Infra"},
    "model_tiers": {
        "chore": "haiku", "bug": "sonnet", "story": "sonnet",
        "epic": {"discovery": "opus", "_default": "sonnet"}, "_default": "sonnet",
    },
}

# --- Ett HELT annat venture: ren research-agentur med egna stationer/discipliner/flöden ---
RESEARCH = {
    "slug": "research-venture",
    "domains": ["research-venture"],
    "flows": {"spike": ["fraga", "metod", "fynd"], "story": ["fraga", "metod", "fynd", "syntes"]},
    "default_flow": ["fraga", "fynd"],
    "disciplines": {"dataset": "Data", "ai-model": "Research"},
    "model_tiers": {"spike": "sonnet", "story": {"syntes": "opus", "_default": "sonnet"}, "_default": "sonnet"},
}

AGENTS = [
    {"slug": "frontend-utvecklare", "department": "Engineering", "sub_department": "Frontend", "status": "active"},
    {"slug": "ux-designer", "department": "Engineering", "sub_department": "Frontend", "status": "shell"},
    {"slug": "backend-utvecklare", "department": "Engineering", "sub_department": "Backend", "status": "active"},
    {"slug": "forskningsledare", "department": "R&D", "sub_department": "Research", "status": "active"},
]


def test_resolve_agentur_by_domain() -> None:
    pool = [PRODUKT, RESEARCH]
    assert resolve_agentur(domain="cortxt", agenturer=pool)["slug"] == "produktutveckling"
    assert resolve_agentur(domain="research-venture", agenturer=pool)["slug"] == "research-venture"
    assert resolve_agentur(slug="research-venture", agenturer=pool)["slug"] == "research-venture"
    # Okänd domän → första konfigurerade (default)
    assert resolve_agentur(domain="okänd", agenturer=pool)["slug"] == "produktutveckling"
    # Tom pool → builtin-default (kraschar ej)
    assert resolve_agentur(agenturer=[])["slug"] == "(builtin-default)"


def test_route_produkt_agentur() -> None:
    r = route("frontend", "bug", agentur=PRODUKT, agents=AGENTS)
    assert r["flow"] == ["delivery", "review"] and r["station"] == "delivery"
    assert r["discipline"] == "Frontend" and r["squad"] == ["frontend-utvecklare"]
    assert r["model"] == "sonnet" and r["agentur"] == "produktutveckling"
    # Mekaniskt → haiku; epic discovery → opus
    assert route("infra", "chore", agentur=PRODUKT, agents=AGENTS)["model"] == "haiku"
    assert route("frontend", "epic", agentur=PRODUKT, agents=AGENTS)["model"] == "opus"


def test_route_research_agentur_same_mechanism() -> None:
    # SAMMA route(), annan konfig → helt andra stationer/flöden. Ingen kodändring.
    r = route("ai-model", "spike", agentur=RESEARCH, agents=AGENTS)
    assert r["flow"] == ["fraga", "metod", "fynd"] and r["station"] == "fraga"
    assert r["discipline"] == "Research" and r["squad"] == ["forskningsledare"]
    assert r["agentur"] == "research-venture"
    # research-story: syntes-stationen → opus
    assert route("dataset", "story", station="syntes", agentur=RESEARCH, agents=AGENTS)["model"] == "opus"


def test_degrades_without_config_or_agents() -> None:
    # Ingen agentur-konfig injicerad och tom roster → builtin-default + tom squad, kraschar ej.
    r = route("frontend", "bug", agentur=ar._BUILTIN_AGENTUR, agents=[])
    assert r["flow"] == ar.DEFAULT_FLOW and r["squad"] == [] and r["model"] == "sonnet"


def test_real_config_loads() -> None:
    # Skarpa konfigfilen ska gå att läsa och betjäna cortxt-domänen.
    cfg = resolve_agentur(domain="cortxt")
    assert cfg["slug"] == "produktutveckling"
    assert cfg["flows"]["bug"] == ["delivery", "review"]


if __name__ == "__main__":
    test_resolve_agentur_by_domain()
    test_route_produkt_agentur()
    test_route_research_agentur_same_mechanism()
    test_degrades_without_config_or_agents()
    test_real_config_loads()
    print("OK — agentur_routing skiva 2: per-agentur-konfig + research-venture (samma mekanism) gröna")
