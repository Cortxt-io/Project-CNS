"""cns-analyze: AI-driven analysis of node.md files via Anthropic Claude."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from scripts.md_parser import apply_changes, read_node
from scripts.validator import (
    VALID_KINDS,
    VALID_MVP_STAGES,
    VALID_RISK_CATEGORIES,
    VALID_STAGES,
    VALID_STATUSES,
)

ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-5"

# Fields the analyst may propose for kind-aware nodes (component/system/framework)
NODE_MODEL_FIELDS = {
    "stage", "status", "risks", "summary",
}

# Legacy fields only proposed for product nodes (kind=None)
LEGACY_FIELDS = {
    "mvp_stage", "status", "current_slice", "roi_percent",
    "value_sek", "cost_sek", "risks", "summary",
}


def _allowed_fields_for(kind: str | None) -> set[str]:
    """Return the set of analyst-proposable fields based on node kind."""
    if kind is not None:
        return NODE_MODEL_FIELDS
    return LEGACY_FIELDS

console = Console()


# ---------------------------------------------------------------------------
# API key
# ---------------------------------------------------------------------------


def _get_api_key() -> str:
    load_dotenv()
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key == "your_key_here":
        raise RuntimeError(
            "Anthropic API key not configured. "
            "Add ANTHROPIC_API_KEY to .env to use cns analyze."
        )
    return key


# ---------------------------------------------------------------------------
# Anthropic Claude caller
# ---------------------------------------------------------------------------


def _call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
    api_key = _get_api_key()

    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
    }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    try:
        resp = requests.post(
            ANTHROPIC_ENDPOINT, json=payload, headers=headers, timeout=60
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Anthropic API request failed: {exc}")

    if resp.status_code != 200:
        raise RuntimeError(
            f"Anthropic API error {resp.status_code}: {resp.text}"
        )

    data = resp.json()
    try:
        content = data["content"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected Anthropic response structure: {exc}")

    content = content.strip()

    # Strip markdown code fences if present
    content = re.sub(r"^```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)

    if not content:
        raise RuntimeError("Anthropic returned empty content.")

    return content.strip()


# ---------------------------------------------------------------------------
# Node context reader
# ---------------------------------------------------------------------------


def _get_devwatch_context(slug: str) -> str:
    """Get recent devwatch events for a specific node slug.

    First tries GitHub (for Railway/production), falls back to local exports/.
    Returns formatted string of recent changes, or empty string if none found.
    """
    devwatch_data = None

    # Try GitHub first (production environment)
    try:
        from app.git_ops import read_file_from_github

        raw = read_file_from_github(
            "nodes/project-vault-dashboard/dashboard/data/devwatch_latest.json"
        )
        if raw:
            devwatch_data = json.loads(raw)
    except Exception:
        pass

    # Fall back to local exports/
    if devwatch_data is None:
        exports_dir = Path("exports")
        local_files = (
            sorted(exports_dir.glob("devwatch_*.json"))
            if exports_dir.exists()
            else []
        )
        if local_files:
            try:
                devwatch_data = json.loads(
                    local_files[-1].read_text(encoding="utf-8")
                )
            except Exception:
                pass

    if not devwatch_data:
        return ""

    # Filter events for this slug
    events = devwatch_data.get("events", [])
    slug_events = [e for e in events if e.get("meta", {}).get("slug") == slug]

    if not slug_events:
        return ""

    # Format the most recent event
    event = slug_events[-1]
    meta = event.get("meta", {})
    parts: list[str] = []

    exported_at = devwatch_data.get("exported_at", "")
    if exported_at:
        parts.append(f"Senaste devwatch-körning: {exported_at[:10]}")

    changed_fields = meta.get("changed_fields", [])
    if changed_fields:
        parts.append(f"Ändrade frontmatter-fält: {', '.join(changed_fields)}")

    changed_files = meta.get("changed_files", [])
    if changed_files:
        file_names = [cf.get("file", "") for cf in changed_files]
        parts.append(f"Ändrade filer: {', '.join(file_names)}")

        # Include section changes from each file
        for cf in changed_files:
            sections = cf.get("sections", [])
            if sections:
                parts.append(
                    f"  {cf['file']}: ändrade sektioner: {', '.join(sections)}"
                )

    raw_content = event.get("rawContent", "")
    if raw_content:
        # Truncate to avoid token overflow
        if len(raw_content) > 1000:
            raw_content = raw_content[:1000] + "\n...[truncated]"
        parts.append(f"\nDiff-innehåll:\n{raw_content}")

    return "\n".join(parts)


def _read_node_context(slug: str) -> str:
    """Read and concatenate all node Markdown files as context."""
    from scripts.md_parser import node_dir

    pdir = node_dir(slug)
    parts: list[str] = []

    files_to_read: list[tuple[Path, str]] = []
    # node.md always first
    node_md = pdir / "node.md"
    if node_md.exists():
        files_to_read.append((node_md, "node.md"))

    for subdir in ("planning", "notes", "research"):
        for md_file in sorted(pdir.glob(f"{subdir}/*.md")):
            if md_file.name.lower() == "readme.md":
                continue
            rel_path = md_file.relative_to(pdir).as_posix()
            files_to_read.append((md_file, rel_path))

    for filepath, rel_path in files_to_read:
        content = filepath.read_text(encoding="utf-8")
        if not content.strip():
            continue
        parts.append(f"### {rel_path}\n{content}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def _build_system_prompt() -> str:
    return (
        "Du är en erfaren produktchef som analyserar ett MVP-projekt. "
        "Om devwatch-aktivitet finns tillgänglig: basera PRIMÄRT dina förslag på vad som "
        "faktiskt hänt nyligen, inte på statiskt projektinnehåll. "
        "Föreslå bara ändringar som är välmotiverade av faktisk aktivitet eller tydliga gap. "
        "Returnera ENDAST giltig JSON med tre toppnycklar: "
        "\"suggestions\" (fältförslag), "
        "\"reasoning\" (motivering per föreslaget fält — MÅSTE referera till specifik aktivitet), "
        "\"overall\" (övergripande bedömning baserad på faktisk aktivitet). "
        "Inga förklaringar utanför JSON-strukturen, inga markdown-backticks."
    )


def _build_user_prompt(context: str, devwatch_context: str = "", kind: str | None = None) -> str:
    if kind is not None:
        # Kind-aware node prompt (component nodes)
        schema = """{
  "suggestions": {
    "stage": "building" | null,
    "status": "early_mvp" | null,
    "risks": [
      {
        "category": "technical",
        "description": "string",
        "score": 8,
        "probability": 2,
        "impact": 4,
        "mitigation": "string or null"
      }
    ] | null,
    "summary": "string" | null
  },
  "reasoning": {
    "stage": "Motivering för ändringen..." | null,
    "status": "Motivering för ändringen..." | null,
    "risks": "Motivering..." | null,
    "summary": "Motivering..." | null
  },
  "overall": "Övergripande bedömning av projektet."
}"""
    else:
        # Legacy product node prompt
        schema = """{
  "suggestions": {
    "mvp_stage": "solution_test" | null,
    "status": "early_mvp" | null,
    "current_slice": "string" | null,
    "roi_percent": 243 | null,
    "value_sek": 120000 | null,
    "cost_sek": 35000 | null,
    "risks": [
      {
        "category": "technical",
        "description": "string",
        "score": 8,
        "probability": 2,
        "impact": 4,
        "mitigation": "string or null"
      }
    ] | null,
    "summary": "string" | null
  },
  "reasoning": {
    "mvp_stage": "Motivering för ändringen..." | null,
    "status": "Motivering för ändringen..." | null,
    "current_slice": "Motivering..." | null,
    "roi_percent": "Motivering..." | null,
    "value_sek": "Motivering..." | null,
    "cost_sek": "Motivering..." | null,
    "risks": "Motivering..." | null,
    "summary": "Motivering..." | null
  },
  "overall": "Övergripande bedömning av projektet."
}"""

    devwatch_section = ""
    if devwatch_context:
        devwatch_section = (
            f"\n\n## Senaste faktiska aktivitet (från devwatch)\n"
            f"Detta är vad som faktiskt ändrades i projektet nyligen:\n\n"
            f"{devwatch_context}\n\n"
            f"Basera dina förslag primärt på denna aktivitet — det är mer reliable än "
            f"att gissa från statiskt innehåll."
        )

    if kind is not None:
        # Kind-aware node: only stage/status/risks/summary
        return (
            f"Här är en komponentnod (kind={kind}):\n\n"
            f"---\n{context}\n---"
            f"{devwatch_section}\n\n"
            f"Du har tillgång till hela projektmappen ovan, inklusive planning-, notes- och research-filer. "
            f"Basera dina förslag på allt material, men prioritera devwatch-aktiviteten om den finns.\n\n"
            f"Giltiga status-värden: {sorted(VALID_STATUSES)}\n"
            f"Giltiga stage-värden: {sorted(VALID_STAGES)}\n"
            f"Giltiga risk_categories: {sorted(VALID_RISK_CATEGORIES)}\n"
            f"Risk-schema: probability (1-5) × impact (1-5) = score (1-25). "
            f"Om du kan bedöma probability och impact separat, gör det. Annars behåll gammalt score-format (1-5). "
            f"Mitigation är en valfri text om hur risken kan hanteras.\n\n"
            f"Förväntat JSON-svar:\n{schema}\n\n"
            f"Analysera projektet ovan. Du får BARA föreslå dessa fält: stage, status, risks, summary. "
            f"Föreslå INGA ekonomiska fält (cost_sek, value_sek, roi_percent) — de är deprecated. "
            f"Föreslå INTE mvp_stage eller current_slice. "
            f"För varje fält i \"suggestions\": om det redan ser korrekt "
            f"och aktuellt ut, returnera null. Om det bör uppdateras, returnera "
            f"det nya värdet. Null betyder \"inget förslag\". "
            f"För risks-fältet: returnera null om riskerna redan ser korrekta "
            f"och aktuella ut. Föreslå bara om du har nya eller väsentligt "
            f"ändrade risker att tillföra. Returnera aldrig exakt samma risker "
            f"som redan finns i projektet.\n\n"
            f"I \"reasoning\": ge en kort motivering för varje föreslaget fält (null för fälten du inte föreslår). "
            f"I \"overall\": ge en övergripande bedömning av projektets status och nästa steg."
        )

    # Legacy product node prompt
    return (
        f"Här är ett MVP-projekt:\n\n"
        f"---\n{context}\n---"
        f"{devwatch_section}\n\n"
        f"Du har tillgång till hela projektmappen ovan, inklusive planning-, notes- och research-filer. "
        f"Basera dina förslag på allt material, men prioritera devwatch-aktiviteten om den finns.\n\n"
        f"Giltiga status-värden: {sorted(VALID_STATUSES)}\n"
        f"Giltiga mvp_stage-värden: {sorted(VALID_MVP_STAGES)}\n"
        f"Giltiga risk_categories: {sorted(VALID_RISK_CATEGORIES)}\n"
        f"Risk-schema: probability (1-5) × impact (1-5) = score (1-25). "
        f"Om du kan bedöma probability och impact separat, gör det. Annars behåll gammalt score-format (1-5). "
        f"Mitigation är en valfri text om hur risken kan hanteras.\n\n"
        f"Förväntat JSON-svar:\n{schema}\n\n"
        f"Analysera projektet ovan. För varje fält i \"suggestions\": om det redan ser korrekt "
        f"och aktuellt ut, returnera null. Om det bör uppdateras, returnera "
        f"det nya värdet. Null betyder \"inget förslag\". Fälten title, slug, "
        f"created, tags, url_live, url_repo och family får INTE föreslås -- "
        f"dessa är manuella fält. "
        f"För risks-fältet: returnera null om riskerna redan ser korrekta "
        f"och aktuella ut. Föreslå bara om du har nya eller väsentligt "
        f"ändrade risker att tillföra. Returnera aldrig exakt samma risker "
        f"som redan finns i projektet.\n\n"
        f"I \"reasoning\": ge en kort motivering för varje föreslaget fält (null för fälten du inte föreslår). "
        f"I \"overall\": ge en övergripande bedömning av projektets status och nästa steg."
    )


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------


def _parse_response(raw: str, kind: str | None = None) -> tuple[dict[str, Any], dict[str, str], str]:
    """Parse Claude response into (suggestions, reasoning, overall).

    Args:
        raw: Raw JSON string from Claude.
        kind: Node kind (None for legacy product nodes).

    Returns:
        suggestions: dict of non-null field suggestions (validated)
        reasoning: dict of per-field motivation strings
        overall: overall assessment string
    """
    allowed_fields = _allowed_fields_for(kind)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse LLM response as JSON: {exc}\nRaw: {raw[:500]}")

    if not isinstance(data, dict):
        raise RuntimeError(f"LLM response is not a JSON object: {type(data)}")

    # Extract the three top-level keys
    suggestions_raw = data.get("suggestions", {})
    reasoning_raw = data.get("reasoning", {})
    overall_raw = data.get("overall", "")

    # Validate suggestions
    if not isinstance(suggestions_raw, dict):
        raise RuntimeError(f"'suggestions' must be a dict, got {type(suggestions_raw)}")

    for key in suggestions_raw:
        if key not in allowed_fields:
            raise RuntimeError(f"Unexpected field in suggestions: '{key}'")

    # Validate enum fields in suggestions
    if kind is not None:
        # Kind-aware node: validate stage enum
        if suggestions_raw.get("stage") is not None and suggestions_raw["stage"] not in VALID_STAGES:
            raise RuntimeError(
                f"Invalid stage '{suggestions_raw['stage']}'. Valid: {sorted(VALID_STAGES)}"
            )
    else:
        # Legacy node: validate mvp_stage enum
        if suggestions_raw.get("mvp_stage") is not None and suggestions_raw["mvp_stage"] not in VALID_MVP_STAGES:
            raise RuntimeError(
                f"Invalid mvp_stage '{suggestions_raw['mvp_stage']}'. Valid: {sorted(VALID_MVP_STAGES)}"
            )

    if suggestions_raw.get("status") is not None and suggestions_raw["status"] not in VALID_STATUSES:
        raise RuntimeError(
            f"Invalid status '{suggestions_raw['status']}'. Valid: {sorted(VALID_STATUSES)}"
        )

    if suggestions_raw.get("risks") is not None:
        if not isinstance(suggestions_raw["risks"], list):
            raise RuntimeError("'risks' must be a list")
        for i, risk in enumerate(suggestions_raw["risks"]):
            if not isinstance(risk, dict):
                raise RuntimeError(f"Risk at index {i} is not an object")
            if risk.get("category") not in VALID_RISK_CATEGORIES:
                raise RuntimeError(
                    f"Invalid risk category '{risk.get('category')}'. "
                    f"Valid: {sorted(VALID_RISK_CATEGORIES)}"
                )
            if not isinstance(risk.get("description"), str):
                raise RuntimeError(f"Risk at index {i} missing 'description' string")
            score = risk.get("score")
            prob = risk.get("probability")
            imp = risk.get("impact")
            # Accept both legacy (score 1-5) and new format (score 1-25)
            if not isinstance(score, (int, float)) or score < 1 or score > 25:
                raise RuntimeError(f"Risk at index {i} has invalid score: {score}")
            # If probability and impact provided, validate and compute score
            if prob is not None and imp is not None:
                if not isinstance(prob, (int, float)) or prob < 1 or prob > 5:
                    raise RuntimeError(f"Risk at index {i} has invalid probability: {prob}")
                if not isinstance(imp, (int, float)) or imp < 1 or imp > 5:
                    raise RuntimeError(f"Risk at index {i} has invalid impact: {imp}")
                # Compute score from p × i if not provided or mismatched
                suggestions_raw["risks"][i]["score"] = int(prob) * int(imp)
            # mitigation is optional
            if "mitigation" in risk and risk["mitigation"] is not None:
                if not isinstance(risk["mitigation"], str):
                    raise RuntimeError(f"Risk at index {i} mitigation must be string or null")

    # Validate reasoning
    if not isinstance(reasoning_raw, dict):
        raise RuntimeError(f"'reasoning' must be a dict, got {type(reasoning_raw)}")

    for key in reasoning_raw:
        if key not in allowed_fields:
            raise RuntimeError(f"Unexpected field in reasoning: '{key}'")
        if reasoning_raw[key] is not None and not isinstance(reasoning_raw[key], str):
            raise RuntimeError(f"Reasoning for '{key}' must be a string or null")

    # Validate overall
    if overall_raw is not None and not isinstance(overall_raw, str):
        raise RuntimeError(f"'overall' must be a string or null, got {type(overall_raw)}")

    # Filter null values from suggestions
    suggestions = {k: v for k, v in suggestions_raw.items() if v is not None}
    reasoning = {k: v for k, v in reasoning_raw.items() if v is not None and isinstance(v, str)}
    overall = overall_raw if isinstance(overall_raw, str) else ""

    return suggestions, reasoning, overall


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_analyze(
    slug: str,
    confirm_fn: Callable[[dict, dict, dict, dict, str], bool] | None = None,
    dry_run: bool = False,
    output_path: Path | None = None,
) -> bool:
    """Analyze a node via Anthropic Claude and apply suggested updates.

    Args:
        slug: Node slug.
        confirm_fn: Callable with signature (meta, new_meta, sections,
            new_sections, slug) -> bool. Returns True if user confirmed.
            If None and output_path is also None, logs a warning.
        dry_run: If True, log context length and suggestion count but do not
            save or apply anything.
        output_path: If set, save suggestions as JSON to this path instead of
            calling confirm_fn.

    Returns:
        True if changes were applied or saved, False otherwise.
    """
    meta, sections, raw = read_node(slug)

    # Skip non-product nodes (framework/system are not analyzed as products)
    kind = meta.get("kind")
    if kind in ("framework", "system"):
        console.print(f"[dim]Skipping analysis — {kind} nodes are not product-analyzed.[/dim]")
        return False

    console.print(f"[bold]Analyzing [cyan]{slug}[/cyan] with {ANTHROPIC_MODEL}...[/bold]")

    context = _read_node_context(slug)
    devwatch_context = _get_devwatch_context(slug)

    if dry_run:
        console.print(f"[dim]Context length: {len(context)} characters[/dim]")
        if devwatch_context:
            console.print(f"[dim]Devwatch context length: {len(devwatch_context)} characters[/dim]")

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(context, devwatch_context, kind=kind)

    ai_raw = _call_claude(system_prompt, user_prompt)
    suggestions, reasoning, overall = _parse_response(ai_raw, kind=kind)

    # After parsing suggestions, filter out no-op suggestions
    try:
        meta, sections, _ = read_node(slug)
        filtered_suggestions = {}
        filtered_reasoning = {}
        for field, proposed_value in suggestions.items():
            current_value = meta.get(field)
            if str(proposed_value).strip() != str(current_value or '').strip():
                filtered_suggestions[field] = proposed_value
                if reasoning and field in reasoning:
                    filtered_reasoning[field] = reasoning[field]
        suggestions = filtered_suggestions
        if reasoning:
            reasoning = filtered_reasoning
    except Exception:
        pass  # If we can't read the node, keep all suggestions

    if not suggestions:
        console.print("[dim]No suggestions -- node looks up to date.[/dim]")
        return False

    if dry_run:
        console.print(f"[dim]Dry run: {len(suggestions)} suggestion(s) found.[/dim]")
        return False

    suggestions["updated_at"] = date.today().isoformat()

    if output_path is not None:
        payload = {
            "slug": slug,
            "analyzed_at": date.today().isoformat(),
            "suggestions": suggestions,
            "reasoning": reasoning,
            "overall": overall,
        }
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[cns analyze] Saved suggestions for {slug} -> {output_path}")
        return True

    if confirm_fn is None:
        console.print("[yellow]Warning: No confirm_fn provided and no output_path set — nothing to do.[/yellow]")
        return False

    new_meta, new_sections = apply_changes(
        meta.copy(), {k: v for k, v in sections.items()}, suggestions
    )

    # apply_changes() does not handle current_slice — apply manually
    if "current_slice" in suggestions and suggestions["current_slice"] is not None:
        new_meta["current_slice"] = suggestions["current_slice"]

    new_meta["updated"] = date.today().isoformat()

    return confirm_fn(meta, new_meta, sections, new_sections, slug)


# ---------------------------------------------------------------------------
# Pending suggestions
# ---------------------------------------------------------------------------


def load_pending_suggestions() -> list[dict]:
    """Load all pending analyze suggestions from exports/.

    Returns list sorted by analyzed_at (oldest first).
    """
    exports_dir = Path("exports")
    if not exports_dir.exists():
        return []

    pending: list[dict] = []
    for json_path in sorted(exports_dir.glob("analyze_*.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        pending.append({
            "path": json_path,
            "slug": data.get("slug", ""),
            "analyzed_at": data.get("analyzed_at", ""),
            "suggestions": data.get("suggestions", {}),
            "reasoning": data.get("reasoning", {}),
            "overall": data.get("overall", ""),
        })

    pending.sort(key=lambda x: x["analyzed_at"])
    return pending


def apply_pending(
    pending: dict,
    confirm_fn: Callable[[dict, dict, dict, dict, str], bool],
) -> bool:
    """Apply a pending suggestion set after user confirmation.

    Returns True if confirmed and applied (and JSON file removed).
    """
    slug = pending["slug"]
    suggestions = pending["suggestions"]

    meta, sections, _ = read_node(slug)

    new_meta, new_sections = apply_changes(
        meta.copy(), {k: v for k, v in sections.items()}, suggestions
    )

    if "current_slice" in suggestions and suggestions["current_slice"] is not None:
        new_meta["current_slice"] = suggestions["current_slice"]

    new_meta["updated"] = date.today().isoformat()

    confirmed = confirm_fn(meta, new_meta, sections, new_sections, slug)
    if confirmed:
        pending["path"].unlink()
    return confirmed
