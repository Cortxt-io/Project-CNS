"""Roll-laddning för roll-medveten exekvering (#90 — så agenterna FAKTISKT jobbar).

Laddar en agents definition (``.claude/agents/<slug>.md``) → system_prompt + modell +
verktyg, så ``agent_host`` kan köra ett pass SOM den agenten (rätt identitet, beteende,
modell) i stället för generisk Claude. Bryggar ``agentur_routing.route()`` → roll:
``route(node.type, issue.type) → squad → load_role(squad[0])``.

**Plan A/B-väggen:** agent_host + denna modul ÄR verktygsladan (Plan A-infra), så att läsa
``.claude/agents/`` här är Plan A→Plan A — inte produktkod→``.claude/``. Produktkod (app/,
json_exporter) läser fortfarande bara den projicerade ``exports/agents.json`` (#46).

Ren, testbar parsning (``parse_role`` tar en sträng). Degraderar tyst: saknad fil/roll → None,
så agent_host faller tillbaka på generiskt beteende.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Dela en agent-.md i (frontmatter-dict, body). Lätt YAML-parse (key: value)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    fm: dict[str, str] = {}
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        line = lines[i]
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
        i += 1
    body = "\n".join(lines[i + 1 :]) if i < len(lines) else ""
    return fm, body.strip()


def _parse_tools(body: str) -> list[str]:
    """Plocka ut verktygen ur ``## Tillåtna verktyg``-sektionen (punktlista)."""
    lines = body.splitlines()
    tools: list[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = "tillåtna verktyg" in stripped.lower()
            continue
        if in_section and stripped.startswith(("-", "*")):
            item = stripped.lstrip("-* ").strip()
            # En rad kan lista flera kommaseparerade verktyg.
            tools.extend(t.strip() for t in item.split(",") if t.strip())
    return tools


def _parse_bool(value: str) -> bool:
    return value.strip().strip("\"'").lower() in ("true", "yes", "1")


def parse_role(text: str) -> dict:
    """Tolka en agent-.md (sträng) → roll-dict.

    Nycklar: slug?, title, model, status, department, sub_department, lead, system_prompt,
    ``tools_override`` (rollens ``## Tillåtna verktyg``) och ``tools``. **Ren parse** (ingen
    matris-IO): här är ``tools == tools_override``; den matris-härledda baslinjen läggs på i
    :func:`load_role` (C1, se ``scripts/tool_families.py``). ``system_prompt`` = hela body:n.
    """
    fm, body = _split_frontmatter(text)
    override = _parse_tools(body)
    return {
        "slug": fm.get("name", ""),
        "title": fm.get("title", ""),
        "model": fm.get("model", ""),
        "status": fm.get("status", ""),
        "department": fm.get("department", ""),
        "sub_department": fm.get("sub_department", ""),
        "lead": _parse_bool(fm.get("lead", "")),
        "system_prompt": body,
        "tools_override": override,
        "tools": override,  # ren default; load_role ersätter med den härledda uppsättningen
    }


def load_role(slug: str, *, matris: dict | None = None) -> dict | None:
    """Läs ``.claude/agents/<slug>.md`` → roll-dict med C1-härledda verktyg, None om filen saknas.

    ``tools`` blir matris-baslinjen (cellens ``tool_families``) UNION rollens override.
    ``matris`` kan injiceras (test); annars läses ``bemanning_matris.json`` från disk.
    """
    if not slug:
        return None
    path = AGENTS_DIR / f"{slug}.md"
    if not path.exists():
        return None
    try:
        role = parse_role(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    role["slug"] = role.get("slug") or slug
    try:
        from scripts.tool_families import effective_tools

        role["tools"] = effective_tools(role, matris=matris)
    except Exception:
        pass  # degradera till override (redan satt i parse_role)
    return role


def role_for_node(
    slug: str | None,
    issue_type: str = "story",
    *,
    agents: list[dict] | None = None,
) -> dict | None:
    """Brygga route()→roll: härled nodens type/domain, routa, ladda den valda agentens roll.

    Returnerar None (→ generiskt beteende) om noden/disciplinen/rollen inte kan resolvas.
    """
    if not slug:
        return None
    try:
        from scripts.md_parser import read_node

        meta, _sections, _raw = read_node(slug)
    except Exception:
        return None
    node_type = str(meta.get("type", "") or "")
    domain = str(meta.get("domain", "") or "") or None
    try:
        from scripts.agentur_routing import route
        from scripts.capabilities import required_capabilities

        req = required_capabilities(node_type, integrations=meta.get("integrations"))
        result = route(node_type, issue_type, domain=domain, agents=agents,
                       required_capabilities=req)
    except Exception:
        return None
    squad = result.get("squad") or []
    if not squad:
        return None
    role = load_role(squad[0])
    if role is not None:
        role["routed"] = {
            "agentur": result.get("agentur"),
            "station": result.get("station"),
            "model_tier": result.get("model"),
            "squad": squad,
        }
    return role
