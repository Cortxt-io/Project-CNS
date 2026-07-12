"""Systemkartan: katalogen renderad som en vault-not.

Kartan är BERÄKNINGSBAR — den är catalog.yaml sett från sidan. Därför genereras den, och
därför får den aldrig handredigeras: en handunderhållen kopia av något maskinen kan räkna ut
är en fil som kommer bli inaktuell. (Samma skäl som `derive_kind`/`derive_layer` inte lagras.)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab.scripts.systemmap import render  # noqa: E402

CATALOG = {
    "cns-core":  {"title": "CNS Core", "summary": "Kärnan", "type": "cli", "domain": "cortxt"},
    "agentur":   {"title": "Agentur", "summary": "Orkestrering", "type": "service",
                  "domain": "cortxt", "part_of": "infrastructure"},
    "juvahem":   {"title": "Juvahem", "summary": "Par-relocation", "type": "tool",
                  "domain": "juvahem", "url_live": "https://juvahem.se",
                  "url_repo": "https://github.com/Cortxt-io/juvahem"},
}


def test_every_node_appears():
    out = render(CATALOG)
    for slug in CATALOG:
        assert slug in out


def test_nodes_are_grouped_by_derived_layer():
    """Lagret HÄRLEDS (portfolio-layers-regeln) — kartan lagrar det inte, den visar det."""
    out = render(CATALOG)
    assert "Substrat" in out and "Vertikal" in out
    substrate, vertical = out.index("Substrat"), out.index("Vertikal")
    assert out.index("cns-core") > substrate
    assert out.index("juvahem") > vertical


def test_live_url_is_shown_as_a_link():
    assert "https://juvahem.se" in render(CATALOG)


def test_the_note_says_it_is_generated():
    """En genererad fil som inte säger att den är genererad blir handredigerad, och då ljuger den."""
    out = render(CATALOG)
    assert "genererad" in out.lower()
    assert "cns systemmap" in out.lower()


def test_frontmatter_declares_it_is_not_prose():
    """Kartan är varken register eller beskrivning — den är en projektion av katalogen."""
    assert out_startswith(render(CATALOG))


def out_startswith(out: str) -> bool:
    return out.startswith("---\n") and "type: index" in out.split("---")[1]
