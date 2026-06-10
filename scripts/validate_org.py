"""Mekanisk konsekvens-kontroll av org-registret.

Läser .claude/org/manifest.json + roster + aktiva agentfiler och rapporterar
ERROR/WARN. Exit 1 vid ERROR (kan grinda CI/agent). Org-arkitekten kör detta
och tillämpar omdöme på det mekaniken inte kan avgöra.

Kör: python scripts/validate_org.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / ".claude" / "org" / "manifest.json"
ROSTER_DIR = ROOT / ".claude" / "org" / "roster"
AGENTS_DIR = ROOT / ".claude" / "agents"

DEPARTMENTS = {"Ledning", "Produkt", "R&D", "Engineering", "Platform",
               "People", "Program", "Drift", "Ekonomi", "Kommunikation"}
MODELS = {"opus", "sonnet", "haiku"}
# Sub_departments som EGENTLIGEN är produktområden (ska vara squad, inte chapter/disciplin)
PRODUCT_AREAS = {"tui", "dashboard", "mcp", "core", "landing", "web", "app", "cns-core"}


def parse_fm(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def main() -> int:
    errors, warns = [], []
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    seen_slugs: dict[str, str] = {}
    manifest_count = 0
    active_count = 0
    for dept, subs in data["departments"].items():
        if dept not in DEPARTMENTS:
            errors.append(f"Okänd avdelning '{dept}' i manifest")
        for sub, roles in subs.items():
            leads = 0
            if sub.lower() in PRODUCT_AREAS:
                warns.append(f"{dept}/{sub}: '{sub}' ser ut som ett PRODUKTOMRÅDE — "
                             f"bör vara en squad, inte en sub_department/chapter")
            for role in roles:
                manifest_count += 1
                slug, title, model, lead, active = role
                if slug in seen_slugs:
                    errors.append(f"Duplicerad slug '{slug}' ({seen_slugs[slug]} + {dept}/{sub})")
                seen_slugs[slug] = f"{dept}/{sub}"
                if model not in MODELS:
                    errors.append(f"{slug}: okänd modell '{model}' (ej {MODELS})")
                if lead:
                    leads += 1
                if active:
                    active_count += 1
                    if not (AGENTS_DIR / f"{slug}.md").exists():
                        errors.append(f"{slug}: active men saknar fil i .claude/agents/")
                else:
                    if not (ROSTER_DIR / f"{slug}.md").exists():
                        errors.append(f"{slug}: roster men saknar fil i .claude/org/roster/")
            if leads == 0:
                warns.append(f"{dept}/{sub}: ingen lead utsedd")

    # Squads: varje medlem måste finnas som roll
    for squad, members in data.get("squads", {}).items():
        for m in members:
            if m not in seen_slugs:
                errors.append(f"Squad '{squad}': medlem '{m}' finns inte som roll i manifest")

    # Föräldralösa aktiva agentfiler (i .claude/agents men ej i manifest)
    for path in AGENTS_DIR.glob("*.md"):
        if path.name == "AGENTUR.md":
            continue
        fm = parse_fm(path.read_text(encoding="utf-8"))
        name = fm.get("name")
        if name and name not in seen_slugs:
            warns.append(f"{name}: aktiv agentfil utan post i manifest.json (föräldralös)")

    # Sync-koll mot faktiska roster-filer
    roster_files = len(list(ROSTER_DIR.glob("*.md"))) if ROSTER_DIR.exists() else 0
    if roster_files + active_count != manifest_count:
        warns.append(f"Sync: manifest {manifest_count} != roster-filer {roster_files} "
                     f"+ aktiva {active_count} — kör scaffold_roster.py + gen_agentur.py")

    print(f"=== ORG-VALIDERING: {manifest_count} roller, {active_count} aktiva ===")
    for e in errors:
        print(f"ERROR: {e}")
    for w in warns:
        print(f"WARN:  {w}")
    if not errors and not warns:
        print("OK — inga inkonsekvenser.")
    print(f"--- {len(errors)} error, {len(warns)} warn ---")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
