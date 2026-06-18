"""Bemanna en roster-roll → körbar agent (mekanisk motor).

Flyttar .claude/org/roster/<slug>.md → .claude/agents/<slug>.md, sätter
status: active, flippar active-flaggan i manifest.json och regenererar registret.
Omdömet (fylla kroppen, validera behovet) görs FÖRE detta via /bemanna-skillen.

Kör: python scripts/bemanna.py <slug>
"""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROSTER_DIR = ROOT / ".claude" / "org" / "roster"
AGENTS_DIR = ROOT / ".claude" / "agents"
MANIFEST = ROOT / ".claude" / "org" / "manifest.json"

SKELETON_MARKERS = ("(TODO", "Skal —", "Skal-roll")


def bemanna(slug: str, force: bool = False) -> int:
    src = ROSTER_DIR / f"{slug}.md"
    dst = AGENTS_DIR / f"{slug}.md"
    if not src.exists():
        print(f"FEL: hittar ingen roster-roll '{slug}' i {ROSTER_DIR}")
        return 1
    if dst.exists():
        print(f"FEL: '{slug}' finns redan som aktiv agent i {AGENTS_DIR}")
        return 1

    # Kvalitetsgrind: en halvfärdig agent får inte aktiveras (om inte --force)
    gate = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_agent.py"), slug]
    )
    if gate.returncode != 0 and not force:
        print(f"\nBLOCKERAD: {slug} klarar inte kvalitetsgrinden (validate_agent). "
              f"Fyll kroppen enligt /bemanna-skillen, eller kör med --force.")
        return 1

    text = src.read_text(encoding="utf-8")

    # 1. status: roster -> active i frontmatter
    text = re.sub(r"^status:.*$", "status: active", text, count=1, flags=re.MULTILINE)

    # 2. flytta fil (skriv ny, ta bort gammal)
    dst.write_text(text, encoding="utf-8")
    src.unlink()

    # 3. flippa manifest-flaggan: rad med "<slug>" -> sista false] blir true]
    mtext = MANIFEST.read_text(encoding="utf-8")
    pattern = re.compile(rf'(\["{re.escape(slug)}",[^\]]*,\s*)false(\s*\])')
    new_mtext, n = pattern.subn(r"\1true\2", mtext)
    if n == 0:
        print(f"VARNING: hittade ingen active=false-rad för '{slug}' i manifest "
              f"(redan aktiv i manifest?) — filflytt gjord ändå.")
    else:
        MANIFEST.write_text(new_mtext, encoding="utf-8")

    # 4. regenerera registret
    subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_agentur.py")], check=True)

    print(f"BEMANNAD: {slug} -> .claude/agents/{slug}.md (status active).")
    print("Nästa steg: lägg ev. routing-regel i scripts/router.py, commit+push.")
    print("OBS: agenten blir anropbar som subagent_type först efter omladdning.")
    return 0


def main(argv: list[str]) -> int:
    force = "--force" in argv
    args = [a for a in argv if a != "--force"]
    if len(args) != 1:
        print("Användning: python scripts/bemanna.py <slug> [--force]")
        return 2
    return bemanna(args[0], force=force)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
