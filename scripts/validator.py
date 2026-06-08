"""Validation for Perplexity API responses and node files."""

from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import ValidationError, validate

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "node_schema.json"

# REMOVED during node-model migration (all nodes now have kind set):
# REQUIRED_FM_FIELDS for legacy product nodes is no longer needed.

# Allowed enum values
VALID_STATUSES = {"idea", "early_mvp", "mvp", "live", "shelved"}
VALID_MVP_STAGES = {"hypothesis", "problem_interviews", "solution_test", "demand_test", "launch"}
VALID_RISK_CATEGORIES = {"technical", "market", "legal", "ops", "competition", "positioning", "adoption"}

# Node model enums (Quest A — optional fields)
VALID_KINDS = {"component", "system", "framework"}
VALID_STAGES = {"idea", "building", "working", "maturing"}

# Legacy enum constants kept for reference but no longer validated:
# VALID_LAYERS, VALID_PIPELINES, VALID_FAMILIES

VALID_LAYERS = {
    "pipeline",
    "infrastructure",
    "interface",
    "concept",
}

VALID_PIPELINES = {
    "pipeline-intern",
    "pipeline-extern",
    "pipeline-review",
}

VALID_FAMILIES = {
    "developer-tools", "digest-pipeline", "internal-monitoring",
    "cns-core", "ideas", "cns-platform", "monitoring-pipeline",
}

# Required sections (must exist as ## headings) — imported lazily to avoid
# circular dependency with kind-aware section sets
from scripts.md_parser import SECTIONS as REQUIRED_SECTIONS
from scripts.md_parser import sections_for_kind as _sections_for_kind


def load_schema() -> dict:
    """Load the JSON schema from disk."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_response(data: dict) -> tuple[bool, str | None]:
    """Validate a parsed JSON response against the node schema.

    Returns (True, None) on success or (False, error_message) on failure.
    """
    schema = load_schema()
    try:
        validate(instance=data, schema=schema)
        return True, None
    except ValidationError as exc:
        return False, str(exc.message)


# ---------------------------------------------------------------------------
# Node-level validation (used by `cns validate`)
# ---------------------------------------------------------------------------

def validate_node(meta: dict, sections: dict) -> list[str]:
    """Validate a node's frontmatter and sections.

    Returns a list of error strings.  Empty list = valid.
    """
    errors: list[str] = []
    kind = meta.get("kind")  # None for legacy product nodes

    # 1. Required frontmatter fields
    #    All nodes now have kind set — require title and slug.
    #    (Legacy REQUIRED_FM_FIELDS check removed during node-model migration.)
    for field in ("title", "slug"):
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

    # (Legacy family/layer/pipeline enum checks removed during node-model migration.)

    # 2e. Kind enum check (optional field)
    if kind is not None and kind not in VALID_KINDS:
        errors.append(
            f"Invalid kind '{kind}'. Allowed: {', '.join(sorted(VALID_KINDS))}"
        )

    # 2f. Stage enum check (optional field)
    stage = meta.get("stage")
    if stage is not None and stage not in VALID_STAGES:
        errors.append(
            f"Invalid stage '{stage}'. Allowed: {', '.join(sorted(VALID_STAGES))}"
        )

    # 3. Required sections — kind-aware
    required_headings = _sections_for_kind(kind)
    for heading in required_headings:
        if heading not in sections:
            errors.append(f"Missing section: ## {heading}")

    # (ROI consistency check removed — no legacy product nodes remain.)

    # 5. Risk category validation + new risk schema
    risk_text = sections.get("Risk Assessment", sections.get("Risker", sections.get("Systemrisker", "")))
    for line in risk_text.splitlines():
        line = line.strip()
        if not line.startswith("- **"):
            continue
        # Extract category from "- **Category** (score ...)" or "- **Category** (P2 × I4 = 8/25)"
        m = re.match(r"- \*\*(\w+)\*\*", line)
        if m:
            cat = m.group(1).lower()
            if cat not in VALID_RISK_CATEGORIES:
                errors.append(
                    f"Invalid risk category '{cat}'. "
                    f"Allowed: {', '.join(sorted(VALID_RISK_CATEGORIES))}"
                )

    # 5b. Validate risk objects in frontmatter (if present as structured data)
    risks = meta.get("risks")
    if isinstance(risks, list):
        for i, risk in enumerate(risks):
            if not isinstance(risk, dict):
                continue
            score = risk.get("score")
            prob = risk.get("probability")
            imp = risk.get("impact")
            # If probability and impact exist, score should equal p × i
            if prob is not None and imp is not None:
                if isinstance(prob, (int, float)) and isinstance(imp, (int, float)):
                    if prob < 1 or prob > 5:
                        errors.append(f"Risk at index {i}: probability must be 1-5, got {prob}")
                    if imp < 1 or imp > 5:
                        errors.append(f"Risk at index {i}: impact must be 1-5, got {imp}")
                    expected_score = prob * imp
                    if score is not None and isinstance(score, (int, float)):
                        if score != expected_score:
                            errors.append(
                                f"Risk at index {i}: score={score} but probability({prob}) × impact({imp}) = {expected_score}"
                            )
            # Score range: 1-25 (new) or 1-5 (legacy)
            if score is not None and isinstance(score, (int, float)):
                if score < 1 or score > 25:
                    errors.append(f"Risk at index {i}: score must be 1-25, got {score}")

    # 6. Node-model reference validation (warnings, not errors)
    if kind is not None:
        # part_of: if set, slug directory should exist
        part_of = meta.get("part_of")
        if part_of is not None and part_of != "":
            from scripts.md_parser import node_dir as _node_dir
            if not _node_dir(part_of).exists():
                errors.append(
                    f"Warning: part_of='{part_of}' but no node directory found for that slug"
                )

        # feeds and depends_on must be lists of strings if present
        for rel_field in ("feeds", "depends_on"):
            val = meta.get(rel_field)
            if val is not None:
                if not isinstance(val, list):
                    errors.append(f"{rel_field} must be a list, got {type(val).__name__}")
                elif not all(isinstance(item, str) for item in val):
                    errors.append(f"{rel_field} must be a list of strings")

        # Kind-structure hints (informational warnings)
        if kind == "framework" and part_of not in (None, ""):
            errors.append(f"Warning: framework nodes should not have part_of (got '{part_of}')")
        if kind == "component" and part_of in (None, ""):
            errors.append("Warning: component nodes should typically have part_of set")

    return errors
