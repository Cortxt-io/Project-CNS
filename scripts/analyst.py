"""cns-analyze: AI-driven analysis of project.md files via Anthropic Claude."""

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

from scripts.md_parser import apply_changes, read_project
from scripts.validator import (
    VALID_MVP_STAGES,
    VALID_RISK_CATEGORIES,
    VALID_STATUSES,
)

ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-5"

ALLOWED_FIELDS = {
    "mvp_stage", "status", "current_slice", "roi_percent",
    "value_sek", "cost_sek", "risks", "summary",
}

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


def _call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
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
# Project context reader
# ---------------------------------------------------------------------------


def _read_project_context(slug: str) -> str:
    """Read and concatenate all project Markdown files as context."""
    from scripts.md_parser import project_dir

    pdir = project_dir(slug)
    parts: list[str] = []

    files_to_read: list[tuple[Path, str]] = []
    # project.md always first
    project_md = pdir / "project.md"
    if project_md.exists():
        files_to_read.append((project_md, "project.md"))

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
        "Returnera ENDAST giltig JSON med tre toppnålar: "
        "\"suggestions\" (fältförslag som tidigare), "
        "\"reasoning\" (motivering per föreslaget fält), "
        "\"overall\" (övergripande bedömning). "
        "Inga förklaringar utanför JSON-strukturen, inga markdown-backticks."
    )


def _build_user_prompt(context: str) -> str:
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
        "score": 3
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

    return (
        f"Här är ett MVP-projekt:\n\n"
        f"---\n{context}\n---\n\n"
        f"Du har tillgång till hela projektmappen ovan, inklusive planning-, notes- och research-filer. "
        f"Basera dina förslag på allt material, inte bara project.md.\n\n"
        f"Giltiga status-värden: {sorted(VALID_STATUSES)}\n"
        f"Giltiga mvp_stage-värden: {sorted(VALID_MVP_STAGES)}\n"
        f"Giltiga risk_categories: {sorted(VALID_RISK_CATEGORIES)}\n\n"
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


def _parse_response(raw: str) -> tuple[dict[str, Any], dict[str, str], str]:
    """Parse Claude response into (suggestions, reasoning, overall).

    Returns:
        suggestions: dict of non-null field suggestions (validated)
        reasoning: dict of per-field motivation strings
        overall: overall assessment string
    """
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
        if key not in ALLOWED_FIELDS:
            raise RuntimeError(f"Unexpected field in suggestions: '{key}'")

    # Validate enum fields in suggestions
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
            if not isinstance(score, (int, float)) or score < 1 or score > 5:
                raise RuntimeError(f"Risk at index {i} has invalid score: {score}")

    # Validate reasoning
    if not isinstance(reasoning_raw, dict):
        raise RuntimeError(f"'reasoning' must be a dict, got {type(reasoning_raw)}")

    for key in reasoning_raw:
        if key not in ALLOWED_FIELDS:
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
    """Analyze a project via Anthropic Claude and apply suggested updates.

    Args:
        slug: Project slug.
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
    meta, sections, raw = read_project(slug)

    console.print(f"[bold]Analyzing [cyan]{slug}[/cyan] with {ANTHROPIC_MODEL}...[/bold]")

    context = _read_project_context(slug)

    if dry_run:
        console.print(f"[dim]Context length: {len(context)} characters[/dim]")

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(context)

    ai_raw = _call_claude(system_prompt, user_prompt)
    suggestions, reasoning, overall = _parse_response(ai_raw)

    # After parsing suggestions, filter out no-op suggestions
    try:
        meta, sections, _ = read_project(slug)
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
        pass  # If we can't read the project, keep all suggestions

    if not suggestions:
        console.print("[dim]No suggestions -- project looks up to date.[/dim]")
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

    meta, sections, _ = read_project(slug)

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
