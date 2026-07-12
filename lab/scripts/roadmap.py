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


def current_phase(slug: str) -> dict:
    """Var står bygget? **Mätt, inte påstått.**

    ``current_phase`` var ett handfält i ``roadmaps/<slug>.md`` — och det var FEL i varenda
    vertikal (orgkomp sa "spec" men låg live; bkfinans sa "spec" men låg live; crusade sa "spec"
    men stod i mvp). Ett fält ingen har anledning att uppdatera blir alltid osant.

    Nu härleds det ur verkligheten: repot, deployen, testerna. Samma nyckel ut till cockpiten —
    men källan är en mätning. Degraderar tyst till ``{}`` om härledningen inte går.
    """
    try:
        from . import phase_derive, signals, vault_reader
        from scripts.catalog import load_catalog

        entry = load_catalog().get(slug, {})
        note = vault_reader.load_annotations().get(slug)
        sig = signals.collect(slug, catalog_entry=entry, annotation=note)
        return phase_derive.derive_phase(
            load_recipe(), signals=sig, checked=signals.checked_steps(note)
        )
    except Exception:
        return {}


def roadmap_summary(slug: str) -> dict | None:
    """Kompakt fas-/beslutsläge för cockpit-kortet (eller None om ingen roadmap).

    ``{current_phase, current_phase_title, phase_index, total_phases, open_decisions,
    next_decision, gates_skipped}``. ``phase_index`` är 1-baserad position i receptet.

    ``current_phase`` HÄRLEDS (se ``current_phase()``) — ``roadmaps/<slug>.md`` bär det inte
    längre. ``gates_skipped`` är skulden: grindar bygget passerade utan att stänga.
    """
    rm = load_roadmap(slug)
    if rm is None:
        return None
    phases = load_recipe()["phases"]
    keys = [p["key"] for p in phases]
    titles = {p["key"]: p.get("title", p["key"]) for p in phases}

    derived = current_phase(slug)
    current = derived.get("phase") or rm.get("current_phase")   # fallback tills allt är migrerat
    phase_index = keys.index(current) + 1 if current in keys else 0
    decisions = rm.get("open_decisions") or []
    return {
        "current_phase": current,
        "current_phase_title": titles.get(current, current),
        "phase_index": phase_index,
        "total_phases": len(keys),
        "open_decisions": len(decisions),
        "next_decision": (decisions[0].get("title") if decisions else None),
        "gates_skipped": derived.get("gates_skipped") or [],
    }


def roadmap_detail(slug: str) -> dict | None:
    """Full roadmap för per-projekt-vyn: receptets faser slagna med projektets epics.

    ``status`` per fas HÄRLEDS numera (fältet är borta ur filerna):

        passed   — bygget har passerat fasen OCH stängt dess grind
        skipped  — bygget har passerat fasen men grinden stängdes ALDRIG (skulden)
        active   — här står bygget nu
        todo     — inte nådd än

    ``skipped`` är den nya statusen, och den viktigaste: den är skillnaden mellan att ha byggt
    något och att ha byggt det ordentligt. Tre av vertikalerna ligger live med fyra skipped var.

    Returnerar ``{slug, current_phase, gates_skipped, phases: [...], open_decisions: [...]}``.
    """
    rm = load_roadmap(slug)
    if rm is None:
        return None

    recipe = load_recipe()["phases"]
    keys = [p["key"] for p in recipe]
    proj_phases = rm.get("phases") or {}

    derived = current_phase(slug)
    current = derived.get("phase")
    skipped = set(derived.get("gates_skipped") or [])
    steps = derived.get("steps") or {}
    current_index = keys.index(current) if current in keys else -1

    phases_out = []
    for i, p in enumerate(recipe):
        key = p["key"]
        if key in skipped:
            status = "skipped"
        elif current_index >= 0 and i < current_index:
            status = "passed"
        elif key == current:
            status = "active"
        else:
            status = "todo"

        pdata = proj_phases.get(key) or {}
        phases_out.append({
            "key": key,
            "title": p.get("title", key),
            "summary": p.get("summary", ""),
            "status": status,
            "epics": pdata.get("epics") or [],
            "steps": [
                {"key": s.get("key"), "title": s.get("title"),
                 "check": s.get("check"), "done": steps.get(s.get("key"))}
                for s in (p.get("steps") or [])
            ],
            "gate": p.get("gate") or {},
        })

    return {
        "slug": slug,
        "current_phase": current,
        "gates_skipped": sorted(skipped, key=lambda k: keys.index(k) if k in keys else 99),
        "phases": phases_out,
        "open_decisions": rm.get("open_decisions") or [],
    }
