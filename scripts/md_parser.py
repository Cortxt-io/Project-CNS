"""Read and write project Markdown files with YAML frontmatter."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

import frontmatter

# Canonical section order that every project file must follow.
SECTIONS = [
    "Problem",
    "Solution",
    "Target Audience",
    "Assumptions to Validate",
    "Why Buy Instead of Build?",
    "MVP Steps",
    "Cost Estimate",
    "Value Estimate",
    "ROI",
    "Risk Assessment",
    "Timeline",
    "Notes",
]

PROJECTS_DIR = Path(__file__).resolve().parent.parent / "projects"


# ---------------------------------------------------------------------------
# Path helpers — single source of truth for project layout
# ---------------------------------------------------------------------------

def project_dir(slug: str) -> Path:
    """Return the folder for a project: projects/<slug>/"""
    return PROJECTS_DIR / slug


def project_path(slug: str) -> Path:
    """Return the canonical file for a project: projects/<slug>/project.md"""
    return PROJECTS_DIR / slug / "project.md"


# Subdirectories scaffolded by `cns new`
PROJECT_SUBDIRS = ["notes", "research", "planning", "exports", "assets"]


def _parse_sections(body: str) -> dict[str, str]:
    """Split the Markdown body into a dict keyed by section heading."""
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []

    for line in body.splitlines():
        if line.startswith("## "):
            # Store previous section
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current = line[3:].strip()
            lines = []
        else:
            lines.append(line)

    # Store the last section
    if current is not None:
        sections[current] = "\n".join(lines).strip()

    return sections


def _render_body(sections: dict[str, str]) -> str:
    """Render sections back into Markdown body in canonical order."""
    parts: list[str] = []
    for heading in SECTIONS:
        content = sections.get(heading, "")
        parts.append(f"## {heading}")
        if content:
            parts.append("")
            parts.append(content)
        parts.append("")  # blank line after each section
    return "\n".join(parts).rstrip() + "\n"


def list_project_files() -> list[Path]:
    """Return sorted list of project.md files in the projects directory."""
    if not PROJECTS_DIR.exists():
        return []
    return sorted(PROJECTS_DIR.glob("*/project.md"))


def read_project(slug: str) -> tuple[dict[str, Any], dict[str, str], str]:
    """Read a project file and return (frontmatter_dict, sections_dict, raw_content).

    Raises FileNotFoundError if the project does not exist.
    """
    path = project_path(slug)
    if not path.exists():
        raise FileNotFoundError(f"Project '{slug}' not found at {path}")

    post = frontmatter.load(str(path))
    meta: dict[str, Any] = dict(post.metadata)
    sections = _parse_sections(post.content)
    raw = path.read_text(encoding="utf-8")
    return meta, sections, raw


def read_all_projects() -> list[tuple[dict[str, Any], dict[str, str]]]:
    """Read all project files. Returns list of (frontmatter, sections) tuples."""
    results = []
    for path in list_project_files():
        post = frontmatter.load(str(path))
        meta = dict(post.metadata)
        sections = _parse_sections(post.content)
        results.append((meta, sections))
    return results


def write_project(
    slug: str,
    meta: dict[str, Any],
    sections: dict[str, str],
) -> Path:
    """Write a project file with the given frontmatter and sections.

    Returns the path that was written to.
    """
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    path = project_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)

    body = _render_body(sections)
    post = frontmatter.Post(body, **meta)
    path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    return path


def new_project_template(slug: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Return default frontmatter and empty sections for a new project."""
    today = date.today().isoformat()
    meta: dict[str, Any] = {
        "title": slug.replace("-", " ").title(),
        "slug": slug,
        "status": "idea",
        "tags": [],
        "cost_sek": 0,
        "value_sek": 0,
        "roi_percent": 0,
        "mvp_stage": "hypothesis",
        "summary": None,
        "family": None,
        "url_live": None,
        "url_repo": None,
        "created": today,
        "updated": today,
    }
    sections = {heading: "" for heading in SECTIONS}
    return meta, sections


def scaffold_project_dirs(slug: str) -> Path:
    """Create the full folder scaffold for a new project.

    Creates: projects/<slug>/{notes, research, planning, exports, assets}/
    with placeholder README.md files in notes/ and assets/.
    Returns the project directory path.
    """
    pdir = project_dir(slug)
    for sub in PROJECT_SUBDIRS:
        (pdir / sub).mkdir(parents=True, exist_ok=True)

    # Placeholder READMEs so empty dirs survive git/OneDrive sync
    for sub in ("notes", "assets"):
        readme = pdir / sub / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# {slug} / {sub}\n\nAdd {sub} files here.\n",
                encoding="utf-8",
            )

    # Seed files for research and planning
    _seed_if_missing(pdir / "research" / "sources.md", f"# {slug} / sources\n")
    _seed_if_missing(pdir / "research" / "market-notes.md", f"# {slug} / market notes\n")
    _seed_if_missing(pdir / "planning" / "roadmap.md", f"# {slug} / roadmap\n")
    _seed_if_missing(pdir / "planning" / "decisions.md", f"# {slug} / decisions\n")

    return pdir


def ensure_project_dirs(slug: str) -> None:
    """Ensure all PROJECT_SUBDIRS exist for a project. Creates only directories,
    no seed files and no project.md."""
    pdir = project_dir(slug)
    for sub in PROJECT_SUBDIRS:
        (pdir / sub).mkdir(parents=True, exist_ok=True)


def ensure_all_project_dirs() -> list[str]:
    """Run ensure_project_dirs for all existing projects.
    Returns list of slugs where directories were created."""
    created: list[str] = []
    for path in list_project_files():
        slug = path.parent.name
        # Check if any subdir was missing before creating
        pdir = project_dir(slug)
        had_missing = any(not (pdir / sub).exists() for sub in PROJECT_SUBDIRS)
        ensure_project_dirs(slug)
        if had_missing:
            created.append(slug)
    return created


def _seed_if_missing(path: Path, content: str) -> None:
    """Write *content* to *path* only if the file does not already exist."""
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def apply_changes(
    meta: dict[str, Any],
    sections: dict[str, str],
    changes: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Apply a validated changes dict (from Perplexity response) to a project.

    Only non-null values in changes are applied.  Returns updated (meta, sections).
    """
    # Direct frontmatter field mappings
    fm_fields = {
        "title": "title",
        "status": "status",
        "tags": "tags",
        "cost_sek": "cost_sek",
        "value_sek": "value_sek",
        "roi_percent": "roi_percent",
        "mvp_stage": "mvp_stage",
        "summary": "summary",
        "family": "family",
        "url_live": "url_live",
        "url_repo": "url_repo",
    }
    for src, dst in fm_fields.items():
        val = changes.get(src)
        if val is not None:
            meta[dst] = val

    # updated_at -> updated
    if changes.get("updated_at"):
        meta["updated"] = changes["updated_at"]

    # Target Audience section
    audiences = []
    if changes.get("primary_audience"):
        audiences.append(f"**Primary:** {changes['primary_audience']}")
    if changes.get("secondary_audience"):
        audiences.append(f"**Secondary:** {changes['secondary_audience']}")
    if audiences:
        existing = sections.get("Target Audience", "").strip()
        sections["Target Audience"] = "\n\n".join(audiences) if not existing else existing + "\n\n" + "\n\n".join(audiences)

    # Why Buy Instead of Build?
    if changes.get("why_buy_not_build"):
        items = [f"- {item}" for item in changes["why_buy_not_build"]]
        sections["Why Buy Instead of Build?"] = "\n".join(items)

    # Risks -> Risk Assessment
    if changes.get("risks"):
        risk_lines = []
        for risk in changes["risks"]:
            risk_lines.append(
                f"- **{risk['category'].title()}** (score {risk['score']}/5): {risk['description']}"
            )
        new_risks = "\n".join(risk_lines)
        sections["Risk Assessment"] = new_risks

    # Notes append
    if changes.get("notes_append"):
        existing = sections.get("Notes", "").strip()
        append_text = changes["notes_append"]
        sections["Notes"] = (
            f"{existing}\n\n{append_text}".strip() if existing else append_text
        )

    return meta, sections
