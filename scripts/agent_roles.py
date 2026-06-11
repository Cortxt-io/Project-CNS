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


def parse_role(text: str) -> dict:
    """Tolka en agent-.md (sträng) → {slug?, title, model, status, department, system_prompt, tools}.

    ``system_prompt`` = hela body:n (rollens identitet + uppgift + gräns + ev. sektioner).
    """
    fm, body = _split_frontmatter(text)
    return {
        "slug": fm.get("name", ""),
        "title": fm.get("title", ""),
        "model": fm.get("model", ""),
        "status": fm.get("status", ""),
        "department": fm.get("department", ""),
        "sub_department": fm.get("sub_department", ""),
        "system_prompt": body,
        "tools": _parse_tools(body),
    }


def load_role(slug: str) -> dict | None:
    """Läs ``.claude/agents/<slug>.md`` → roll-dict, eller None om filen saknas."""
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

        result = route(node_type, issue_type, domain=domain, agents=agents)
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
