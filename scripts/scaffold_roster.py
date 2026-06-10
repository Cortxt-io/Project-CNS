"""Scaffolda org-registret ur .claude/org/manifest.json.

För varje roll som INTE är aktiv (active=false) skapas en skal-fil i
.claude/org/roster/<slug>.md om den saknas. Aktiva roller bor i .claude/agents/
och rörs inte. Idempotent: befintliga roster-filer skrivs inte över.

Kör: python scripts/scaffold_roster.py
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / ".claude" / "org" / "manifest.json"
ROSTER_DIR = ROOT / ".claude" / "org" / "roster"
AGENTS_DIR = ROOT / ".claude" / "agents"

MODEL_MAP = {
    "opus": "claude-opus-4-8",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
}

SKELETON = """---
name: {slug}
title: {title}
department: {department}
sub_department: {sub_department}
chapter: {chapter}
squad: null
lead: {lead}
model: {model}
status: roster
description: {title} i avdelningen {department}/{sub_department}. (Skal — fyll vid bemanning.)
---

# {title}

> **Skal-roll i org-registret.** Inte körbar förrän bemannad (status: active) och flyttad
> till `.claude/agents/`. Se `.claude/agents/AGENTUR.md` och `/bemanna`-flödet.

## Roll (TODO vid bemanning)
- Kärnuppgift: <vad rollen levererar — 1 mening>
- Hör till: {department} → {sub_department}{chapter_line}

## Tillåtna verktyg (TODO)
- <MCP-verktyg rollen behöver>

## Eval-kriterier (TODO)
- <hur vet vi att rollen gör sitt jobb>
"""


def iter_roles():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for dept, subs in data["departments"].items():
        for sub, roles in subs.items():
            for slug, title, model, lead, active in roles:
                yield dept, sub, slug, title, model, lead, active


def main() -> None:
    ROSTER_DIR.mkdir(parents=True, exist_ok=True)
    created, skipped_active, skipped_exists = 0, 0, 0
    removed_stale = 0
    for dept, sub, slug, title, model, lead, active in iter_roles():
        if active:
            skipped_active += 1
            # Städa: en aktiverad roll får inte ligga kvar som roster-skal (dubbelräkning)
            stale = ROSTER_DIR / f"{slug}.md"
            if stale.exists():
                stale.unlink()
                removed_stale += 1
            continue
        path = ROSTER_DIR / f"{slug}.md"
        if path.exists():
            skipped_exists += 1
            continue
        chapter = sub if dept == "Engineering" else "null"
        chapter_line = f" (chapter: {sub})" if dept == "Engineering" else ""
        path.write_text(SKELETON.format(
            slug=slug, title=title, department=dept, sub_department=sub,
            chapter=chapter, lead=str(lead).lower(),
            model=MODEL_MAP.get(model, "claude-haiku-4-5"),
            chapter_line=chapter_line,
        ), encoding="utf-8")
        created += 1
    total = created + skipped_active + skipped_exists
    print(f"Roster: {created} skapade, {skipped_exists} fanns redan, "
          f"{skipped_active} aktiva (i .claude/agents/), {removed_stale} stale roster-filer städade. "
          f"Totalt {total} roller i manifest.")


if __name__ == "__main__":
    main()
