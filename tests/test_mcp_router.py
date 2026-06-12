"""Tester för config-routern (scripts/mcp_router.py).

Ren resolve()-logik med ett FAKE-register + fake builders — ingen claude_agent_sdk,
ingen disk, ingen riktig GitHub-MCP. Verifierar per-roll-monteringen, fail-open på
saknad extern server, och bakåtkompatibel CNS-fallback.
"""
from __future__ import annotations

import os

import pytest

from scripts import mcp_router


# -- fixtures ---------------------------------------------------------------

def _registry() -> dict[str, dict]:
    """Litet register som speglar config/mcp_servers.json men utan disk-beroende."""
    return {
        "cns": {"kind": "sdk", "builder": "cns", "always": True,
                "provides": ["mcp__cns__", "cortxt_"]},
        "web": {"kind": "sdk", "builder": "web", "always": True,
                "provides": ["mcp__web__"]},
        "github": {"kind": "stdio", "provides": ["mcp__github__"],
                   "command_env": "GITHUB_MCP_COMMAND", "args": ["stdio"],
                   "url_env": "GITHUB_MCP_URL", "token_env": "GITHUB_MCP_TOKEN",
                   "token_header": "Authorization", "token_header_prefix": "Bearer ",
                   "token_env_passthrough": "GITHUB_PERSONAL_ACCESS_TOKEN"},
    }


def _builders():
    """Fake in-process-builders: returnerar markörsträngar i stället för riktiga servrar."""
    return {"cns": lambda: "CNS_SERVER", "web": lambda: "WEB_SERVER"}


_SDK_TOOLS = {"cns": ["mcp__cns__list_nodes", "mcp__cns__get_node"], "web": ["mcp__web__fetch"]}


@pytest.fixture(autouse=True)
def _clear_github_env(monkeypatch):
    for var in ("GITHUB_MCP_COMMAND", "GITHUB_MCP_URL", "GITHUB_MCP_TOKEN",
                "GITHUB_PERSONAL_ACCESS_TOKEN"):
        monkeypatch.delenv(var, raising=False)


def _resolve(role_tools, **kw):
    return mcp_router.resolve(
        role_tools,
        builders=kw.pop("builders", _builders()),
        sdk_tool_names=kw.pop("sdk_tool_names", _SDK_TOOLS),
        registry=kw.pop("registry", _registry()),
        **kw,
    )


# -- baseline / cns alltid --------------------------------------------------

def test_cns_always_mounted_even_with_empty_role():
    servers, allowed, warnings = _resolve([])
    assert servers["cns"] == "CNS_SERVER"
    # CNS-verktygen finns i allowed (bakåtkompatibel fallback för rollösa pass).
    assert "mcp__cns__list_nodes" in allowed
    # Läsverktygen är baseline.
    assert {"Read", "Glob", "Grep"} <= set(allowed)
    assert warnings == []


def test_web_mounted_when_builder_present():
    servers, _allowed, _w = _resolve([])
    assert servers["web"] == "WEB_SERVER"


def test_web_skipped_silently_when_builder_returns_none():
    builders = {"cns": lambda: "CNS_SERVER", "web": lambda: None}
    servers, _allowed, warnings = _resolve([], builders=builders)
    assert "web" not in servers
    assert warnings == []  # baseline-server som degraderar → tyst


# -- per-roll extern montering (github) -------------------------------------

def test_github_mounted_when_role_has_github_tool_and_env_set(monkeypatch):
    monkeypatch.setenv("GITHUB_MCP_COMMAND", "github-mcp-server")
    servers, allowed, warnings = _resolve(["mcp__github__create_pull_request"])
    assert servers["github"] == {"type": "stdio", "command": "github-mcp-server",
                                 "args": ["stdio"]}
    assert "mcp__github__create_pull_request" in allowed
    assert warnings == []


def test_github_http_config_with_bearer_token(monkeypatch):
    monkeypatch.setenv("GITHUB_MCP_URL", "https://github-mcp.example/mcp")
    monkeypatch.setenv("GITHUB_MCP_TOKEN", "tok123")
    servers, _allowed, _w = _resolve(["mcp__github__get_issue"])
    assert servers["github"]["type"] == "http"
    assert servers["github"]["headers"]["Authorization"] == "Bearer tok123"


def test_github_not_mounted_for_role_without_github_tool(monkeypatch):
    monkeypatch.setenv("GITHUB_MCP_COMMAND", "github-mcp-server")
    servers, allowed, warnings = _resolve(["cortxt_list_open_issues"])
    assert "github" not in servers  # backend-liknande roll utan github-verktyg
    assert not any("mcp__github__" in t for t in allowed)


def test_github_skipped_with_warning_when_env_missing():
    # Rollen VILL ha github men ingen env är satt → fail-open: skip + warning.
    servers, allowed, warnings = _resolve(["mcp__github__create_pull_request"])
    assert "github" not in servers
    assert any("github" in w for w in warnings)
    # Passet klarar sig ändå på CNS.
    assert servers["cns"] == "CNS_SERVER"


# -- allowed_tools-sammansättning -------------------------------------------

def test_write_tools_added_only_when_allow_writes():
    _s, allowed_ro, _w = _resolve([])
    assert not ({"Write", "Edit", "Bash"} & set(allowed_ro))
    _s, allowed_rw, _w = _resolve([], allow_writes=True)
    assert {"Write", "Edit", "Bash"} <= set(allowed_rw)


def test_allowed_tools_are_deduped():
    _s, allowed, _w = _resolve(["mcp__cns__list_nodes"])
    assert allowed.count("mcp__cns__list_nodes") == 1


# -- registerladdning från disk ---------------------------------------------

def test_load_registry_reads_real_config_file():
    reg = mcp_router.load_registry()
    assert "cns" in reg and "github" in reg
    assert reg["cns"]["always"] is True
    assert "_doc" not in reg  # kommentarsnycklar filtreras
