"""Enhetstester för rena hjälpare i scripts/sync_gh_project.py (epic #13).

Ingen nätverk/GitHub krävs — testar bara parsing/mappning. Live-synken
verifieras separat när project-scope beviljats.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sync_gh_project import (  # noqa: E402
    FIELD_INITIATIVE,
    FIELD_SYSTEM,
    FIELD_TYPE,
    field_value_for,
    parse_initiative,
)


def test_parse_initiative_found():
    assert parse_initiative("Initiative: Agentur\n\nText") == "Agentur"


def test_parse_initiative_case_and_blank():
    assert parse_initiative("initiative:   Modell-evolution  ") == "Modell-evolution"
    assert parse_initiative("Initiative:") is None
    assert parse_initiative("ingen rad här") is None
    assert parse_initiative(None) is None


def test_field_value_for_maps_label_and_milestone():
    issue = {"node_slug": "cns-mcp", "type": "chore", "quest": 13}
    vals = field_value_for(issue, {13: "Integrations"})
    assert vals[FIELD_SYSTEM] == "cns-mcp"
    assert vals[FIELD_TYPE] == "chore"
    assert vals[FIELD_INITIATIVE] == "Integrations"


def test_field_value_for_defaults_and_no_milestone():
    issue = {"node_slug": "cns-core", "type": None, "quest": None}
    vals = field_value_for(issue, {})
    assert vals[FIELD_TYPE] == "story"          # default
    assert vals[FIELD_INITIATIVE] is None        # ingen quest → ingen initiative


def _run() -> int:
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"{len(fns) - failed}/{len(fns)} passerade")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run())
