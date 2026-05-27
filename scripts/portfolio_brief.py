"""cns-portfolio-brief: AI-driven portfolio decision brief."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

from scripts.analyst import _call_claude, _get_api_key, load_pending_suggestions
from scripts.md_parser import read_all_projects


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _latest_export(pattern: str) -> Path | None:
    """Find the most recent file in exports/ matching a glob pattern."""
    exports_dir = Path("exports")
    if not exports_dir.exists():
        return None
    matches = sorted(exports_dir.glob(pattern))
    return matches[-1] if matches else None


# ---------------------------------------------------------------------------
# Portfolio context builder
# ---------------------------------------------------------------------------


def _build_portfolio_context(
    projects: list[tuple[dict, dict]],
    devwatch_events: list[dict],
    pending: list[dict],
) -> str:
    """Build compressed portfolio context string for Claude."""
    lines: list[str] = []

    # Aggregate metadata
    all_meta = [meta for meta, _ in projects]
    total = len(all_meta)
    status_counts = Counter(m.get("status", "unknown") for m in all_meta)
    status_dist = ", ".join(f"{k}({v})" for k, v in sorted(status_counts.items()))

    lines.append("## Portföljöversikt")
    lines.append(f"Datum: {date.today().isoformat()}")
    lines.append(f"Antal projekt: {total}")
    lines.append(f"Status-fördelning: {status_dist}")
    lines.append("")

    # Per-project summary
    lines.append("## Projekt")
    for meta, _ in projects:
        slug = meta.get("slug", "")
        title = meta.get("title", slug)
        status = meta.get("status", "")
        mvp_stage = meta.get("mvp_stage", "")
        updated = meta.get("updated", "")
        roi = meta.get("roi_percent", "")
        # Check if project has pending suggestions
        has_pending = any(p["slug"] == slug for p in pending)
        pending_note = ""
        if has_pending:
            p_item = next(p for p in pending if p["slug"] == slug)
            fields = list(p_item.get("suggestions", {}).keys())
            pending_note = f" | ja ({len(fields)} förslag: {', '.join(fields[:5])})"
        lines.append(
            f"[{slug}] {title} | {status} | {mvp_stage} | roi={roi}% | updated={updated}{pending_note}"
        )
    lines.append("")

    # Devwatch events
    if devwatch_events:
        lines.append("## Senaste aktivitet (devwatch)")
        for event in devwatch_events:
            emeta = event.get("meta", {})
            slug = emeta.get("slug", "")
            changed_fields = emeta.get("changed_fields", [])
            changed_files = [
                f.get("file", "") for f in emeta.get("changed_files", [])
            ]
            lines.append(
                f"[{slug}] Ändrade fält: {', '.join(changed_fields) or '—'} | Ändrade filer: {', '.join(changed_files) or '—'}"
            )
        lines.append("")

    # Pending suggestions summary
    if pending:
        lines.append("## Väntande AI-förslag")
        for p in pending:
            slug = p["slug"]
            fields = list(p.get("suggestions", {}).keys())
            lines.append(f"{slug}: {len(fields)} förslag ({', '.join(fields)})")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


BRIEF_SYSTEM = (
    "Du är en produktstrateg som analyserar en hel projektportfölj. "
    "Du ser beroenden, flaskhalsar och prioriteringar som ägaren missar i det dagliga arbetet. "
    "Returnera ENDAST giltig JSON enligt det schema som specificeras. "
    "Inga förklaringar utanför JSON-strukturen."
)

BRIEF_SCHEMA = """{
  "situation": "2-3 meningar om portföljens nuläge",
  "priorities": [
    {
      "slug": "string",
      "title": "string",
      "reason": "varför detta projekt bör prioriteras just nu",
      "action": "konkret nästa steg"
    }
  ],
  "blockers": [
    {
      "slug": "string",
      "blocker": "vad som blockerar framsteg"
    }
  ],
  "quest_suggestion": {
    "title": "kort questtitel",
    "description": "vad questen ska åstadkomma",
    "target_slug": "vilket projekt questen gäller",
    "estimated_impact": "varför detta quest ger mest värde idag"
  },
  "pending_recommendation": "om det finns pending förslag: godkänn/avvisa X med motivering"
}"""


def _build_brief_user_prompt(context: str) -> str:
    return (
        f"Här är din projektportfölj:\n\n"
        f"---\n{context}\n---\n\n"
        f"Förväntat JSON-svar:\n{BRIEF_SCHEMA}\n\n"
        f"Analysera portföljen. Identifiera de 3 viktigaste prioriteringarna, "
        f"eventuella blockers, och föreslå en quest som ger mest värde idag. "
        f"Om det finns väntande AI-förslag, ge en rekommendation om vilka "
        f"som bör godkännas eller avvisas."
    )


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------


def _parse_brief_response(raw: str) -> dict:
    """Parse and validate the brief JSON response from Claude."""
    import re

    content = raw.strip()
    content = re.sub(r"^```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse brief response: {exc}\nRaw: {content[:500]}")

    if not isinstance(data, dict):
        raise RuntimeError(f"Brief response is not a JSON object: {type(data)}")

    # Validate required keys
    required = {"situation", "priorities", "blockers", "quest_suggestion", "pending_recommendation"}
    for key in required:
        if key not in data:
            raise RuntimeError(f"Missing required key in brief: '{key}'")

    # Validate priorities structure
    if not isinstance(data["priorities"], list):
        raise RuntimeError("'priorities' must be a list")
    for i, p in enumerate(data["priorities"][:3]):
        if not isinstance(p, dict):
            raise RuntimeError(f"Priority at index {i} must be an object")
        for field in ("slug", "title", "reason", "action"):
            if field not in p:
                raise RuntimeError(f"Priority at index {i} missing '{field}'")

    # Validate blockers structure
    if not isinstance(data["blockers"], list):
        raise RuntimeError("'blockers' must be a list")
    for i, b in enumerate(data["blockers"]):
        if not isinstance(b, dict):
            raise RuntimeError(f"Blocker at index {i} must be an object")
        if "slug" not in b or "blocker" not in b:
            raise RuntimeError(f"Blocker at index {i} missing 'slug' or 'blocker'")

    # Validate quest_suggestion structure
    qs = data["quest_suggestion"]
    if not isinstance(qs, dict):
        raise RuntimeError("'quest_suggestion' must be an object")
    for field in ("title", "description", "target_slug", "estimated_impact"):
        if field not in qs:
            raise RuntimeError(f"quest_suggestion missing '{field}'")

    # Limit priorities to max 3
    data["priorities"] = data["priorities"][:3]

    return data


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_portfolio_brief(output_path: Path | None = None) -> dict:
    """Generate an AI-driven portfolio decision brief.

    Args:
        output_path: If set, save brief as JSON to this path.

    Returns:
        Brief dict with situation, priorities, blockers, quest_suggestion,
        pending_recommendation, and generated_at.
    """
    # 1. Read all projects
    projects = read_all_projects()
    if not projects:
        raise RuntimeError("No projects in portfolio — cannot generate brief.")

    # 2. Read latest devwatch
    devwatch_events: list[dict] = []
    devwatch_path = _latest_export("devwatch_*.json")
    if devwatch_path:
        try:
            data = json.loads(devwatch_path.read_text(encoding="utf-8"))
            devwatch_events = data.get("events", [])
        except Exception:
            pass

    # 3. Read pending suggestions
    pending = load_pending_suggestions()

    # 4. Build portfolio context
    context = _build_portfolio_context(projects, devwatch_events, pending)

    # 5. Call Claude
    system_prompt = BRIEF_SYSTEM
    user_prompt = _build_brief_user_prompt(context)
    ai_raw = _call_claude(system_prompt, user_prompt, max_tokens=4096)

    # 6. Parse response
    brief = _parse_brief_response(ai_raw)
    brief["generated_at"] = date.today().isoformat()

    # 7. Optionally save to file
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    return brief