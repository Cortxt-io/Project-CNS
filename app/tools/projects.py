"""Project (node) tools: list all catalog entries, get one node's metadata.

These tools expose the catalog.yaml-backed node/component model under the
stable connector names ``cortxt_list_projects`` / ``cortxt_get_project``.
The legacy fields ``status``, ``layer``, ``pipeline`` have been removed —
they were delegated to the board (GitHub Projects/Linear) and no longer live
in the catalog.  Planning-file reads were also removed: the ``nodes/`` directory
was torn down in the nodmodel-teardown (#98/#101).
"""

from __future__ import annotations

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_list_projects() -> list[dict]:
        """List all CNS catalog entries (components/systems/frameworks) with metadata.

        Returns slug, title, kind, type, domain, part_of, summary and owner_agent
        for every entry in catalog.yaml.
        """
        from scripts.md_parser import read_all_nodes
        result = []
        for meta, _ in read_all_nodes():
            result.append({
                "slug": meta.get("slug"),
                "title": meta.get("title"),
                "kind": meta.get("kind"),
                "type": meta.get("type"),
                "domain": meta.get("domain"),
                "part_of": meta.get("part_of"),
                "summary": meta.get("summary"),
                "owner_agent": meta.get("owner_agent"),
            })
        return result

    @mcp.tool()
    def cortxt_get_project(slug: str) -> dict:
        """Get metadata for a single CNS catalog entry by slug.

        Returns the full meta dict from catalog.yaml plus any prose from
        decisions/<slug>.md (the sections dict; empty if no decision record exists).
        """
        from scripts.md_parser import read_node
        try:
            meta, sections, _ = read_node(slug)
            return {"meta": meta, "sections": sections}
        except FileNotFoundError:
            return {"error": f"Project '{slug}' not found in catalog"}
