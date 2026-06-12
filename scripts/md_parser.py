"""Read and write node Markdown files with YAML frontmatter."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

import frontmatter

# Canonical section order that every node file must follow.
# Product template (legacy — used when kind is None)
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

# Component template — for nodes with kind: component
COMPONENT_SECTIONS = [
    "Syfte",
    "Beroenden",
    "Status",
    "Nästa steg",
    "Risker",
    "Arbetslogg",
    "Anteckningar",
]

# System template — for nodes with kind: system
SYSTEM_SECTIONS = [
    "Syfte/mål",
    "Ingående komponenter",
    "Dataflöde",
    "Hälsa",
    "Systemrisker",
    "Arbetslogg",
    "Anteckningar",
]

# Framework template — for nodes with kind: framework
FRAMEWORK_SECTIONS = [
    "Vision",
    "Ingående system",
    "Karta",
    "Riktning",
    "Principer",
    "Arbetslogg",
    "Anteckningar",
]


def sections_for_kind(kind: str | None) -> list[str]:
    """Return the canonical section list for a given node kind.

    If kind is None (legacy product nodes), returns the product SECTIONS list.
    """
    return {
        "component": COMPONENT_SECTIONS,
        "system": SYSTEM_SECTIONS,
        "framework": FRAMEWORK_SECTIONS,
    }.get(kind, SECTIONS)

NODES_DIR = Path(__file__).resolve().parent.parent / "nodes"


# ---------------------------------------------------------------------------
# Path helpers — single source of truth for node layout
# ---------------------------------------------------------------------------

def node_dir(slug: str) -> Path:
    """Return the folder for a node: nodes/<slug>/"""
    return NODES_DIR / slug


def node_path(slug: str) -> Path:
    """Return the canonical file for a node: nodes/<slug>/node.md"""
    return NODES_DIR / slug / "node.md"


# Subdirectories scaffolded by `cns new`
NODE_SUBDIRS = ["notes", "research", "planning", "exports", "assets"]


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


def _render_body(sections: dict[str, str], kind: str | None = None) -> str:
    """Render sections back into Markdown body in canonical order.

    Sections not in the canonical order for this kind are appended
    at the end (preserving content from migrated nodes).
    """
    canonical = sections_for_kind(kind)
    rendered_headings: set[str] = set()
    parts: list[str] = []

    # First pass: render sections in canonical order
    for heading in canonical:
        content = sections.get(heading, "")
        parts.append(f"## {heading}")
        if content:
            parts.append("")
            parts.append(content)
        parts.append("")  # blank line after each section
        rendered_headings.add(heading)

    # Second pass: append any remaining sections not in canonical order
    for heading, content in sections.items():
        if heading not in rendered_headings:
            parts.append(f"## {heading}")
            if content:
                parts.append("")
                parts.append(content)
            parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def list_node_files() -> list[Path]:
    """Return sorted list of node.md files in the nodes directory."""
    if not NODES_DIR.exists():
        return []
    return sorted(NODES_DIR.glob("*/node.md"))


def read_node(slug: str) -> tuple[dict[str, Any], dict[str, str], str]:
    """Read a single node and return (meta, sections, raw).

    Tunn wrapper ovanpå catalog.yaml (nodmodell-teardown #98). Sanningskällan är
    numera katalogen, inte nodes/<slug>/node.md. `meta` har samma nycklar som förr
    (kind härleds); sections är tomt (prosa bor i decisions/<slug>.md); raw = decisions-text.

    Raises FileNotFoundError om systemet inte finns i katalogen (signaturkompatibelt
    med tidigare beteende).
    """
    from scripts import catalog  # lazy: undvik import-cykler vid modulladdning

    try:
        return catalog.read_node_as_meta(slug)
    except KeyError as exc:
        raise FileNotFoundError(str(exc)) from exc


def read_all_nodes() -> list[tuple[dict[str, Any], dict[str, str]]]:
    """Read all nodes as (meta, sections) tuples — ur catalog.yaml (#98)."""
    from scripts import catalog  # lazy: undvik import-cykler

    return catalog.load_nodes_as_meta()


def write_node(
    slug: str,
    meta: dict[str, Any],
    sections: dict[str, str],
) -> Path:
    """Write a node file with the given frontmatter and sections.

    Returns the path that was written to.
    """
    NODES_DIR.mkdir(parents=True, exist_ok=True)
    path = node_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)

    kind = meta.get("kind")  # None for legacy product nodes
    body = _render_body(sections, kind=kind)
    post = frontmatter.Post(body, **meta)
    path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    return path


def new_node_template(slug: str, kind: str | None = None) -> tuple[dict[str, Any], dict[str, str]]:
    """Return default frontmatter and empty sections for a new node.

    If kind is set, uses the appropriate section template and includes
    kind/stage/part_of/feeds/depends_on in frontmatter.
    If kind is None, uses the legacy product template.
    """
    today = date.today().isoformat()
    section_headings = sections_for_kind(kind)
    sections = {heading: "" for heading in section_headings}

    # Base meta common to all templates
    meta: dict[str, Any] = {
        "title": slug.replace("-", " ").title(),
        "slug": slug,
        "status": "idea",
        "tags": [],
        "summary": None,
        "created": today,
        "updated": today,
    }

    if kind is None:
        # Legacy product template
        meta.update({
            "cost_sek": 0,
            "value_sek": 0,
            "roi_percent": 0,
            "mvp_stage": "hypothesis",
            "family": None,
            "url_live": None,
            "url_repo": None,
        })
    else:
        # Node model template
        meta.update({
            "kind": kind,
            "stage": "idea",
            "part_of": "",
            "feeds": [],
            "depends_on": [],
        })

    return meta, sections


def scaffold_node_dirs(slug: str) -> Path:
    """Create the full folder scaffold for a new node.

    Creates: nodes/<slug>/{notes, research, planning, exports, assets}/
    with placeholder README.md files in notes/ and assets/.
    Returns the node directory path.
    """
    pdir = node_dir(slug)
    for sub in NODE_SUBDIRS:
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


def ensure_node_dirs(slug: str) -> None:
    """Ensure all NODE_SUBDIRS exist for a node. Creates only directories,
    no seed files and no node.md."""
    pdir = node_dir(slug)
    for sub in NODE_SUBDIRS:
        (pdir / sub).mkdir(parents=True, exist_ok=True)


def ensure_all_node_dirs() -> list[str]:
    """Run ensure_node_dirs for all existing nodes.
    Returns list of slugs where directories were created."""
    created: list[str] = []
    for path in list_node_files():
        slug = path.parent.name
        # Check if any subdir was missing before creating
        pdir = node_dir(slug)
        had_missing = any(not (pdir / sub).exists() for sub in NODE_SUBDIRS)
        ensure_node_dirs(slug)
        if had_missing:
            created.append(slug)
    return created


def _seed_if_missing(path: Path, content: str) -> None:
    """Write *content* to *path* only if the file does not already exist."""
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def render_generated_section(slug: str, all_nodes: list[tuple[dict, dict]] | None = None) -> str:
    """Generate 'Ingående komponenter' or 'Ingående system' from part_of relations.

    For system nodes: find all nodes where part_of == slug.
    For framework nodes: find all nodes where part_of == slug, OR where part_of
    points to a system node that has part_of == slug.

    Args:
        slug: The slug of the system/framework node to generate for.
        all_nodes: Optional list of (meta, sections) tuples. If None, reads all.

    Returns:
        Markdown-formatted string for the generated section.
    """
    if all_nodes is None:
        all_nodes = read_all_nodes()

    kind = None
    for meta, _ in all_nodes:
        if meta.get("slug") == slug:
            kind = meta.get("kind")
            break

    if kind not in ("system", "framework"):
        return ""

    # Find direct children (part_of == this slug)
    children = []
    for meta, _ in all_nodes:
        if meta.get("part_of") == slug:
            children.append(meta)

    if kind == "system":
        # List direct children as components
        if not children:
            return "(Inga komponenter ännu.)"
        lines = []
        for child in sorted(children, key=lambda m: m.get("stage", "")):
            c_slug = child.get("slug", "")
            c_stage = child.get("stage", "")
            c_summary = child.get("summary", "")
            line = f"- **{c_slug}** ({c_stage})"
            if c_summary:
                line += f" — {c_summary}"
            lines.append(line)
        return "\n".join(lines)

    # Framework: list direct children (systems) + their components
    if not children:
        return "(Inga system ännu.)"

    lines = []
    for child in sorted(children, key=lambda m: m.get("slug", "")):
        c_slug = child.get("slug", "")
        c_stage = child.get("stage", "")
        c_kind = child.get("kind", "")
        c_summary = child.get("summary", "")
        line = f"- **{c_slug}** ({c_kind}, {c_stage})"
        if c_summary:
            line += f" — {c_summary}"
        lines.append(line)

        # Find sub-children (components of this system)
        sub_children = []
        for meta, _ in all_nodes:
            if meta.get("part_of") == c_slug:
                sub_children.append(meta)
        for sub in sorted(sub_children, key=lambda m: m.get("stage", "")):
            s_slug = sub.get("slug", "")
            s_stage = sub.get("stage", "")
            line = f"  - {s_slug} ({s_stage})"
            lines.append(line)

    return "\n".join(lines)


def render_dataflow_section(slug: str, all_nodes: list[tuple[dict, dict]] | None = None) -> str:
    """Generate 'Dataflöde' section from feeds relations among children.

    For system nodes: find feeds chains among components that are part_of this system.

    Returns:
        Markdown-formatted string describing data flows, or empty string.
    """
    if all_nodes is None:
        all_nodes = read_all_nodes()

    # Find children of this slug
    children = {meta.get("slug"): meta for meta, _ in all_nodes if meta.get("part_of") == slug}
    if not children:
        return ""

    # Find feeds relations among children
    flow_lines = []
    for c_slug, c_meta in sorted(children.items()):
        feeds = c_meta.get("feeds", [])
        for target in feeds:
            if target in children:
                flow_lines.append(f"{c_slug} → {target}")
            elif target:  # feeds outside this system
                flow_lines.append(f"{c_slug} → {target} (extern)")

    if not flow_lines:
        return "(Inga dataflöden mellan ingående komponenter.)"

    return "\n".join(f"- {line}" for line in flow_lines)


def apply_changes(
    meta: dict[str, Any],
    sections: dict[str, str],
    changes: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Apply a validated changes dict (from Perplexity response) to a node.

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
        # Node model fields (Quest A)
        "kind": "kind",
        "stage": "stage",
        "part_of": "part_of",
        "feeds": "feeds",
        "depends_on": "depends_on",
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

    # Risks -> Risk Assessment / Risker / Systemrisker
    if changes.get("risks"):
        risk_lines = []
        for risk in changes["risks"]:
            prob = risk.get("probability")
            imp = risk.get("impact")
            mitigation = risk.get("mitigation")
            if prob is not None and imp is not None:
                # New format: P2 × I4 = 8/25
                score = risk['score']
                line = f"- **{risk['category'].title()}** (P{prob} × I{imp} = {score}/25): {risk['description']}"
                if mitigation:
                    line += f" Mitigation: {mitigation}"
            else:
                # Legacy format: score 3/5
                line = f"- **{risk['category'].title()}** (score {risk['score']}/5): {risk['description']}"
            risk_lines.append(line)
        new_risks = "\n".join(risk_lines)
        # Write to whichever risk section exists for this node kind
        for key in ("Risk Assessment", "Risker", "Systemrisker"):
            if key in sections:
                sections[key] = new_risks
                break
        else:
            sections["Risk Assessment"] = new_risks

    # Notes append
    if changes.get("notes_append"):
        existing = sections.get("Notes", "").strip()
        append_text = changes["notes_append"]
        sections["Notes"] = (
            f"{existing}\n\n{append_text}".strip() if existing else append_text
        )

    return meta, sections
