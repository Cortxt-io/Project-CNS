"""Levande bygg-cookbooks — AI-underhållna per produkt.

Agenturen läser en produkts faktiska läge (catalog-noder + roadmap) och *genererar* en
strukturerad bygg-cookbook (UI/UX + backend, ordnade steg) anpassad till var produkten står.
Levande: kör om generatorn när produkten ändras → cookbooken fräschas.

En källa (genererad JSON i ``cookbooks/<domain>.json``) → tre vyer: referens (läs, byggd),
checklista (per-produkt ``done`` på ``step.key``, senare), agent-playbook (``agent_hint`` per
steg, senare).

Återanvänder LLM-seamen + git-push (``analyst._call_claude``, ``git_ops.push_file_immediately``).
Generera OFFLINE (CLI/CI) — inte i en web-request; appen läser den committade filen.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
COOKBOOKS_DIR = ROOT / "cookbooks"

# Den DELADE DNA:n — hur man bygger en Cortxt-produkt rätt. Driver kvalitet + form;
# den per-produkt-anpassade outputen genereras ur {detta + produktens nuläge}.
SYSTEM_PROMPT = """Du är en senior bygg-coach för Cortxt — ett lokalt-först, beslutsstöds-fokuserat
produkthus. Du skriver en LEVANDE bygg-cookbook för EN produkt: konkreta, ordnade steg för hur man
bygger den rätt mot första betalande/återkommande användare, anpassade till var produkten står NU.

Delad approach (anpassa till produktens stack, hitta inte på framework-tutorials):
- UI/UX: tydlig informationsarkitektur, återanvänd designsystem (shadcn/@cortxt/ui-anda), enkla
  flöden, tillgänglighet (färg alltid parad med text), ärliga tomma/fel-tillstånd, mobil först.
- Backend: modellera datan/beslutslogiken först, smal typad API-yta, auth-söm tidigt, deploy-väg
  och observability, transparent (ingen rådgivning som låtsas vara fakta).

Regler:
- Härled stegen ur produktens FAKTISKA läge (noder, roadmap-fas, öppna beslut) — generiskt är värdelöst.
- Ordnade, körbara steg. Inga floskler. Svenska.
- Returnera ENBART giltig JSON, exakt denna form:
{
  "title": "<produktnamn> — bygg-cookbook",
  "summary": "<1-2 meningar om var produkten står och vad guiden täcker>",
  "steps": [
    {"key": "<stabil-kebab-id>", "discipline": "ui_ux" | "backend",
     "title": "<kort steg-titel>", "detail": "<2-4 meningar: vad, varför, hur>",
     "agent_hint": "<en mening: vad en agent skulle göra för detta steg>"}
  ]
}
10-16 steg, blandat ui_ux och backend, i bygg-ordning."""


def _build_cookbook_context(domain: str) -> str:
    """Markdown-kontext om produkten: dess catalog-noder + roadmap. Matas till modellen."""
    parts = [f"# Produkt: {domain}\n"]
    try:
        from scripts.catalog import load_catalog
        cat = load_catalog()
        nodes = [(s, n) for s, n in cat.items() if n.get("domain") == domain]
        parts.append("## System/komponenter (catalog)")
        if not nodes:
            parts.append("(inga modellerade noder än)")
        for s, n in nodes:
            parts.append(
                f"- **{s}** ({n.get('type', '?')}, {n.get('kind') or 'nod'}): {n.get('summary', n.get('title', ''))}"
                + (f" · part_of={n['part_of']}" if n.get('part_of') else "")
                + (f" · feeds={n['feeds']}" if n.get('feeds') else "")
                + (f" · depends_on={n['depends_on']}" if n.get('depends_on') else "")
            )
    except Exception as exc:
        parts.append(f"(kunde inte läsa catalog: {exc})")

    try:
        from scripts.roadmap import load_roadmap, load_recipe
        rm = load_roadmap(domain)
        if rm:
            parts.append("\n## Roadmap (var produkten är)")
            parts.append(f"Aktuell fas: {rm.get('current_phase')}")
            recipe = {p['key']: p.get('title') for p in load_recipe()['phases']}
            for key, pdata in (rm.get('phases') or {}).items():
                epics = pdata.get('epics') or []
                if epics:
                    parts.append(f"- {recipe.get(key, key)} ({pdata.get('status', 'todo')}): "
                                 + "; ".join(e.get('title', '') for e in epics))
            decs = rm.get('open_decisions') or []
            if decs:
                parts.append("Öppna beslut: " + "; ".join(d.get('title', '') for d in decs))
    except Exception:
        pass

    return "\n".join(parts)


def run_cookbook(domain: str, *, dry_run: bool = False, push: bool = True) -> dict:
    """Generera (eller torrkör) cookbooken för en produkt och persistera den.

    dry_run → bygg kontext + prompt men anropa INTE modellen (hermetiskt, gratis).
    """
    context = _build_cookbook_context(domain)
    user_prompt = f"Här är produktens nuläge:\n\n{context}\n\nSkriv dess bygg-cookbook (JSON)."

    if dry_run:
        return {"domain": domain, "dry_run": True, "context": context, "prompt": user_prompt}

    from scripts.analyst import _call_claude
    raw = _call_claude(SYSTEM_PROMPT, user_prompt, max_tokens=4096)
    data = json.loads(raw)
    data["domain"] = domain
    data["generated_at"] = date.today().isoformat()

    COOKBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    out = COOKBOOKS_DIR / f"{domain}.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    if push:
        try:
            from app.git_ops import push_file_immediately
            push_file_immediately(out, f"chore: regenerate cookbook for {domain}")
        except Exception:
            pass  # fail-open: lokal fil finns; push kräver token/repo

    return {"domain": domain, "generated_at": data["generated_at"], "steps": len(data.get("steps", []))}


def load_cookbook(domain: str) -> dict | None:
    """Läs den committade cookbooken (eller None om ingen genererats än). Transport-fri."""
    path = COOKBOOKS_DIR / f"{domain}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
