"""Tester för derive_layer (scripts/catalog.py) — portföljlager substrate/fog/vertical.

Rena härledare med injicerad data + ett smoke-test mot riktiga catalog.yaml.
Modellen: decisions/portfolio-layers.md.
"""
from __future__ import annotations

from scripts.catalog import derive_layer, catalog_to_meta, load_catalog


def _systems():
    return {
        "cns-core": {"type": "cli", "domain": "cortxt"},
        "cns-triage": {"type": "tool", "domain": "cortxt", "part_of": "cns-core"},
        "agentur": {"type": "service", "domain": "cortxt", "part_of": "infrastructure"},
        "cns-mcp": {"type": "mcp-server", "domain": "cortxt", "part_of": "infrastructure"},
        "interface": {"type": "frontend", "domain": "cortxt", "part_of": "cortxt"},
        "infrastructure": {"type": "infra", "domain": "cortxt", "part_of": "cortxt"},
        "cortxt": {"type": "tool", "domain": "cortxt"},
        "juvahem": {"type": "tool", "domain": "juvahem"},
        "crusade": {"type": "service", "domain": "crusade"},
    }


def test_vertical_is_non_cortxt_domain():
    s = _systems()
    assert derive_layer("juvahem", s) == "vertical"
    assert derive_layer("crusade", s) == "vertical"


def test_substrate_is_core_and_its_part_of_chain():
    s = _systems()
    assert derive_layer("cns-core", s) == "substrate"
    assert derive_layer("cns-triage", s) == "substrate"  # part_of: cns-core


def test_fog_is_everything_else_in_cortxt():
    s = _systems()
    for slug in ("agentur", "cns-mcp", "interface", "infrastructure", "cortxt"):
        assert derive_layer(slug, s) == "fog", slug


def test_no_part_of_cycle_hang():
    s = {"a": {"domain": "cortxt", "part_of": "b"}, "b": {"domain": "cortxt", "part_of": "a"}}
    assert derive_layer("a", s) == "fog"  # cykel → faller igenom till fog, ingen loop


def test_catalog_to_meta_carries_layer():
    systems = load_catalog()
    assert "cns-core" in systems, "catalog.yaml saknar cns-core"
    meta = catalog_to_meta("cns-core", systems["cns-core"], systems)
    assert meta["layer"] == "substrate"


def test_real_catalog_every_system_has_valid_layer():
    systems = load_catalog()
    valid = {"substrate", "fog", "vertical"}
    for slug in systems:
        assert derive_layer(slug, systems) in valid, slug
