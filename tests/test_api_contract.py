"""Kontraktet mellan CNS och app.cortxt.io — de fyra endpoints som faktiskt har en konsument.

Sömmen är `cortxt/apps/app/src/lib/cns.js` (exakt fyra funktioner). Allt annat i `lab/app/server.py`
saknar anropare och revs 2026-07-13. Det här testet är beviset att rivningen inte tog något som
appen läser.

Formen pinnas mot inspelade svar i `tests/golden/`, hämtade från drift innan rivningen. Byte-för-byte
går inte — svaren bär tidsstämplar. Det som måste överleva är **fälten frontenden läser**.

Spela in på nytt (efter rivning) och kör testet igen: samma fält ⇒ appen överlever.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

GOLDEN = Path(__file__).parent / "golden"

# Vad cns.js faktiskt läser. Källa: cortxt/apps/app/src/lib/cns.js:11-14, 44.
CONTRACT = {
    # fetchCommandCenter() → Cockpit + Sidebar (useCommandCenter.js)
    "command-center": ["missions", "sitrep", "logistics", "orders", "command", "freshness",
                       "infra", "verticals"],
    # fetchVertical(slug) → pages/Vertical.jsx
    "vertical-orgkomp": ["slug", "vertical", "roadmap"],
    # fetchGraph(domain) → returnerar data.nodes ?? []
    "nodes-orgkomp": ["version", "nodes", "agents", "edges"],
    # fetchCookbook(slug)
    "cookbook-orgkomp": ["slug", "steps"],
}

# Grafen behöver relationerna intakta — den normaliserar inte (cns.js:40-41).
NODE_GRAPH_FIELDS = ["part_of", "feeds", "depends_on", "kind"]


def load(name: str) -> dict:
    path = GOLDEN / f"{name}.json"
    if not path.exists():
        pytest.skip(f"golden saknas: {path.name} — spela in med scripts/record_golden.py")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("name,keys", CONTRACT.items())
def test_endpoint_keeps_its_top_level_fields(name, keys):
    payload = load(name)
    missing = [k for k in keys if k not in payload]
    assert not missing, f"{name}: frontenden läser {missing}, svaret saknar dem"


def test_graph_nodes_keep_their_relations():
    """`fetchGraph` matar @cortxt/graph rått — tappas relationerna ritas ingen graf."""
    nodes = load("nodes-orgkomp")["nodes"]
    assert nodes, "nodes[] är tom — grafen skulle rendera tomt"
    for field in NODE_GRAPH_FIELDS:
        assert any(field in n for n in nodes), f"ingen nod bär {field!r}"
