"""Agent-host: driver Claude lokalt via Claude Agent SDK och exponerar CNS:s
datalager som in-process MCP-verktyg. Renderingen sköts av AgentScreen i app.py.

Isolerat: lazy import av claude_agent_sdk (degraderar tydligt om paketet/CLI
saknas), rör inte app/mcp_server.py. Read-first: bara läsverktyg är förhands-
godkända; skrivverktyg (Write/Edit/Bash) nekas av can_use_tool om de inte
explicit släpps på.

Auth: kräver ANTHROPIC_API_KEY (Agent SDK får ej använda prenumerationslogin).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncIterator

REPO_ROOT = Path(__file__).resolve().parents[2]

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
    """claude_agent_sdk saknas, CLI saknas, eller ANTHROPIC_API_KEY ej satt."""


def availability() -> tuple[bool, str]:
    """(ok, meddelande) — om agent-host kan köras här."""
    try:
        import claude_agent_sdk  # noqa: F401
    except Exception:
        return (False, "claude-agent-sdk saknas (pip install -r requirements-agent.txt)")
    import os
    import shutil

    if not shutil.which("claude"):
        return (False, "Claude Code CLI saknas på PATH")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return (False, "ANTHROPIC_API_KEY ej satt (Agent SDK kräver API-nyckel)")
    return (True, "ok")


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

def build_seed(slug: str | None) -> str:
    """Systemprompt: ramar in agenten kring en markerad nod (read-first)."""
    base = (
        "Du är CNS-agenten, inbäddad i ett terminal-UI för en produktportfölj. "
        "CNS äger strukturen (noder/relationer); GitHub äger uppgifter. "
        "Använd mcp__cns__*-verktygen för portföljdata och Read/Glob/Grep för kod. "
        "Du är i LÄS-LÄGE: föreslå ändringar i text, skriv/kör inte själv."
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

    allowed = set(READ_TOOLS + CNS_TOOL_NAMES)
    if tool_name in allowed or tool_name.startswith(f"mcp__{CNS_SERVER_NAME}__"):
        return PermissionResultAllow()
    return PermissionResultDeny(message=f"'{tool_name}' nekat i CNS read-läge.")


def build_options(slug: str | None = None, resume: str | None = None, allow_writes: bool = False) -> Any:
    """Bygg ClaudeAgentOptions för ett agent-pass (read-first som default)."""
    from claude_agent_sdk import ClaudeAgentOptions

    allowed = list(READ_TOOLS) + list(CNS_TOOL_NAMES)
    if allow_writes:
        allowed += WRITE_TOOLS
    kwargs: dict[str, Any] = {
        "system_prompt": build_seed(slug),
        "mcp_servers": {CNS_SERVER_NAME: build_cns_server()},
        "allowed_tools": allowed,
        "permission_mode": "default",
        "cwd": str(REPO_ROOT),
    }
    if not allow_writes:
        kwargs["can_use_tool"] = _deny_unlisted
    if resume:
        kwargs["resume"] = resume
    return ClaudeAgentOptions(**kwargs)


async def run_turn(
    prompt: str,
    slug: str | None = None,
    resume: str | None = None,
    allow_writes: bool = False,
) -> AsyncIterator[tuple[str, Any]]:
    """Kör ett agent-pass och yielda render-händelser för AgentScreen.

    Händelser: ('session', id) · ('text', str) · ('tool', name) · ('result', text) · ('error', msg).
    """
    ok, msg = availability()
    if not ok:
        yield ("error", msg)
        return
    from claude_agent_sdk import (
        AssistantMessage,
        ResultMessage,
        SystemMessage,
        TextBlock,
        ToolUseBlock,
        query,
    )

    options = build_options(slug=slug, resume=resume, allow_writes=allow_writes)
    try:
        async for message in query(prompt=prompt, options=options):
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
                yield ("result", getattr(message, "result", "") or "")
    except Exception as exc:
        yield ("error", f"{type(exc).__name__}: {exc}")
