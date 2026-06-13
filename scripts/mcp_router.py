"""MCP-router (config-router) — per-roll val av MCP-servrar + verktyg för ett agent-pass.

**Problemet den löser:** ``agent_host.build_options`` monterade tidigare en HÅRDKODAD
serveruppsättning (bara ``cns`` + ev. web) och ignorerade vilka verktyg rollen faktiskt
fått. En agent kunde därför aldrig nå en extern MCP-server (GitHub-MCP m.fl.) oavsett roll.

**Seamet:** rollens ``## Tillåtna verktyg`` (parsas redan av ``agent_roles._parse_tools``).
Routern utgår från DEN listan — inte från nodfilformen — så CNS kan byggas om utan att röra
routningen. Se ``decisions/mcp-router.md``.

**Två steg i routerns evolution:** (a) denna *config-router* nu (serverregister i
``config/mcp_servers.json`` + montering per pass); (b) en separat ``mcp-gateway``-process
senare, när Plan B-agenter når många servrar / behöver central auth+allowlist.

Ren och testbar: ``resolve()`` tar injicerade builders + ett register (default läses från
disk) och importerar ALDRIG claude_agent_sdk. In-process-servrar (``cns``/``web``) byggs via
de injicerade builder-funktionerna; externa servrar (stdio/http) gatas på env och hoppas
**tyst över med en warning** om de inte är konfigurerade (fail-open — ett saknat GitHub-MCP
ska aldrig stjälpa ett pass som ändå klarar sig på CNS-verktygen).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = REPO_ROOT / "config" / "mcp_servers.json"

# Claude Codes egna verktyg (speglar agent_host-konstanterna; hålls här så routern
# inte importerar agent_host — agent_host importerar routern, inte tvärtom).
DEFAULT_READ_TOOLS = ["Read", "Glob", "Grep"]
DEFAULT_WRITE_TOOLS = ["Write", "Edit", "Bash"]


def load_registry(path: str | Path | None = None) -> dict[str, dict]:
    """Läs serverregistret från disk → {server_name: entry}. Tom dict om filen saknas/trasig."""
    p = Path(path) if path else DEFAULT_REGISTRY_PATH
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    servers = data.get("servers", data)  # tillåt både {"servers": {...}} och rå dict
    return {k: v for k, v in servers.items() if isinstance(v, dict) and not k.startswith("_")}


def _matches(tool: str, provides: list[str]) -> bool:
    """Matchar ett verktygsnamn mot en servers ``provides``-prefix."""
    return any(tool.startswith(prefix) for prefix in provides)


def _dedupe(items: list[str]) -> list[str]:
    """Bevara ordning, ta bort dubbletter."""
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def list_servers(registry: dict[str, dict] | None = None) -> list[dict]:
    """Diagnostik: vilka MCP-servrar registret känner + om de är konfigurerade (env satt).

    Returnerar [{name, kind, capability, configured, hint}] — för `cns mcp-servers`. En
    sdk-server är alltid tillgänglig (in-process); en extern är 'configured' när dess
    command_env eller url_env är satt i miljön.
    """
    registry = load_registry() if registry is None else registry
    out: list[dict] = []
    for name, entry in registry.items():
        kind = entry.get("kind", "")
        if kind == "sdk":
            configured, hint = True, "in-process (alltid tillgänglig)"
        else:
            cmd_env = entry.get("command_env")
            url_env = entry.get("url_env")
            has = bool((cmd_env and os.environ.get(cmd_env)) or (url_env and os.environ.get(url_env)))
            need = " eller ".join(x for x in (cmd_env, url_env) if x) or "env"
            tok = entry.get("token_env")
            configured = has
            hint = "konfigurerad" if has else f"sätt {need}" + (f" (+ {tok})" if tok else "")
        out.append({
            "name": name,
            "kind": kind,
            "capability": entry.get("capability", ""),
            "configured": configured,
            "hint": hint,
        })
    return out


def _build_external(name: str, entry: dict) -> tuple[dict | None, str | None]:
    """Bygg en McpServerConfig (stdio/http) för en extern server ur env.

    Returnerar ``(config, None)`` vid framgång, annars ``(None, warning)`` — fail-open.
    stdio kräver ``command_env`` satt; http kräver ``url_env`` satt. stdio prövas först.
    """
    # stdio: en lokal binär/kommando pekat ut av env.
    cmd_env = entry.get("command_env")
    command = os.environ.get(cmd_env) if cmd_env else None
    if command:
        cfg: dict[str, Any] = {"type": "stdio", "command": command}
        if entry.get("args"):
            cfg["args"] = list(entry["args"])
        env_passthrough = entry.get("token_env_passthrough")
        token = os.environ.get(entry["token_env"]) if entry.get("token_env") else None
        if env_passthrough and token:
            cfg["env"] = {env_passthrough: token}
        return cfg, None
    # http: en fjärr-endpoint pekat ut av env, ev. med bearer-token.
    url_env = entry.get("url_env")
    url = os.environ.get(url_env) if url_env else None
    if url:
        cfg = {"type": "http", "url": url}
        token = os.environ.get(entry["token_env"]) if entry.get("token_env") else None
        if token and entry.get("token_header"):
            prefix = entry.get("token_header_prefix", "")
            cfg["headers"] = {entry["token_header"]: f"{prefix}{token}"}
        return cfg, None
    hint = cmd_env or url_env or "env"
    return None, f"MCP-server '{name}' ej konfigurerad (sätt {hint}) — hoppas över"


def resolve(
    role_tools: list[str] | None,
    *,
    allow_writes: bool = False,
    builders: dict[str, Callable[[], Any]] | None = None,
    sdk_tool_names: dict[str, list[str]] | None = None,
    read_tools: list[str] | None = None,
    write_tools: list[str] | None = None,
    registry: dict[str, dict] | None = None,
    registry_path: str | Path | None = None,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Lös upp vilka MCP-servrar + verktyg ett pass ska få, utifrån rollens verktygslista.

    Args:
        role_tools: rollens ``## Tillåtna verktyg`` (logiska/connector-namn, kan vara tom).
        allow_writes: lägg till skrivverktyg (Write/Edit/Bash) i allowed.
        builders: {server_name: () -> McpServer} för in-process ``sdk``-servrar (cns/web).
            En builder som returnerar None betyder "ej tillgänglig" → servern hoppas över.
        sdk_tool_names: {server_name: [verktygsnamn]} — vilka verktygsnamn en sdk-server
            bidrar till allowed_tools (t.ex. cns: dess fyra mcp__cns__*-namn).
        registry / registry_path: registret (default läses från config/mcp_servers.json).

    Returns:
        (mcp_servers, allowed_tools, warnings) — redo att stoppas i ClaudeAgentOptions.
    """
    role_tools = list(role_tools or [])
    builders = builders or {}
    sdk_tool_names = sdk_tool_names or {}
    read_tools = list(read_tools if read_tools is not None else DEFAULT_READ_TOOLS)
    write_tools = list(write_tools if write_tools is not None else DEFAULT_WRITE_TOOLS)
    if registry is None:
        registry = load_registry(registry_path)

    mcp_servers: dict[str, Any] = {}
    allowed: list[str] = list(read_tools)
    warnings: list[str] = []

    for name, entry in registry.items():
        provides = entry.get("provides", [])
        always = bool(entry.get("always", False))
        needed = always or any(_matches(t, provides) for t in role_tools)
        if not needed:
            continue
        kind = entry.get("kind")
        if kind == "sdk":
            builder = builders.get(entry.get("builder", name))
            if builder is None:
                # Ingen builder injicerad (t.ex. web-extra saknas) — tyst skip om ej baseline.
                if not always:
                    warnings.append(f"MCP-server '{name}' saknar builder — hoppas över")
                continue
            try:
                srv = builder()
            except Exception as exc:  # noqa: BLE001 — degradera, stjälp aldrig passet
                warnings.append(f"MCP-server '{name}' kunde inte byggas ({exc}) — hoppas över")
                continue
            if srv is None:
                continue  # ej tillgänglig (t.ex. web utan beroende) — tyst, baseline
            mcp_servers[name] = srv
            allowed.extend(sdk_tool_names.get(name, []))
        else:  # extern: stdio/http
            cfg, warn = _build_external(name, entry)
            if cfg is None:
                warnings.append(warn or f"MCP-server '{name}' ej tillgänglig")
                continue
            mcp_servers[name] = cfg
            # Bara de av rollens verktyg som hör till denna server släpps på.
            allowed.extend(t for t in role_tools if _matches(t, provides))

    if allow_writes:
        allowed.extend(write_tools)

    return mcp_servers, _dedupe(allowed), warnings
