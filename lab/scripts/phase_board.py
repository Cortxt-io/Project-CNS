"""Fas-checklistan — den härledda fasen renderad IN i venture-noten.

Fasen HÄRLEDS (``phase_derive``) ur verkligheten: repo, tester, deploy. Men härledd får inte
betyda osynlig — man ska kunna se på rak arm var något står, och en sanning ingen ser styr
ingenting.

Därför **lagrar** vi den inte (ett fält någon måste flytta för hand blir en andra sanning som
driver isär från verkligheten — det var precis vad ``stage`` gjorde). Vi **projicerar** den:
generatorn skriver ett block mellan markörer, och räknar om det utan att röra prosan runt
omkring. Samma art som systemkartan — varken register eller beskrivning, utan en projektion.

Kör: python lab/cns_lab.py phase-board [--write]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from scripts.catalog import load_catalog

BEGIN = "<!-- cns:phase:start — GENERERAD. Redigera inte innanför markörerna. -->"
END = "<!-- cns:phase:end -->"

TICK = {True: "x", False: " ", None: "?"}


def render_block(recipe: dict, derived: dict, annotation: dict) -> str:
    """Fasen, stegen och grinden — som en människa kan läsa på tre sekunder."""
    phase = derived.get("phase")
    steps = derived.get("steps") or {}
    gate = derived.get("gate") or {}
    skipped = derived.get("gates_skipped") or []

    out = [BEGIN, "", f"## Fas: **{derived.get('title') or phase or '—'}**", ""]
    out.append("_Härledd ur verkligheten (repo · tester · deploy), inte kryssad. "
               "Fasen är bevis, inte påstående._")
    out.append("")

    # Bara den aktuella fasens steg — resten är brus.
    for p in recipe.get("phases", []):
        if p.get("key") != phase:
            continue
        for s in p.get("steps", []):
            key, title = s.get("key"), s.get("title", s.get("key"))
            state = steps.get(key)
            manual = s.get("check") == "manual"
            mark = TICK.get(state, " ")
            hint = "" if state else ("  ← dina ögon" if manual else "  ← mäts, saknas")
            out.append(f"- [{mark}] {title}{hint}")
        out.append("")

    if gate:
        out.append(f"**Grind: {gate.get('title', '—')}**")
        out.append(f"> {gate.get('question', '')}")
        blocked = gate.get("blocked_by") or []
        if blocked:
            out.append(f"> Blockerad av: {', '.join(blocked)}")
        out.append("")

    decision = annotation.get("gate_decision")
    if decision:
        date = annotation.get("gate_date") or "odaterad"
        out.append(f"**Ditt beslut:** `{decision}` ({date})")
    else:
        out.append("**Ditt beslut:** — · `gate_decision` är tom. Den här rullar på tröghet, "
                   "inte på beslut. Skriv `go` · `kill` · `hold` · `recycle`.")
    out.append("")

    if skipped:
        out.append(f"> [!warning] Hoppade grindar: {', '.join(skipped)}")
        out.append("> Bygget passerade dem utan att någon frågade om det borde finnas. "
                   "Det är inte ett fel i mätningen — det är vad som hände.")
        out.append("")

    out.append(END)
    return "\n".join(out)


def inject(note: str, block: str) -> str:
    """Byt ut blocket, eller lägg till det. Prosan runt omkring är människans — rör den aldrig."""
    if BEGIN in note and END in note:
        head = note.split(BEGIN)[0]
        tail = note.split(END, 1)[1]
        return f"{head}{block}{tail}"
    return note.rstrip("\n") + "\n\n" + block + "\n"


def main(argv: list[str] | None = None) -> int:
    from scripts import phase_derive, signals, vault_reader

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--write", action="store_true", help="skriv in i noterna (default: dry-run)")
    args = p.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent.parent
    recipe = yaml.safe_load((repo_root / "roadmaps" / "_recipe.yaml").read_text(encoding="utf-8"))
    catalog = load_catalog()
    root = vault_reader.vault_root()
    if root is None:
        print("ingen vault")
        return 1

    for path in vault_reader._note_paths(root):
        text = path.read_text(encoding="utf-8")
        meta, _ = vault_reader.parse_note(text)
        if not meta or not vault_reader.is_portfolio_note(meta, path):
            continue
        slug = path.stem
        node = str(meta.get("node") or "").strip()
        sig = signals.collect(slug, catalog_entry=catalog.get(node), annotation=meta)
        derived = phase_derive.derive_phase(
            recipe, signals=sig, checked=signals.checked_steps(meta))
        block = render_block(recipe, derived, meta)
        if args.write:
            path.write_text(inject(text, block), encoding="utf-8")
        print(f"{slug:24} {derived.get('phase', '?'):12} "
              f"grind={meta.get('gate_decision') or '—'}")
    if not args.write:
        print("\n(dry-run — kör med --write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
