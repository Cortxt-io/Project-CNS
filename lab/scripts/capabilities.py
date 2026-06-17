"""Kapabilitet som routningssignal (Del B — derived-catalog-and-capability-spec).

**Princip (B1/B3):** en agents kapabilitet HÄRLEDS ur dess `## Tillåtna verktyg` (+ ev.
skills) — ingen handlista som kan driva isär. Kapabilitet är ett *projektivt index* över
verktyg, inte en egen sanning. Projiceras in i `exports/agents.json` av `gen_agentur` så
`agentur_routing.route()` kan matcha på den utan att läsa `.claude/` (Plan A/B-väggen).

En kapabilitet är en normaliserad token:
- ``mcp__<server>__<tool>``  → ``<server>``   (github, cns, web, …) — "når denna MCP-server"
- ``cortxt_*``               → ``cns``         (CNS connector-verktyg)
- Write/Edit/Bash           → ``code``        (får skriva kod)
- Read/Glob/Grep            → ``read``        (läsverktyg)
- en skill ``<namn>``        → ``skill:<namn>``

Ren och testbar: tar in listor, returnerar listor. Inga sidoeffekter.
"""
from __future__ import annotations

_WRITE_TOOLS = {"Write", "Edit", "Bash"}
_READ_TOOLS = {"Read", "Glob", "Grep"}


def derive_capabilities(tools: list[str] | None, skills: list[str] | None = None) -> list[str]:
    """Härled kapabilitets-tokens ur en agents verktyg (+ skills). Sorterad, deduplicerad."""
    caps: set[str] = set()
    for t in tools or []:
        t = (t or "").strip()
        if not t:
            continue
        if t.startswith("mcp__"):
            parts = t.split("__")
            if len(parts) >= 3 and parts[1]:
                caps.add(parts[1])          # server-namn = kapabilitet
        elif t.startswith("cortxt_"):
            caps.add("cns")
        elif t in _WRITE_TOOLS:
            caps.add("code")
        elif t in _READ_TOOLS:
            caps.add("read")
    for s in skills or []:
        s = (s or "").strip()
        if s:
            caps.add(f"skill:{s}")
    return sorted(caps)


# Härledning av en NODS kapabilitetskrav (B2: ur node.type + integrations, valfri override).
# Minimal v1 — växer när fler node-typer/integrationer behöver styra. Disciplin = fallback,
# så en tom kravlista bryter aldrig befintlig routning.
_NODE_TYPE_CAPABILITY = {
    "mcp-server": ["code"],     # bygga/ändra en MCP-server kräver kodskrivning
    "service": ["code"],
    "frontend": ["code"],
    "cli": ["code"],
    "library": ["code"],
    "pipeline": ["code"],
}


def required_capabilities(
    node_type: str = "",
    *,
    integrations: dict | None = None,
    needs: list[str] | None = None,
) -> list[str]:
    """Härled vilka kapabiliteter ett arbete på en nod kräver.

    ``needs`` = explicit override (issue-label ``needs:<cap>``). ``integrations`` = nodens
    integrationsfält (#77): en ``deploy``-yta kräver den ytans kapabilitet (t.ex. vercel).
    """
    req: set[str] = set(needs or [])
    req.update(_NODE_TYPE_CAPABILITY.get(node_type, []))
    for surface in (integrations or {}).get("deploy", {}) or {}:
        if surface:
            req.add(str(surface))           # t.ex. "vercel", "railway"
    return sorted(req)


def capability_score(agent_caps: list[str] | None, required: list[str] | None) -> int:
    """Hur många av de krävda kapabiliteterna agenten täcker (för ranking)."""
    if not required:
        return 0
    have = set(agent_caps or [])
    return sum(1 for r in required if r in have)
