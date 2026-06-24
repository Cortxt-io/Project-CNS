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

EVOLVERA, regenerera ALDRIG från noll: om en föregående version bifogas, UPPDATERA den. Behåll varje
stegs ``key`` och dess ``done``-status (höj false→true bara om nuläget visar att det är klart, aldrig
true→false utan skäl). Reflektera vad som ändrats; addera steg när produkten växt, pensionera bara det
som inte längre gäller. En levande tråd, inte en ny snapshot.

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
     "nodes": ["<slug>", ...],
     "agent_hint": "<en mening: vad en agent skulle göra för detta steg>"}
  ]
}
10-16 steg, blandat ui_ux och backend, i bygg-ordning. ``nodes`` = de katalog-slug(s) steget rör
(en eller flera; tom lista om tvärgående) — använd EXAKT slug:arna ur kontextens nodlista så
bygg-guiden korslänkar mot arkitektur-grafen."""


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


def _have_key() -> bool:
    """ANTHROPIC_API_KEY satt (env eller otrackad .cns-agent-key)? Annars → abonnemang via SDK."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"] != "your_key_here"
    keyfile = ROOT / ".cns-agent-key"
    if keyfile.exists():
        try:
            k = keyfile.read_text(encoding="utf-8").strip().splitlines()[0].strip()
            if k:
                os.environ["ANTHROPIC_API_KEY"] = k
                return True
        except Exception:
            pass
    return False


def _generate(system: str, user: str, max_tokens: int = 4096) -> str:
    """LLM-anrop: rå API-nyckel om satt, annars Claude Code-abonnemang via claude_agent_sdk.

    Samma auth-anda som agent_host.py (nyckel → .cns-agent-key → Claude Code-login).
    """
    if _have_key():
        from scripts.analyst import _call_claude
        return _call_claude(system, user, max_tokens=max_tokens)

    # Inget nyckel → kör på abonnemanget (Claude Code-login) via SDK:n.
    import asyncio
    import re
    from claude_agent_sdk import query, ClaudeAgentOptions

    async def _run() -> str:
        chunks: list[str] = []
        options = ClaudeAgentOptions(system_prompt=system, max_turns=1)
        async for msg in query(prompt=user, options=options):
            for block in getattr(msg, "content", []) or []:
                t = getattr(block, "text", None)
                if t:
                    chunks.append(t)
        return "".join(chunks)

    raw = asyncio.run(_run()).strip()
    raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
    raw = re.sub(r"\n?```\s*$", "", raw)
    return raw.strip()


def run_cookbook(domain: str, *, dry_run: bool = False, push: bool = True) -> dict:
    """Generera (eller torrkör) cookbooken för en produkt och persistera den.

    EVOLVERAR: läser föregående cookbook och matar in den så modellen uppdaterar (regenererar
    ej från noll); ``done`` per ``key`` återställs i kod så ackumulerad progress överlever.
    dry_run → bygg kontext + prompt men anropa INTE modellen (hermetiskt, gratis).
    """
    context = _build_cookbook_context(domain)
    prev = load_cookbook(domain)
    prev_block = (
        "\n\n## Föregående cookbook (UPPDATERA denna, regenerera inte):\n"
        + json.dumps(prev, ensure_ascii=False)
    ) if prev else ""
    user_prompt = (
        f"Här är produktens nuläge:\n\n{context}{prev_block}\n\n"
        "Uppdatera/skriv dess bygg-cookbook (JSON)."
    )

    if dry_run:
        return {"domain": domain, "dry_run": True, "context": context, "prompt": user_prompt,
                "evolves_from_previous": prev is not None}

    raw = _generate(SYSTEM_PROMPT, user_prompt, max_tokens=4096)
    data = json.loads(raw)
    data["domain"] = domain
    data["generated_at"] = date.today().isoformat()
    data["source"] = "generated"

    # Bevara done per key (modellen får höja, inte sänka).
    if prev:
        prev_done = {s["key"]: s.get("done") for s in prev.get("steps", []) if s.get("key")}
        for s in data.get("steps", []):
            if not s.get("done") and prev_done.get(s.get("key")):
                s["done"] = True

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
