"""Domänkärna: katalognoder (catalog.yaml). Transport-fri, läs-only."""
from __future__ import annotations

from typing import Any


def project(action: str, **kw: Any) -> Any:
    if action == "list":
        from scripts.md_parser import read_all_nodes

        out = []
        for meta, _ in read_all_nodes():
            out.append(
                {
                    "slug": meta.get("slug"),
                    "title": meta.get("title"),
                    "kind": meta.get("kind"),
                    "type": meta.get("type"),
                    "domain": meta.get("domain"),
                    "part_of": meta.get("part_of"),
                    "summary": meta.get("summary"),
                    "owner_agent": meta.get("owner_agent"),
                }
            )
        return out

    if action == "get":
        from scripts.md_parser import read_node

        try:
            meta, sections, _ = read_node(kw["slug"])
            return {"meta": meta, "sections": sections}
        except FileNotFoundError:
            return {"error": f"Project '{kw['slug']}' not found in catalog"}

    raise ValueError(f"okänd project-action: {action}")
