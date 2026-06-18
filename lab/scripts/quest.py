"""Quest workflow — manage active build state for CNS nodes."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import frontmatter

from scripts.md_parser import (
    node_dir,
    node_path,
    read_node,
    write_node,
    _parse_sections,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Required sections in planning/mvp-scope.md
QUEST_SECTIONS = ["Current Slice", "Next Steps", "Not Now"]

# Statuses that are considered "more advanced" than early_mvp
_ADVANCED_STATUSES = {"mvp", "live"}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def mvp_scope_path(slug: str) -> Path:
    """Return path to planning/mvp-scope.md for a node."""
    return node_dir(slug) / "planning" / "mvp-scope.md"


# ---------------------------------------------------------------------------
# Read / write mvp-scope.md
# ---------------------------------------------------------------------------

def read_mvp_scope(slug: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Read planning/mvp-scope.md and return (frontmatter_dict, sections_dict).

    Raises FileNotFoundError if the file does not exist.
    """
    path = mvp_scope_path(slug)
    if not path.exists():
        raise FileNotFoundError(f"mvp-scope.md not found at {path}")

    post = frontmatter.load(str(path))
    meta: dict[str, Any] = dict(post.metadata)
    sections = _parse_sections(post.content)
    return meta, sections


def write_mvp_scope(slug: str, meta: dict[str, Any], sections: dict[str, str]) -> Path:
    """Write planning/mvp-scope.md with the given frontmatter and sections.

    Returns the path that was written to.
    """
    path = mvp_scope_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Render body in canonical section order
    parts: list[str] = []
    for heading in QUEST_SECTIONS:
        content = sections.get(heading, "")
        parts.append(f"## {heading}")
        if content:
            parts.append("")
            parts.append(content)
        parts.append("")
    body = "\n".join(parts).rstrip() + "\n"

    post = frontmatter.Post(body, **meta)
    path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    return path


def new_mvp_scope_template(slug: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Return default frontmatter and empty sections for a new mvp-scope.md."""
    today = date.today().isoformat()
    meta: dict[str, Any] = {
        "slug": slug,
        "quest_started": today,
        "quest_updated": today,
    }
    sections = {heading: "" for heading in QUEST_SECTIONS}
    return meta, sections


# ---------------------------------------------------------------------------
# Quest init logic
# ---------------------------------------------------------------------------

def quest_init(slug: str) -> dict[str, Any]:
    """Initialize quest for a node. Idempotent-safe.

    Returns a dict describing what was done:
        {
            "scope_created": bool,
            "scope_existed": bool,
            "node_updated": bool,
            "changes": list[str],
        }
    """
    result: dict[str, Any] = {
        "scope_created": False,
        "scope_existed": False,
        "node_updated": False,
        "changes": [],
    }

    # Ensure node exists
    ppath = node_path(slug)
    if not ppath.exists():
        raise FileNotFoundError(f"Node '{slug}' not found at {ppath}")

    # --- mvp-scope.md ---
    scope_path = mvp_scope_path(slug)
    if scope_path.exists():
        result["scope_existed"] = True
    else:
        meta, sections = new_mvp_scope_template(slug)
        write_mvp_scope(slug, meta, sections)
        result["scope_created"] = True
        result["changes"].append("Created planning/mvp-scope.md")

    # --- node.md: ensure quest fields ---
    proj_meta, proj_sections, _ = read_node(slug)
    updated = False

    # Add current_slice if missing
    if "current_slice" not in proj_meta:
        proj_meta["current_slice"] = ""
        updated = True
        result["changes"].append("Added current_slice field to node.md")

    # Upgrade status to early_mvp if still at 'idea'
    # (do NOT downgrade a more advanced status)
    current_status = proj_meta.get("status", "idea")
    if current_status == "idea":
        proj_meta["status"] = "early_mvp"
        updated = True
        result["changes"].append("Updated status: idea -> early_mvp")

    if updated:
        proj_meta["updated"] = date.today().isoformat()
        write_node(slug, proj_meta, proj_sections)
        result["node_updated"] = True

    return result


# ---------------------------------------------------------------------------
# Quest sync logic
# ---------------------------------------------------------------------------

def quest_sync(slug: str) -> dict[str, Any]:
    """Sync current_slice from mvp-scope.md back into node.md frontmatter.

    Returns a dict describing what was done.
    """
    result: dict[str, Any] = {"synced": False, "current_slice": ""}

    # Read mvp-scope
    scope_meta, scope_sections = read_mvp_scope(slug)

    # Extract first non-empty line from "Current Slice" as the summary
    current_text = scope_sections.get("Current Slice", "").strip()
    # Use the first line (or first sentence) as the compact slice description
    first_line = ""
    for line in current_text.splitlines():
        line = line.strip()
        if line and not line.startswith("-"):
            first_line = line.rstrip(".")
            break
    # Fallback: if all lines are bullets, join the first few
    if not first_line:
        bullets = [l.strip().lstrip("- ") for l in current_text.splitlines() if l.strip().startswith("-")]
        first_line = "; ".join(bullets[:2]) if bullets else ""

    result["current_slice"] = first_line

    # Update node.md
    proj_meta, proj_sections, _ = read_node(slug)
    old_slice = proj_meta.get("current_slice", "")

    if old_slice != first_line:
        proj_meta["current_slice"] = first_line
        proj_meta["updated"] = date.today().isoformat()
        write_node(slug, proj_meta, proj_sections)
        result["synced"] = True

    return result
