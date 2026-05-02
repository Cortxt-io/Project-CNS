"""Validation for Perplexity API responses and project files."""

from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import ValidationError, validate

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "project_schema.json"

# Required frontmatter fields for a valid project
REQUIRED_FM_FIELDS = [
    "title", "slug", "status", "mvp_stage",
    "cost_sek", "value_sek", "roi_percent",
]

# Allowed enum values
VALID_STATUSES = {"idea", "early_mvp", "mvp", "live", "shelved"}
VALID_MVP_STAGES = {"hypothesis", "problem_interviews", "solution_test", "demand_test", "launch"}
VALID_RISK_CATEGORIES = {"technical", "market", "legal", "ops", "competition"}

# Required sections (must exist as ## headings)
from scripts.md_parser import SECTIONS as REQUIRED_SECTIONS


def load_schema() -> dict:
    """Load the JSON schema from disk."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_response(data: dict) -> tuple[bool, str | None]:
    """Validate a parsed JSON response against the project schema.

    Returns (True, None) on success or (False, error_message) on failure.
    """
    schema = load_schema()
    try:
        validate(instance=data, schema=schema)
        return True, None
    except ValidationError as exc:
        return False, str(exc.message)


# ---------------------------------------------------------------------------
# Project-level validation (used by `cns validate`)
# ---------------------------------------------------------------------------

def validate_project(meta: dict, sections: dict) -> list[str]:
    """Validate a project's frontmatter and sections.

    Returns a list of error strings.  Empty list = valid.
    """
    errors: list[str] = []

    # 1. Required frontmatter fields
    for field in REQUIRED_FM_FIELDS:
        if field not in meta:
            errors.append(f"Missing frontmatter field: {field}")

    # 2. Enum checks
    status = meta.get("status")
    if status is not None and status not in VALID_STATUSES:
        errors.append(
            f"Invalid status '{status}'. Allowed: {', '.join(sorted(VALID_STATUSES))}"
        )

    mvp_stage = meta.get("mvp_stage")
    if mvp_stage is not None and mvp_stage not in VALID_MVP_STAGES:
        errors.append(
            f"Invalid mvp_stage '{mvp_stage}'. Allowed: {', '.join(sorted(VALID_MVP_STAGES))}"
        )

    # 3. Required sections
    for heading in REQUIRED_SECTIONS:
        if heading not in sections:
            errors.append(f"Missing section: ## {heading}")

    # 4. ROI consistency
    cost = meta.get("cost_sek", 0)
    value = meta.get("value_sek", 0)
    roi = meta.get("roi_percent", 0)
    if isinstance(cost, (int, float)) and isinstance(value, (int, float)) and isinstance(roi, (int, float)):
        if cost > 0:
            expected_roi = round((value - cost) / cost * 100)
            if roi != expected_roi:
                errors.append(
                    f"ROI mismatch: roi_percent={roi} but calculated "
                    f"(value_sek - cost_sek) / cost_sek * 100 = {expected_roi}"
                )
        elif cost == 0 and roi != 0:
            errors.append(
                f"ROI mismatch: cost_sek=0 so roi_percent should be 0, got {roi}"
            )

    # 5. Risk category validation
    risk_text = sections.get("Risk Assessment", "")
    for line in risk_text.splitlines():
        line = line.strip()
        if not line.startswith("- **"):
            continue
        # Extract category from "- **Category** (score ...)"
        m = re.match(r"- \*\*(\w+)\*\*", line)
        if m:
            cat = m.group(1).lower()
            if cat not in VALID_RISK_CATEGORIES:
                errors.append(
                    f"Invalid risk category '{cat}'. "
                    f"Allowed: {', '.join(sorted(VALID_RISK_CATEGORIES))}"
                )

    return errors
