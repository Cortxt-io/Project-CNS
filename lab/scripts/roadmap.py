"""Per-projekt roadmap — recept (delad mall) + per-vertikal plan (instans).

Det STRATEGISKA lagret i hybriden: CNS äger riktningen (recept-faser, var ett projekt
står, öppna beslut), GitHub-repona äger granulär exekvering (stories) senare. Återinför
en TUNN fas-axel (portfölj-roadmap, ej Jira-klon) motiverad av att vertikalerna ska
byggas om mot en nedskriven plan.

- Receptet (nivå 1, delat): ``roadmaps/_recipe.yaml`` — ordnade faser mot första
  betalande/återkommande användare. Enkälla, redigerbar.
- Planen (nivå 2, per vertikal): ``roadmaps/<slug>.md`` (YAML-frontmatter) — ``current_phase``,
  per fas ``{status, epics}``, och ``open_decisions``. Anpassas per stack/projekt.

Transport-fri och ren (mönster: ``catalog.py``/``health.py``). Degraderar tyst: saknad
fil → ``None`` (vertikal utan roadmap), aldrig en krasch.
"""
from __future__ import annotations

from pathlib import Path

# roadmaps/ ligger i repo-roten (bredvid catalog.yaml och decisions/); denna modul bor i
# lab/scripts/ → tre nivåer upp.
ROADMAPS_DIR = Path(__file__).resolve().parent.parent.parent / "roadmaps"
RECIPE_PATH = ROADMAPS_DIR / "_recipe.yaml"


def load_recipe() -> dict:
    """De delade faserna (nivå 1). ``{"phases": [{key, title, summary}, ...]}``.

    Tom (``{"phases": []}``) om filen saknas/ogiltig — konsumenter degraderar.
    """
    try:
        import yaml
        data = yaml.safe_load(RECIPE_PATH.read_text(encoding="utf-8")) or {}
        phases = data.get("phases") or []
        return {"phases": [p for p in phases if p.get("key")]}
    except Exception:
        return {"phases": []}


def load_roadmap(slug: str) -> dict | None:
    """Per-vertikal plan (nivå 2) ur ``roadmaps/<slug>.md`` (YAML-frontmatter), eller None.

    Returnerar frontmatter-dicten (current_phase, phases, open_decisions, …) plus ``body``.
    """
    path = ROADMAPS_DIR / f"{slug}.md"
    if not path.exists():
        return None
    try:
        import frontmatter
        post = frontmatter.load(str(path))
        data = dict(post.metadata)
        data["body"] = post.content
        return data
    except Exception:
        return None


def roadmap_summary(slug: str) -> dict | None:
    """Kompakt fas-/beslutsläge för cockpit-kortet (eller None om ingen roadmap).

    ``{current_phase, current_phase_title, phase_index, total_phases, open_decisions, next_decision}``.
    ``phase_index`` är 1-baserad position i receptet (0 om ``current_phase`` ej matchar).
    """
    rm = load_roadmap(slug)
    if rm is None:
        return None
    phases = load_recipe()["phases"]
    keys = [p["key"] for p in phases]
    titles = {p["key"]: p.get("title", p["key"]) for p in phases}
    current = rm.get("current_phase")
    phase_index = keys.index(current) + 1 if current in keys else 0
    decisions = rm.get("open_decisions") or []
    return {
        "current_phase": current,
        "current_phase_title": titles.get(current, current),
        "phase_index": phase_index,
        "total_phases": len(keys),
        "open_decisions": len(decisions),
        "next_decision": (decisions[0].get("title") if decisions else None),
    }


def roadmap_detail(slug: str) -> dict | None:
    """Full roadmap för per-projekt-vyn: receptets faser slagna med projektets status/epics.

    Returnerar ``{slug, current_phase, phases: [{key, title, summary, status, epics:[{title,done}]}],
    open_decisions: [{title, why}]}`` — eller None.
    """
    rm = load_roadmap(slug)
    if rm is None:
        return None
    recipe = load_recipe()["phases"]
    proj_phases = rm.get("phases") or {}
    phases_out = []
    for p in recipe:
        pdata = proj_phases.get(p["key"]) or {}
        phases_out.append({
            "key": p["key"],
            "title": p.get("title", p["key"]),
            "summary": p.get("summary", ""),
            "status": pdata.get("status", "todo"),
            "epics": pdata.get("epics") or [],
        })
    return {
        "slug": slug,
        "current_phase": rm.get("current_phase"),
        "phases": phases_out,
        "open_decisions": rm.get("open_decisions") or [],
    }
