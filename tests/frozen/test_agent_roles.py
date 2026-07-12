"""Verifiering av roll-medveten exekvering (scripts/agent_roles.py + agent_host.build_seed, #90).

Ren parsning + bryggan route()→roll. Ingen SDK/disk behövs (read_node/route/load_role patchas).
Körs fristående (``python tests/test_agent_roles.py``) ELLER under pytest.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import agent_roles  # noqa: E402
from scripts.agent_roles import parse_role, load_role, role_for_node  # noqa: E402

_SAMPLE = """---
name: frontend-utvecklare
title: Frontend-utvecklare
department: Engineering
sub_department: Frontend
model: claude-sonnet-4-6
status: active
---

Du är Frontend-utvecklaren. Du bygger UI och äger komponentkvalitet.

## Tillåtna verktyg
- Read, Edit, Bash
- cortxt_list_open_issues

## Eval-kriterier
- Levererar tillgängligt UI
"""


def test_parse_role() -> None:
    r = parse_role(_SAMPLE)
    assert r["slug"] == "frontend-utvecklare"
    assert r["title"] == "Frontend-utvecklare"
    assert r["model"] == "claude-sonnet-4-6"
    assert r["status"] == "active" and r["sub_department"] == "Frontend"
    assert "Du är Frontend-utvecklaren" in r["system_prompt"]
    # Kommaseparerad rad + egen rad → platt verktygslista
    assert r["tools"] == ["Read", "Edit", "Bash", "cortxt_list_open_issues"]


def test_parse_role_without_frontmatter() -> None:
    r = parse_role("Bara en kropp utan frontmatter.")
    assert r["system_prompt"].startswith("Bara en kropp") and r["model"] == "" and r["tools"] == []


def test_load_role_missing_returns_none() -> None:
    assert load_role("finns-inte-xyz") is None
    assert load_role("") is None


def test_role_for_node_bridge() -> None:
    # Patcha de tre beroendena så bryggan kan testas utan disk/SDK.
    import scripts.md_parser as md
    import scripts.agentur_routing as ar

    orig_read, orig_route, orig_load = md.read_node, ar.route, agent_roles.load_role
    md.read_node = lambda slug: ({"type": "frontend", "domain": "cortxt"}, {}, "")
    ar.route = lambda nt, it, **kw: {"agentur": "produktutveckling", "station": "delivery",
                                     "model": "sonnet", "squad": ["frontend-utvecklare"]}
    agent_roles.load_role = lambda slug: parse_role(_SAMPLE) if slug == "frontend-utvecklare" else None
    try:
        role = role_for_node("cortxt-dashboard-app", "bug")
        assert role is not None
        assert role["slug"] == "frontend-utvecklare"
        assert role["routed"]["station"] == "delivery"
        assert role["routed"]["model_tier"] == "sonnet"
        assert role["routed"]["agentur"] == "produktutveckling"
    finally:
        md.read_node, ar.route, agent_roles.load_role = orig_read, orig_route, orig_load


def test_role_for_node_degrades() -> None:
    import scripts.md_parser as md
    import scripts.agentur_routing as ar

    orig_read, orig_route = md.read_node, ar.route
    md.read_node = lambda slug: ({"type": "okänd", "domain": "cortxt"}, {}, "")
    ar.route = lambda nt, it, **kw: {"squad": []}  # tom squad → ingen roll
    try:
        assert role_for_node("nån-nod") is None
    finally:
        md.read_node, ar.route = orig_read, orig_route
    assert role_for_node(None) is None  # ingen slug → None


def test_build_seed_uses_role() -> None:
    # build_seed är ren (ingen SDK). Med roll → rollens prompt blir basen.
    from scripts.tui.agent_host import build_seed

    role = parse_role(_SAMPLE)
    seed = build_seed(None, role=role)
    assert seed.startswith("Du är Frontend-utvecklaren")
    assert "LÄS-LÄGE" in seed
    # Utan roll → generiska CNS-agenten
    generic = build_seed(None, role=None)
    assert generic.startswith("Du är CNS-agenten")


if __name__ == "__main__":
    test_parse_role()
    test_parse_role_without_frontmatter()
    test_load_role_missing_returns_none()
    test_role_for_node_bridge()
    test_role_for_node_degrades()
    test_build_seed_uses_role()
    print("OK - agent_roles: parse + load + brygga route-roll + build_seed roll-medveten grona")
