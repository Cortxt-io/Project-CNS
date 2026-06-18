"""Tests for the optional `entity_type` axis (Del 5.2).

`entity_type` is orthogonal to `type` (technical/routing) and `domain` (vertical):
it records what a node MODELS within its vertical (municipality, course, …).
Soft validation only — an unknown value warns, it never errors.
"""

import json
from pathlib import Path

from scripts.validator import validate_catalog, VALID_ENTITY_TYPES

ENUMS = json.loads((Path(__file__).resolve().parent.parent / "schemas" / "enums.json").read_text("utf-8"))


def _entry(**over):
    base = {"title": "X", "summary": "y", "feeds": [], "depends_on": []}
    base.update(over)
    return {"x": base}


def test_entity_types_enum_present():
    assert "municipality" in ENUMS["entity_types"]
    assert VALID_ENTITY_TYPES == set(ENUMS["entity_types"])


def test_known_entity_type_no_warning():
    errors, warnings = validate_catalog(_entry(entity_type="municipality"))
    assert not errors
    assert not any("entity_type" in w for w in warnings)


def test_unknown_entity_type_warns_not_errors():
    errors, warnings = validate_catalog(_entry(entity_type="spaceship"))
    assert not errors
    assert any("entity_type" in w for w in warnings)


def test_entity_type_absent_is_fine():
    errors, warnings = validate_catalog(_entry())
    assert not any("entity_type" in w for w in warnings)
