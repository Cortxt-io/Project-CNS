"""Generera org-registret ur agent-frontmatter.

Läser frontmatter i .claude/agents/*.md (aktiva) + .claude/org/roster/*.md (skal),
och genererar:
  - scripts/agent_registry.py  (MODEL_TIER för aktiva, DEPARTMENT + ROSTER för alla)
  - .claude/agents/AGENTUR.md   (org-schema avd→underavd→roll)

router.py importerar MODEL_TIER/DEPARTMENT härifrån istället för handkodning.
Kör: python scripts/gen_agentur.py
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / ".claude" / "agents"
ROSTER_DIR = ROOT / ".claude" / "org" / "roster"
REGISTRY = ROOT / "scripts" / "agent_registry.py"
AGENTUR = AGENTS_DIR / "AGENTUR.md"

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


def write_registry(agents: list[dict]) -> None:
    active = [a for a in agents if a["_active"]]
    model_tier = {a["name"]: a.get("model", "claude-haiku-4-5") for a in active}
    department = {a["name"]: a.get("department", "?") for a in agents}
    roster = [{
        "slug": a["name"], "title": a.get("title", a["name"]),
        "department": a.get("department", "?"),
        "sub_department": a.get("sub_department", "null"),
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
    REGISTRY.write_text("\n".join(lines), encoding="utf-8")


def write_agentur(agents: list[dict]) -> None:
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
            out.append("| slug | titel | modell | roll | status |")
            out.append("|------|-------|--------|------|--------|")
            for r in sorted(roles, key=lambda x: (x.get("lead") != "true", x["name"])):
                lead = "lead" if r.get("lead") == "true" else "—"
                status = "aktiv" if r["_active"] else "skal"
                model = r.get("model", "?").replace("claude-", "")
                out.append(f"| `{r['name']}` | {r.get('title','')} | {model} | {lead} | {status} |")
            out.append("")
    AGENTUR.write_text("\n".join(out), encoding="utf-8")


def main() -> None:
    agents = load_agents()
    write_registry(agents)
    write_agentur(agents)
    n_active = sum(1 for a in agents if a["_active"])
    print(f"Genererat: {len(agents)} roller ({n_active} aktiva) -> agent_registry.py + AGENTUR.md")


if __name__ == "__main__":
    main()
