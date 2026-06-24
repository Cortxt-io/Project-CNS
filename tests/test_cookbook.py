"""Verifiering av cookbook-generatorn (scripts/cookbook.py) — hermetiskt, ingen LLM/nät.

dry_run bygger kontext + prompt utan modell-anrop; load_cookbook läser committad JSON.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import cookbook  # noqa: E402


def test_dry_run_builds_context_no_llm() -> None:
    r = cookbook.run_cookbook("juvahem", dry_run=True)
    assert r["dry_run"] is True
    assert "juvahem" in r["context"]
    # roadmap-fasen ska finnas med i kontexten (kopplar nuläget)
    assert "fas" in r["context"].lower() or "roadmap" in r["context"].lower()
    assert "JSON" in r["prompt"] or "cookbook" in r["prompt"].lower()


def test_load_cookbook_seed() -> None:
    cb = cookbook.load_cookbook("juvahem")
    assert cb is not None
    assert cb["domain"] == "juvahem" and len(cb["steps"]) >= 5
    assert {s["discipline"] for s in cb["steps"]} <= {"ui_ux", "backend"}
    assert all(s.get("key") for s in cb["steps"])


def test_missing_cookbook_is_none() -> None:
    assert cookbook.load_cookbook("does-not-exist") is None


if __name__ == "__main__":
    test_dry_run_builds_context_no_llm(); test_load_cookbook_seed(); test_missing_cookbook_is_none()
    print("OK — cookbook reader/generator (dry) green")


def test_dry_run_evolves_from_previous() -> None:
    """När en cookbook redan finns matas den in i prompten (evolve, ej regenerera)."""
    r = cookbook.run_cookbook("juvahem", dry_run=True)
    assert r["evolves_from_previous"] is True
    assert "Föregående cookbook" in r["prompt"]
