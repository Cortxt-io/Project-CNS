"""Cortxt MCP Server – exposes Cortxt data as tools for Qoder/Claude Desktop.

Communicates via MCP protocol over stdio. Provides 5 tools:
  - cortxt_list_active_quests
  - cortxt_get_quest
  - cortxt_complete_quest
  - cortxt_list_projects
  - cortxt_get_project
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repo root is on path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("cortxt")


@mcp.tool()
def cortxt_list_active_quests() -> list[dict]:
    """List all quests with status 'active' or 'in_progress'."""
    from scripts.quest_manager import list_quests
    active = list_quests(status="active")
    in_progress = list_quests(status="in_progress")
    return active + in_progress


@mcp.tool()
def cortxt_get_quest(quest_id: str) -> dict:
    """Get full quest details including project context."""
    from scripts.quest_manager import get_quest
    from scripts.md_parser import read_project
    quest = get_quest(quest_id)
    if not quest:
        return {"error": f"Quest {quest_id} not found"}
    # Add project context
    try:
        meta, sections, _ = read_project(quest["slug"])
        quest["project_context"] = {
            "meta": meta,
            "summary": meta.get("summary", ""),
            "layer": meta.get("layer", ""),
            "pipeline": meta.get("pipeline", ""),
        }
    except Exception:
        pass
    return quest


@mcp.tool()
def cortxt_complete_quest(quest_id: str, result_summary: str) -> dict:
    """Mark a quest as completed with a result summary."""
    from scripts.quest_manager import transition_quest, update_quest
    from app.git_ops import push_file_immediately
    from scripts.quest_manager import QUESTS_DIR
    quest = transition_quest(quest_id, "completed")
    quest = update_quest(quest_id, result_summary=result_summary)
    # Push to GitHub
    quest_path = QUESTS_DIR / f"{quest_id}.json"
    push_file_immediately(quest_path, f"cns-vault: complete quest {quest_id}")
    return quest


@mcp.tool()
def cortxt_list_projects() -> list[dict]:
    """List all CNS projects with metadata."""
    from scripts.md_parser import read_all_projects
    result = []
    for meta, _ in read_all_projects():
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
    from scripts.md_parser import read_project, project_dir
    try:
        meta, sections, _ = read_project(slug)
        # Read planning files
        planning = {}
        pdir = project_dir(slug) / "planning"
        if pdir.exists():
            for f in sorted(pdir.glob("*.md")):
                if f.name.lower() != "readme.md":
                    planning[f.name] = f.read_text(encoding="utf-8")
        return {"meta": meta, "sections": sections, "planning": planning}
    except FileNotFoundError:
        return {"error": f"Project {slug} not found"}


if __name__ == "__main__":
    mcp.run()
