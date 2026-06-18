"""C1-härledning: en rolls verktyg härleds ur bemanningsmatrisen, inte handlistas.

Seam: roll (``department`` + härledd nivå) → ``bemanning_matris.json:cells[dep|nivå].
tool_families`` → families. Rollens ``## Tillåtna verktyg`` blir **override** ovanpå
baslinjen (full kontroll kvar hos rollförfattaren; t.ex. externa verktyg som
``mcp__github__*`` eller domäner matrisen inte täcker). Saknas cellen → bara override
(bakåtkompat). Samma härlednings-princip som ``catalog.derive_kind`` och ``role_for_node``.

Familjenamn (``issues``, ``prs`` …) konsumeras direkt av ``mcp_router``/``registry.
local_names_for`` (universum B) och matchas mot externa servrars ``provides`` (universum A).
Ren/testbar: matrisen kan injiceras; default läses från disk.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MATRIS_PATH = REPO_ROOT / ".claude" / "org" / "bemanning_matris.json"

# Universell baslinje: families varje roll får oavsett matriscell. Bokföring (sessions)
# och idé-fångst (ideas) är agent-hygien som fanns i nästan varje rolls override — hoisat
# hit så det inte behöver upprepas per cell. Övriga families är disciplin-specifika (matris).
BASELINE_FAMILIES: tuple[str, ...] = ("sessions", "ideas")


def load_matris(path: str | Path | None = None) -> dict:
    """Läs bemanningsmatrisen. Tom dict om filen saknas/trasig (degradera till override)."""
    try:
        return json.loads(Path(path or MATRIS_PATH).read_text(encoding="utf-8"))
    except Exception:
        return {}


def derive_level(role: dict) -> str:
    """Härled matris-nivå ur rollen: exec (Ledning) | lead (lead:true) | ic (övriga).

    Speglar matrisens egen regel (``bemanning_matris.json:_doc``).
    """
    if (role.get("department") or "").strip() == "Leadership":
        return "exec"
    if role.get("lead"):
        return "lead"
    return "ic"


def families_for_cell(department: str, level: str, matris: dict) -> list[str]:
    """Matriscellens ``tool_families`` för (department|nivå); tom lista om cellen saknas."""
    cell = (matris.get("cells") or {}).get(f"{department}|{level}")
    if not cell:
        return []
    return list(cell.get("tool_families") or [])


def effective_tools(role: dict, *, matris: dict | None = None) -> list[str]:
    """Rollens effektiva verktyg: matris-families (baslinje) UNION rollens override.

    Override = rollens ``## Tillåtna verktyg`` (``role['tools_override']``). Ordning:
    families först, sedan override; dubbletter tas bort. Saknas matriscell → bara override.
    """
    if matris is None:
        matris = load_matris()
    department = (role.get("department") or "").strip()
    level = derive_level(role)
    base = list(BASELINE_FAMILIES) + families_for_cell(department, level, matris)
    override = list(role.get("tools_override") or [])
    seen: set[str] = set()
    out: list[str] = []
    for t in base + override:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out
