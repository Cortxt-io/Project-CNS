"""cns-analyze: AI-driven analysis of project.md files via OpenAI."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
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

OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"

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
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or key == "your_key_here":
        raise RuntimeError(
            "OpenAI API key not configured. "
            "Add OPENAI_API_KEY to .env to use cns analyze."
        )
    return key


# ---------------------------------------------------------------------------
# OpenAI caller
# ---------------------------------------------------------------------------


def _call_openai(system_prompt: str, user_prompt: str) -> str:
    api_key = _get_api_key()

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            OPENAI_ENDPOINT, json=payload, headers=headers, timeout=60
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc}")

    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI API error {resp.status_code}: {resp.text}")

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected OpenAI response structure: {exc}")

    content = content.strip()

    # Strip markdown code fences if present
    content = re.sub(r"^```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)

    if not content:
        raise RuntimeError("OpenAI returned empty content.")

    return content.strip()


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def _build_system_prompt() -> str:
    return (
        "Du är en erfaren produktchef som analyserar ett MVP-projekt. "
        "Returnera ENDAST giltig JSON enligt det schema som specificeras. "
        "Inga förklaringar, ingen löptext, inga markdown-backticks."
    )


def _build_user_prompt(raw_content: str) -> str:
    schema = """{
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
}"""

    return (
        f"Här är ett MVP-projekt:\n\n"
        f"---\n{raw_content}\n---\n\n"
        f"Giltiga status-värden: {sorted(VALID_STATUSES)}\n"
        f"Giltiga mvp_stage-värden: {sorted(VALID_MVP_STAGES)}\n"
        f"Giltiga risk_categories: {sorted(VALID_RISK_CATEGORIES)}\n\n"
        f"Förväntat JSON-svar:\n{schema}\n\n"
        f"Analysera projektet ovan. För varje fält: om det redan ser korrekt "
        f"och aktuellt ut, returnera null. Om det bör uppdateras, returnera "
        f"det nya värdet. Null betyder \"inget förslag\". Fälten title, slug, "
        f"created, tags, url_live, url_repo och family får INTE föreslås — "
        f"dessa är manuella fält."
    )


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------


def _parse_response(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse LLM response as JSON: {exc}\nRaw: {raw[:500]}")

    if not isinstance(data, dict):
        raise RuntimeError(f"LLM response is not a JSON object: {type(data)}")

    # Validate keys
    for key in data:
        if key not in ALLOWED_FIELDS:
            raise RuntimeError(f"Unexpected field in LLM response: '{key}'")

    # Validate enum fields
    if data.get("mvp_stage") is not None and data["mvp_stage"] not in VALID_MVP_STAGES:
        raise RuntimeError(
            f"Invalid mvp_stage '{data['mvp_stage']}'. Valid: {sorted(VALID_MVP_STAGES)}"
        )

    if data.get("status") is not None and data["status"] not in VALID_STATUSES:
        raise RuntimeError(
            f"Invalid status '{data['status']}'. Valid: {sorted(VALID_STATUSES)}"
        )

    if data.get("risks") is not None:
        if not isinstance(data["risks"], list):
            raise RuntimeError("'risks' must be a list")
        for i, risk in enumerate(data["risks"]):
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

    # Filter null values
    return {k: v for k, v in data.items() if v is not None}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_analyze(
    slug: str,
    confirm_fn: Callable[[dict, dict, dict, dict, str], bool],
) -> bool:
    """Analyze a project via OpenAI and apply suggested updates.

    Args:
        slug: Project slug.
        confirm_fn: Callable with signature (meta, new_meta, sections,
            new_sections, slug) -> bool. Returns True if user confirmed.

    Returns:
        True if changes were applied, False otherwise.
    """
    meta, sections, raw = read_project(slug)

    console.print(f"[bold]Analyzing [cyan]{slug}[/cyan] with {OPENAI_MODEL}...[/bold]")

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(raw)

    ai_raw = _call_openai(system_prompt, user_prompt)
    suggestions = _parse_response(ai_raw)

    if not suggestions:
        console.print("[dim]No suggestions — project looks up to date.[/dim]")
        return False

    suggestions["updated_at"] = date.today().isoformat()

    new_meta, new_sections = apply_changes(
        meta.copy(), {k: v for k, v in sections.items()}, suggestions
    )

    # apply_changes() does not handle current_slice — apply manually
    if "current_slice" in suggestions and suggestions["current_slice"] is not None:
        new_meta["current_slice"] = suggestions["current_slice"]

    new_meta["updated"] = date.today().isoformat()

    return confirm_fn(meta, new_meta, sections, new_sections, slug)
