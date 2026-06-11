"""Generera org-registret ur agent-frontmatter.

Läser frontmatter i .claude/agents/*.md (aktiva) + .claude/org/roster/*.md (skal),
och genererar:
  - scripts/agent_registry.py  (MODEL_TIER för aktiva, DEPARTMENT + ROSTER för alla)
  - .claude/agents/AGENTUR.md   (org-schema avd→underavd→roll)
  - exports/agents.json         (Plan A/B artefakt — produktkod läser denna)

router.py importerar MODEL_TIER/DEPARTMENT härifrån istället för handkodning.
Kör: python scripts/gen_agentur.py
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / ".claude" / "agents"
ROSTER_DIR = ROOT / ".claude" / "org" / "roster"
MANIFEST = ROOT / ".claude" / "org" / "manifest.json"
REGISTRY = ROOT / "scripts" / "agent_registry.py"
AGENTUR = AGENTS_DIR / "AGENTUR.md"
AGENTS_JSON = ROOT / "exports" / "agents.json"

# Avdelningsordning för org-schemat
DEPT_ORDER = ["Ledning", "Produkt", "R&D", "Engineering", "Platform",
              "People", "Program", "Drift", "Ekonomi", "Kommunikation"]


def parse_frontmatter(text: str) -> dict:
    """Enkel frontmatter-läsare: skalärt key: value mellan inledande --- och nästa ---."""
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


def load_squads() -> dict[str, list[str]]:
    """squad-namn -> medlems-slugs, ur manifest.json."""
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return data.get("squads", {})


def stamp_squads(slug2squad: dict[str, str]) -> int:
    """Skriv in squad-fältet i varje medlems frontmatter (idempotent)."""
    stamped = 0
    for d in (AGENTS_DIR, ROSTER_DIR):
        if not d.exists():
            continue
        for path in d.glob("*.md"):
            if path.name == "AGENTUR.md":
                continue
            text = path.read_text(encoding="utf-8")
            fm = parse_frontmatter(text)
            slug = fm.get("name")
            if not slug or "squad" not in fm:
                continue
            want = slug2squad.get(slug, "null")
            if fm.get("squad") == want:
                continue
            new = re.sub(r"^squad:.*$", f"squad: {want}", text, count=1, flags=re.MULTILINE)
            if new != text:
                path.write_text(new, encoding="utf-8")
                stamped += 1
    return stamped


def load_agents() -> list[dict]:
    agents = []
    for path in sorted(AGENTS_DIR.glob("*.md")):
        if path.name == "AGENTUR.md":
            continue
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not fm.get("name"):
            continue
        fm["_active"] = True
        agents.append(fm)
    for path in sorted(ROSTER_DIR.glob("*.md")) if ROSTER_DIR.exists() else []:
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not fm.get("name"):
            continue
        fm["_active"] = (fm.get("status") == "active")
        agents.append(fm)
    return agents


def write_registry(agents: list[dict], squads: dict[str, list[str]]) -> None:
    active = [a for a in agents if a["_active"]]
    model_tier = {a["name"]: a.get("model", "claude-haiku-4-5") for a in active}
    department = {a["name"]: a.get("department", "?") for a in agents}
    roster = [{
        "slug": a["name"], "title": a.get("title", a["name"]),
        "department": a.get("department", "?"),
        "sub_department": a.get("sub_department", "null"),
        "squad": a.get("squad", "null"),
        "model": a.get("model", "claude-haiku-4-5"),
        "lead": a.get("lead", "false") == "true",
        "active": a["_active"],
    } for a in agents]

    lines = ['"""GENERERAD av scripts/gen_agentur.py — redigera inte för hand."""', ""]
    lines.append("# Modell-tier för AKTIVA agenter (router-override).")
    lines.append("MODEL_TIER = {")
    for k, v in sorted(model_tier.items()):
        lines.append(f'    {k!r}: {v!r},')
    lines.append("}")
    lines.append("")
    lines.append("# Avdelning per slug (alla roller, aktiva + skal).")
    lines.append("DEPARTMENT = {")
    for k, v in sorted(department.items()):
        lines.append(f'    {k!r}: {v!r},')
    lines.append("}")
    lines.append("")
    lines.append("# Full roster (org-registret).")
    lines.append("ROSTER = [")
    for r in sorted(roster, key=lambda x: (x["department"], x["sub_department"], x["slug"])):
        lines.append(f"    {r!r},")
    lines.append("]")
    lines.append("")
    lines.append("# Tvärfunktionella squads (mission-team) -> medlems-slugs.")
    lines.append("SQUADS = {")
    for name, members in sorted(squads.items()):
        lines.append(f"    {name!r}: {list(members)!r},")
    lines.append("}")
    lines.append("")
    REGISTRY.write_text("\n".join(lines), encoding="utf-8")


def write_agentur(agents: list[dict], squads: dict[str, list[str]]) -> None:
    # gruppera department -> sub_department -> roller
    tree: dict[str, dict[str, list[dict]]] = {}
    for a in agents:
        d = a.get("department", "?")
        s = a.get("sub_department", "—")
        tree.setdefault(d, {}).setdefault(s, []).append(a)

    n_active = sum(1 for a in agents if a["_active"])
    out = [
        "# AGENTUR.md — org-schema (Plan A) — GENERERAD",
        "",
        "> Genererad av `scripts/gen_agentur.py` ur agent-frontmatter. **Redigera inte för hand** —",
        "> ändra rollerna i `.claude/agents/*.md` (aktiva) / `.claude/org/roster/*.md` (skal) och kör om.",
        "",
        f"**{len(agents)} roller** i registret, varav **{n_active} aktiva** (körbara i `.claude/agents/`).",
        "Resten är skal i org-registret (`.claude/org/roster/`) — bemannas vid behov.",
        "",
        "Princip: agenter = anställda, skills = kompetenser. Matris (Spotify): department +",
        "sub_department (linjen) × squad (mission) × chapter (disciplin) × guild (skills `Gemensam`).",
        "",
        "Aktiva rostern hålls liten (playbook: 7–10 aktiva åt gången). VD = Rikard (ej agentfil).",
        "",
    ]
    for dept in DEPT_ORDER + [d for d in tree if d not in DEPT_ORDER]:
        if dept not in tree:
            continue
        out.append(f"## {dept}")
        out.append("")
        for sub, roles in tree[dept].items():
            out.append(f"### {sub}")
            out.append("")
            out.append("| slug | titel | modell | roll | squad | status |")
            out.append("|------|-------|--------|------|-------|--------|")
            for r in sorted(roles, key=lambda x: (x.get("lead") != "true", x["name"])):
                lead = "lead" if r.get("lead") == "true" else "—"
                status = "aktiv" if r["_active"] else "skal"
                model = r.get("model", "?").replace("claude-", "")
                squad = r.get("squad", "null")
                squad_cell = squad if squad and squad != "null" else "—"
                out.append(f"| `{r['name']}` | {r.get('title','')} | {model} | {lead} | {squad_cell} | {status} |")
            out.append("")
    if squads:
        out.append("## Squads (tvärfunktionella mission-team)")
        out.append("")
        out.append("Ortogonalt mot avdelning: *vad* vi bygger (produktområde), tvärfunktionellt bemannat.")
        out.append("")
        out.append("| squad | medlemmar |")
        out.append("|-------|-----------|")
        for name, members in sorted(squads.items()):
            out.append(f"| **{name}** | {', '.join(f'`{m}`' for m in members)} |")
        out.append("")
    AGENTUR.write_text("\n".join(out), encoding="utf-8")


def _norm(val: str | None) -> str:
    """Normalisera "null"/None → tom sträng för ren JSON-output."""
    if not val or val == "null":
        return ""
    return val


def write_agents_json(agents: list[dict]) -> None:
    """Emittera exports/agents.json — Plan A/B artefakt för produktkod.

    Enda källan till agent-metadata utanför .claude/; produktkod (app/, json_exporter)
    läser denna fil, aldrig .claude/ direkt.
    """
    records = []
    for a in agents:
        records.append({
            "slug": a["name"],
            "title": a.get("title", a["name"]),
            "department": _norm(a.get("department")),
            "sub_department": _norm(a.get("sub_department")),
            "squad": _norm(a.get("squad")),
            "status": "active" if a["_active"] else "shell",
            "model": a.get("model", "claude-haiku-4-5"),
            "owns": [],
            "contributes_to": [],
        })
    records.sort(key=lambda x: (x["department"], x["sub_department"], x["slug"]))
    payload = {
        "generated_by": "scripts/gen_agentur.py",
        "agents": records,
    }
    AGENTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    AGENTS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    squads = load_squads()
    slug2squad = {slug: name for name, members in squads.items() for slug in members}
    stamped = stamp_squads(slug2squad)
    agents = load_agents()  # läs efter stämpling så squad-fältet är aktuellt
    write_registry(agents, squads)
    write_agentur(agents, squads)
    write_agents_json(agents)
    n_active = sum(1 for a in agents if a["_active"])
    print(f"Genererat: {len(agents)} roller ({n_active} aktiva), {len(squads)} squads, "
          f"{stamped} squad-stämplingar -> agent_registry.py + AGENTUR.md + exports/agents.json")


if __name__ == "__main__":
    main()
