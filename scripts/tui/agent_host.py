"""Agent-host: driver Claude lokalt via Claude Agent SDK och exponerar CNS:s
datalager som in-process MCP-verktyg. Renderingen sköts av AgentScreen i app.py.

Isolerat: lazy import av claude_agent_sdk (degraderar tydligt om paketet/CLI
saknas), rör inte app/mcp_server.py. Read-first: bara läsverktyg är förhands-
godkända; skrivverktyg (Write/Edit/Bash) nekas av can_use_tool om de inte
explicit släpps på.

Auth: provar i ordning (1) ANTHROPIC_API_KEY i miljön, (2) en otrackad lokal
fil `.cns-agent-key` i repo-roten (en rad = nyckeln; auto-läses hit), (3) din
befintliga Claude Code-login som CLI:t redan har. Nyckeln är alltså valfri för
personligt lokalt bruk; en egen nyckel (separat fakturering) läggs i filen en
gång och behöver aldrig exporteras manuellt.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, AsyncIterator

REPO_ROOT = Path(__file__).resolve().parents[2]

# Webb-verktyg (valfritt extra — importeras lazy så browser_use ej krävs).
# web_tools importerar INTE browser_use på modulnivå; det sker inne i varje wrapper.
try:
    from scripts.tui.web_tools import WEB_SERVER_NAME, WEB_TOOL_NAMES, build_web_server

    _WEB_AVAILABLE = True
except Exception:
    _WEB_AVAILABLE = False
    WEB_SERVER_NAME = "web"  # fallback för _deny_unlisted
    WEB_TOOL_NAMES: list[str] = []

    def build_web_server() -> Any:  # type: ignore[misc]
        return None
# Otrackad lokal nyckelfil (gitignored) — auto-läses till miljön om satt.
LOCAL_KEY_FILE = REPO_ROOT / ".cns-agent-key"

# Claude Codes egna läsverktyg som agenten får använda direkt.
READ_TOOLS = ["Read", "Glob", "Grep"]
WRITE_TOOLS = ["Write", "Edit", "Bash"]
# CNS:s in-process MCP-verktyg (namnges mcp__<server>__<tool>).
CNS_SERVER_NAME = "cns"
CNS_TOOL_NAMES = [
    f"mcp__{CNS_SERVER_NAME}__list_nodes",
    f"mcp__{CNS_SERVER_NAME}__get_node",
    f"mcp__{CNS_SERVER_NAME}__list_ideas",
    f"mcp__{CNS_SERVER_NAME}__list_open_issues",
]


class AgentHostUnavailable(RuntimeError):
    """claude_agent_sdk saknas eller Claude Code CLI saknas på PATH."""


def _ensure_key_loaded() -> None:
    """Läs in .cns-agent-key till miljön om ANTHROPIC_API_KEY inte redan är satt."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    try:
        if LOCAL_KEY_FILE.exists():
            key = LOCAL_KEY_FILE.read_text(encoding="utf-8").strip().splitlines()
            if key and key[0].strip():
                os.environ["ANTHROPIC_API_KEY"] = key[0].strip()
    except Exception:
        pass


def availability() -> tuple[bool, str]:
    """(ok, meddelande) — om agent-host kan köras här.

    Nyckeln är INTE ett hårt krav: saknas den provar SDK:n din befintliga
    Claude Code-login. ok kräver bara att SDK + CLI finns.
    """
    try:
        import claude_agent_sdk  # noqa: F401
    except Exception:
        return (False, "claude-agent-sdk saknas (pip install -r requirements-agent.txt)")
    import shutil

    if not shutil.which("claude"):
        return (False, "Claude Code CLI saknas på PATH")
    _ensure_key_loaded()
    if os.environ.get("ANTHROPIC_API_KEY"):
        return (True, "ok (API-nyckel)")
    return (True, "ok (provar Claude-login; lägg ev. nyckel i .cns-agent-key)")


# -- CNS-verktyg (read-first, wrappar det stabila datalagret) ---------------

def _text(payload: Any) -> dict[str, Any]:
    """MCP-content-svar med JSON-text."""
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]}


def _build_cns_tools() -> list[Any]:
    """Definiera @tool-wrappers. Importeras lazy så modulen kan laddas utan SDK."""
    from claude_agent_sdk import tool

    @tool(
        "list_nodes",
        "Lista alla CNS-noder (slug, title, kind, stage, status, part_of).",
        {"type": "object", "properties": {}},
    )
    async def list_nodes(_args: dict) -> dict:
        from scripts.md_parser import read_all_nodes

        rows = []
        for meta, _sections in read_all_nodes():
            rows.append(
                {
                    "slug": meta.get("slug"),
                    "title": meta.get("title"),
                    "kind": meta.get("kind"),
                    "stage": meta.get("stage"),
                    "status": meta.get("status"),
                    "part_of": meta.get("part_of"),
                }
            )
        return _text(rows)

    @tool(
        "get_node",
        "Hämta en CNS-nods frontmatter + sektioner.",
        {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]},
    )
    async def get_node(args: dict) -> dict:
        from scripts.md_parser import read_node

        try:
            meta, sections, _raw = read_node(args["slug"])
        except Exception as exc:
            return _text({"error": str(exc)})
        return _text({"meta": meta, "sections": sections})

    @tool(
        "list_ideas",
        "Lista öppna idéer i CNS-inkorgen, valfritt filtrerat på nod-slug.",
        {"type": "object", "properties": {"slug": {"type": "string"}}},
    )
    async def list_ideas(args: dict) -> dict:
        from scripts.idea_inbox import list_ideas as _li

        return _text(_li(status="open", slug=args.get("slug")))

    @tool(
        "list_open_issues",
        "Lista öppna GitHub-issues för en nod (grindat; degraderar om ej konfigurerat).",
        {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]},
    )
    async def list_open_issues(args: dict) -> dict:
        from scripts.tui.sources import open_issues_for_slug

        status, issues = open_issues_for_slug(args["slug"])
        return _text({"status": status, "issues": issues})

    return [list_nodes, get_node, list_ideas, list_open_issues]


def build_cns_server() -> Any:
    from claude_agent_sdk import create_sdk_mcp_server

    return create_sdk_mcp_server(name=CNS_SERVER_NAME, tools=_build_cns_tools())


# -- kontext-seed -----------------------------------------------------------

def build_seed(slug: str | None, role: dict | None = None) -> str:
    """Systemprompt: ramar in agenten kring en markerad nod (read-first).

    ``role`` (roll-medveten exekvering, #90): om satt körs passet SOM den routade
    agenten — dess egen systemprompt (identitet/uppgift/gräns) blir basen i stället
    för den generiska CNS-agenten. None → generiskt beteende (bakåtkompatibelt).
    """
    read_mode = "Du är i LÄS-LÄGE: föreslå ändringar i text, skriv/kör inte själv."
    if role and role.get("system_prompt"):
        base = (
            role["system_prompt"].strip()
            + "\n\n---\nDu arbetar inbäddad i CNS (terminal-UI för en produktportfölj); "
            "CNS äger strukturen (noder/relationer), GitHub äger uppgifter. "
            "Använd mcp__cns__*-verktygen för portföljdata och Read/Glob/Grep för kod. "
            + read_mode
        )
    else:
        base = (
            "Du är CNS-agenten, inbäddad i ett terminal-UI för en produktportfölj. "
            "CNS äger strukturen (noder/relationer); GitHub äger uppgifter. "
            "Använd mcp__cns__*-verktygen för portföljdata och Read/Glob/Grep för kod. "
            + read_mode
        )
    if not slug:
        return base
    try:
        from scripts.md_parser import read_node

        meta, _sections, _raw = read_node(slug)
        ctx = {
            k: meta.get(k)
            for k in ("slug", "title", "kind", "stage", "status", "summary")
        }
        return base + f"\n\nArbetsnod (kontext):\n{json.dumps(ctx, ensure_ascii=False)}"
    except Exception:
        return base + f"\n\nArbetsnod: {slug}"


# -- options + körning ------------------------------------------------------

async def _deny_unlisted(tool_name: str, _input: dict, _ctx: Any) -> Any:
    """can_use_tool: neka allt som inte är förhandsgodkänt (read-first-skydd)."""
    from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

    allowed = set(READ_TOOLS + CNS_TOOL_NAMES + WEB_TOOL_NAMES)
    if (
        tool_name in allowed
        or tool_name.startswith(f"mcp__{CNS_SERVER_NAME}__")
        or tool_name.startswith(f"mcp__{WEB_SERVER_NAME}__")
    ):
        return PermissionResultAllow()
    return PermissionResultDeny(message=f"'{tool_name}' nekat i CNS read-läge.")


def build_options(
    slug: str | None = None,
    resume: str | None = None,
    allow_writes: bool = False,
    permission_check: Any = None,
    role: dict | None = None,
    cwd: str | None = None,
) -> Any:
    """Bygg ClaudeAgentOptions för ett agent-pass (read-first som default).

    ``permission_check`` (om satt) ersätter ``_deny_unlisted`` som ``can_use_tool``
    — så run_turn kan wrappa read-first-kollen med guardrails (#60).
    ``role`` (roll-medveten exekvering, #90): sätter rollens systemprompt + modell
    (den routade agentens modellnivå) — så passet körs SOM agenten, inte generiskt.
    ``cwd`` (worktree-isolering, #59): kör passet i en annan arbetskatalog än repo-roten
    — så ett SKRIVANDE dispatch-pass jobbar i en isolerad git-worktree i stället för main.
    """
    from claude_agent_sdk import ClaudeAgentOptions

    allowed = list(READ_TOOLS) + list(CNS_TOOL_NAMES) + list(WEB_TOOL_NAMES)
    if allow_writes:
        allowed += WRITE_TOOLS
    mcp_servers: dict[str, Any] = {CNS_SERVER_NAME: build_cns_server()}
    if _WEB_AVAILABLE:
        web_srv = build_web_server()
        if web_srv is not None:
            mcp_servers[WEB_SERVER_NAME] = web_srv
    kwargs: dict[str, Any] = {
        "system_prompt": build_seed(slug, role=role),
        "mcp_servers": mcp_servers,
        "allowed_tools": allowed,
        "permission_mode": "default",
        "cwd": cwd or str(REPO_ROOT),
    }
    if role and role.get("model"):
        kwargs["model"] = role["model"]
    if not allow_writes:
        kwargs["can_use_tool"] = permission_check or _deny_unlisted
    if resume:
        kwargs["resume"] = resume
    return ClaudeAgentOptions(**kwargs)


async def run_turn(
    prompt: str,
    slug: str | None = None,
    resume: str | None = None,
    allow_writes: bool = False,
    agent_slug: str | None = None,
    cwd: str | None = None,
) -> AsyncIterator[tuple[str, Any]]:
    """Kör ett agent-pass och yielda render-händelser för AgentScreen.

    Händelser: ('session', id) · ('role', dict) · ('text', str) · ('tool', name) ·
    ('result', text) · ('warning', msg) · ('metrics', dict) · ('error', msg).

    Roll-medveten exekvering (#90): ``agent_slug`` kör som en namngiven agent; annars
    härleds rollen ur den markerade noden via ``route()`` (role_for_node). Misslyckas
    rollresolutionen körs passet generiskt (bakåtkompatibelt).
    """
    ok, msg = availability()
    if not ok:
        yield ("error", msg)
        return

    # Roll-medveten exekvering: kör SOM den routade/namngivna agenten om möjligt.
    role = None
    try:
        from scripts.agent_roles import load_role, role_for_node

        role = load_role(agent_slug) if agent_slug else role_for_node(slug)
    except Exception:
        role = None
    if role:
        yield (
            "role",
            {
                "slug": role.get("slug"),
                "title": role.get("title"),
                "model": role.get("model"),
                "routed": role.get("routed"),
            },
        )

    # cns-sync-guardrail (#60): varna om ett annat pass redan jobbar på samma nod.
    guard = None
    try:
        from scripts.agent_guardrails import Guardrails, check_session_overlap

        clear, conflicting = check_session_overlap(slug)
        if not clear:
            yield ("warning", f"{len(conflicting)} pass jobbar redan på '{slug}' — risk för dubbelarbete (cns-sync)")
        guard = Guardrails()
    except Exception:
        guard = None  # guardrails är valfria — degradera tyst

    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeSDKClient,
        PermissionResultDeny,
        ResultMessage,
        SystemMessage,
        TextBlock,
        ToolUseBlock,
    )

    # Wrappa read-first-kollen med guardrails (turn/token-tak + upprepat-anrop, #60).
    permission_check = None
    if guard is not None and not allow_writes:
        async def permission_check(tool_name: str, tool_input: dict, ctx: Any) -> Any:
            allow, reason = guard.check(tool_name, tool_input)
            if not allow:
                return PermissionResultDeny(message=f"guardrail: {reason}")
            return await _deny_unlisted(tool_name, tool_input, ctx)

    options = build_options(
        slug=slug, resume=resume, allow_writes=allow_writes,
        permission_check=permission_check, role=role, cwd=cwd,
    )
    # ClaudeSDKClient kör i streaming-läge → can_use_tool fungerar med strängprompt.
    client = ClaudeSDKClient(options=options)
    try:
        await client.connect()
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, SystemMessage):
                sid = (getattr(message, "data", {}) or {}).get("session_id")
                if sid:
                    yield ("session", sid)
            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        yield ("text", block.text)
                    elif isinstance(block, ToolUseBlock):
                        yield ("tool", block.name)
            elif isinstance(message, ResultMessage):
                # Observabilitet (#58): mata guardrails token-räkningen ur usage,
                # yielda en metrics-snapshot (AgentScreen/_record_session kan skriva
                # den till session_store.record_metrics).
                if guard is not None:
                    try:
                        usage = getattr(message, "usage", None) or {}
                        guard.tokens += int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
                    except Exception:
                        pass
                    yield ("metrics", guard.snapshot())
                yield ("result", getattr(message, "result", "") or "")
    except Exception as exc:
        yield ("error", f"{type(exc).__name__}: {exc}")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
