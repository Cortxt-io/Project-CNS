"""Project (node) tools: list all, get full context."""

from __future__ import annotations

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def cortxt_list_projects() -> list[dict]:
        """List all CNS projects with metadata."""
        from scripts.md_parser import read_all_nodes
        result = []
        for meta, _ in read_all_nodes():
            result.append({
                "slug": meta.get("slug"),
                "title": meta.get("title"),
                "status": meta.get("status"),
                "layer": meta.get("layer"),
                "pipeline": meta.get("pipeline"),
                "summary": meta.get("summary"),
            })
        return result

    @mcp.tool()
    def cortxt_get_project(slug: str) -> dict:
        """Get full project context including sections and planning files."""
        from scripts.md_parser import read_node, node_dir
        try:
            meta, sections, _ = read_node(slug)
            # Read planning files
            planning = {}
            pdir = node_dir(slug) / "planning"
            if pdir.exists():
                for f in sorted(pdir.glob("*.md")):
                    if f.name.lower() != "readme.md":
                        planning[f.name] = f.read_text(encoding="utf-8")
            return {"meta": meta, "sections": sections, "planning": planning}
        except FileNotFoundError:
            return {"error": f"Project {slug} not found"}
