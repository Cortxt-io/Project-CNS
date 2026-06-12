"""Tester för härledningen (scripts/derive_catalog.py) — Del A, skiva 1.

Rena härledare + diff med injicerad data (ingen disk). Verifierar att verkligheten
härleds och att diffen är ärlig om vad v1 inte täcker.
"""
from __future__ import annotations

from scripts import derive_catalog as dc


def _agents():
    return {"agents": [
        {"slug": "backend-utvecklare", "title": "Backend-utvecklare", "status": "active",
         "department": "Engineering"},
        {"slug": "incidentledare", "title": "Incidentledare", "status": "shell",
         "department": "Drift"},
        {"slug": "", "title": "skippad — ingen slug"},  # ska hoppas över
    ]}


def _mcp():
    return {"mcpServers": {"project-cns": {"type": "http", "url": "https://x/mcp"}}}


# -- härledare ---------------------------------------------------------------

def test_derive_from_agents_one_node_per_agent():
    nodes = dc.derive_from_agents(_agents())
    assert set(nodes) == {"backend-utvecklare", "incidentledare"}  # tom slug skippad
    assert nodes["backend-utvecklare"]["type"] == "agent"
    assert nodes["backend-utvecklare"]["status_derived"] == "active"
    assert nodes["backend-utvecklare"]["_source"] == "exports/agents.json"
    assert nodes["backend-utvecklare"]["part_of"] == "agentur"


def test_derive_from_mcp_one_node_per_server():
    nodes = dc.derive_from_mcp(_mcp())
    assert nodes["project-cns"]["type"] == "mcp-server"
    assert nodes["project-cns"]["transport"] == "http"


def test_derive_merges_sources():
    nodes = dc.derive(agents_data=_agents(), mcp_data=_mcp())
    assert "backend-utvecklare" in nodes and "cns-mcp" in nodes  # mcp aliasas till cns-mcp


def test_derive_handles_missing_sources():
    assert dc.derive() == {}
    assert dc.derive(agents_data=None, mcp_data=None) == {}


# -- diff --------------------------------------------------------------------

def test_diff_flags_reality_missing_from_catalog():
    derived = dc.derive(agents_data=_agents())
    catalog = {"cns-core": {"type": "cli"}}  # handkatalog utan agenterna
    report = dc.diff_against_catalog(derived, catalog)
    assert "backend-utvecklare" in report.only_in_reality
    assert "incidentledare" in report.only_in_reality
    assert "cns-core" in report.only_in_catalog


def test_diff_separates_known_phantoms():
    catalog = {"pipeline-intern": {"type": "pipeline"}, "cortxt-landing": {"type": "frontend"}}
    report = dc.diff_against_catalog({}, catalog)
    assert report.phantoms == ["pipeline-intern"]
    assert report.only_in_catalog == ["cortxt-landing"]  # äkta nod, ej phantom


def test_diff_in_both():
    derived = {"project-cns": {"type": "mcp-server"}}
    catalog = {"project-cns": {"type": "mcp-server"}}
    report = dc.diff_against_catalog(derived, catalog)
    assert report.in_both == ["project-cns"]


def test_diff_report_text_renders():
    report = dc.diff_against_catalog(dc.derive(agents_data=_agents()), {"pipeline-intern": {}})
    text = report.as_text()
    assert "SAKNAS i katalogen" in text and "PHANTOM" in text


# -- alias + merge + annoteringsbygge (skiva 2) ------------------------------

def test_derive_aliases_mcp_to_canonical_slug():
    nodes = dc.derive(mcp_data=_mcp())
    assert "cns-mcp" in nodes and "project-cns" not in nodes  # project-cns → cns-mcp
    assert nodes["cns-mcp"]["type"] == "mcp-server"


def test_build_annotations_drops_phantoms_and_retags_children():
    catalog = {
        "pipeline-intern": {"type": "pipeline", "part_of": "cortxt"},
        "cns-devlog": {"type": "pipeline", "part_of": "pipeline-intern", "summary": "loggar"},
        "cns-core": {"type": "cli", "part_of": "infrastructure"},
    }
    ann = dc.build_annotations_from_catalog(catalog)
    assert "pipeline-intern" not in ann                       # attrappen borta
    assert ann["cns-devlog"]["part_of"] == "cortxt"            # om-föräldrad
    assert "pipeline" in ann["cns-devlog"]["tags"]
    assert "intern" in ann["cns-devlog"]["tags"]
    assert ann["cns-core"]["part_of"] == "infrastructure"     # orörd


def test_merge_annotation_wins_semantics_derived_keeps_structure():
    derived = {"cns-mcp": {"type": "mcp-server", "_source": ".mcp.json", "title": "x"}}
    annotations = {"cns-mcp": {"summary": "MCP-servern", "domain": "cortxt", "title": "CNS MCP"}}
    merged = dc.merge(derived, annotations)
    node = merged["cns-mcp"]
    assert node["title"] == "CNS MCP"          # annotering vinner
    assert node["type"] == "mcp-server"        # härlett bidrar struktur
    assert node["_source"] == ".mcp.json"      # härledningsspår överlever
    assert node["summary"] == "MCP-servern"


def test_merge_union_of_slugs():
    merged = dc.merge({"a": {"type": "agent"}}, {"b": {"type": "cli"}})
    assert set(merged) == {"a", "b"}
