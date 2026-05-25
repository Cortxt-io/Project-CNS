"""Export project data to JSON format."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from scripts.md_parser import read_all_projects

EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"


def _extract_audience(section_text: str, label: str) -> str:
    """Extract a labelled audience from the Target Audience section."""
    for line in section_text.splitlines():
        if label in line:
            return line.split(":", 1)[-1].strip().strip("*")
    return ""


def _list_items(section_text: str) -> list[str]:
    """Return bullet-list items as a list of strings."""
    items = []
    for line in section_text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
    return items


def _top_risk(section_text: str) -> str:
    """Return the first risk line from Risk Assessment."""
    for line in section_text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            return line[2:].strip()
    return ""


def export_json(output_path: Optional[Path] = None) -> Path:
    """Generate exports/projects.json from all project files.

    Returns the path to the generated file.
    """
    if output_path is None:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = EXPORTS_DIR / "projects.json"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    projects = read_all_projects()

    project_list = []
    for meta, sections in projects:
        project_list.append({
            "slug": meta.get("slug", ""),
            "title": meta.get("title", ""),
            "status": meta.get("status", ""),
            "mvp_stage": meta.get("mvp_stage", ""),
            "cost_sek": meta.get("cost_sek", 0),
            "value_sek": meta.get("value_sek", 0),
            "roi_percent": meta.get("roi_percent", 0),
            "tags": meta.get("tags", []),
            "created": str(meta.get("created", "")),
            "updated": str(meta.get("updated", "")),
            "summary": meta.get("summary", ""),
            "family": meta.get("family", ""),
            "url_live": meta.get("url_live", ""),
            "url_repo": meta.get("url_repo", ""),
            "current_slice": meta.get("current_slice", ""),
            "problem": sections.get("Problem", "").strip(),
            "solution": sections.get("Solution", "").strip(),
            "primary_audience": _extract_audience(sections.get("Target Audience", ""), "Primary"),
            "assumptions": _list_items(sections.get("Assumptions to Validate", "")),
            "mvp_steps": _list_items(sections.get("MVP Steps", "")),
            "top_risk": _top_risk(sections.get("Risk Assessment", "")),
        })

    payload = {
        "exported_at": datetime.now().isoformat(),
        "version": "1.0",
        "projects": project_list,
    }

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return output_path
