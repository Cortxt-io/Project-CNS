"""Systemkartan — katalogen renderad som en vault-not.

Kartan är BERÄKNINGSBAR: den är `catalog.yaml` sett från sidan, grupperad på det härledda
lagret (`derive_layer`, portfolio-layers-regeln). Därför genereras den, och därför får den
aldrig handredigeras — en handunderhållen kopia av något maskinen räknar ut är per definition
en fil som kommer bli inaktuell. Det är samma skäl som `kind` och `layer` aldrig lagras.

Vaulten bär omdöme (grindar, kill-villkor, prosa). Katalogen bär struktur. Den här filen är
bron: den låter vaulten *visa* strukturen utan att *äga* den.

Kör: python lab/cns_lab.py systemmap [--out <sökväg>]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from scripts.catalog import derive_kind, derive_layer, load_catalog

LAYERS = [
    ("substrate", "Substrat", "Kärnan allt annat vilar på."),
    ("fog", "Fog", "Det delade lagret mellan bar kärna och produkt — orkestrering, MCP, ytor."),
    ("vertical", "Vertikal", "Produkterna. Egna domäner, egna repon, egen drift."),
]

BANNER = """---
type: index
status: active
tags: [systemkarta, generated]
---

# Systemkartan

> [!warning] Genererad — redigera inte
> Den här noten är en **projektion av `catalog.yaml`**, inte prosa. Den är varken register
> eller beskrivning: den är beräkningsbar, och därför räknas den ut. Skriv om du vill ändra
> något: ändra katalogen och kör om `cns systemmap`. Redigerar du här skriver nästa körning
> över dig — och tills dess ljuger filen.

Portföljen i T-form: en bred bas (substrat + fog) som smala produktstammar vilar på. Lagret
**härleds** ur `part_of` och `domain` (regeln: [[portfolio-layers]]), det lagras inte.
"""


def render(systems: dict[str, dict]) -> str:
    out = [BANNER]
    for key, title, blurb in LAYERS:
        members = sorted(s for s in systems if derive_layer(s, systems) == key)
        if not members:
            continue
        out.append(f"\n## {title} · {len(members)} st\n\n_{blurb}_\n")
        out.append("| Nod | Sort | Typ | Live | Repo |")
        out.append("|-----|------|-----|------|------|")
        for slug in members:
            e = systems[slug]
            live = e.get("url_live") or ""
            repo = e.get("url_repo") or ""
            out.append(
                f"| **{slug}** — {e.get('title', '')} "
                f"| {derive_kind(slug, systems)} | {e.get('type', '—')} "
                f"| {live or '—'} | {repo or '—'} |"
            )
    out.append(f"\n---\n\n_{len(systems)} noder. Genererad av `cns systemmap` ur `catalog.yaml`._\n")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", type=Path, help="skriv noten hit (default: skriv till stdout)")
    args = p.parse_args(argv)

    text = render(load_catalog())
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"skrev {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
