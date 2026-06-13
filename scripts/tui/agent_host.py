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
# CNS:s in-process MCP-verktyg = de feta verktygen ur den delade taxonomin (universum B).
# Namnges mcp__<server>__<domän>; servernamnet speglar registry.TOOL_NAMESPACE.
from scripts.tools import registry as _registry  # noqa: E402

CNS_SERVER_NAME = _registry.TOOL_NAMESPACE
CNS_TOOL_NAMES = [t.local_name for t in _registry.FAT_TOOLS]
# Baseline (läs-kärna) varje pass får oavsett roll — orienteringsytan: katalog, issues,
# idéer (motsvarar de gamla 4 läsverktygen: list_nodes/get_node/list_ideas/list_open_issues).
# Övriga domäner (quest/pr/session/wiki/…) monteras per roll via routerns sdk_role_resolver.
BASELINE_CNS_TOOLS = [_registry.by_domain(d).local_name for d in ("project", "issue", "idea")]
# {lokalt verktygsnamn -> set(läs-actions)} — read-first-grinden inspekterar action,
# eftersom ett fett verktyg blandar läsning och skrivning per action (namnet räcker ej).
_READ_ACTIONS_BY_TOOL = {t.local_name: set(t.read_actions()) for t in _registry.FAT_TOOLS}


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


def _fat_tool_schema(spec: Any) -> dict:
    """JSON-schema för ett fett SDK-verktyg: action (enum) + fria params (per action)."""
    return {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": list(spec.action_names),
                "description": "Vilken operation; se verktygsbeskrivningen för params per action.",
            }
        },
        "required": ["action"],
        "additionalProperties": True,
    }


def _make_fat_tool(spec: Any) -> Any:
    """Bygg ETT fett SDK-@tool för en domän som dispatchar mot den delade kärnan.

    Universum B (lokala pass): samma domänkärna som connectorn (universum A). Idé-/
    sessions-skrivningar pushas best-effort (samma split som connectorn); leases får
    owner='local' (ingen OAuth lokalt). Read-first-grinden (``_deny_unlisted``) hindrar
    skriv-actions i läsläge — här körs bara det passet redan fått släppt på.
    """
    from claude_agent_sdk import tool

    domain = spec.domain

    @tool(domain, spec.summary, _fat_tool_schema(spec))
    async def _fat(args: dict) -> dict:
        action = args.get("action")
        kwargs = {k: v for k, v in args.items() if k != "action"}
        try:
            if domain == "lease":
                kwargs.setdefault("owner", "local")
            result = _registry.dispatch(domain, action, **kwargs)
        except ValueError as exc:
            return _text({"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 — degradera, stjälp aldrig passet
            return _text({"error": f"{type(exc).__name__}: {exc}"})
        # Push av idé-/sessionsfil (best-effort), samma split som connector-wrappern.
        try:
            _maybe_push(domain, action, result)
        except Exception:
            pass
        return _text(result)

    return _fat


def _maybe_push(domain: str, action: str, result: Any) -> None:
    """Best-effort GitHub-push av idé-/sessionsskrivningar från ett lokalt pass."""
    if domain == "idea" and action in ("capture", "resolve") and isinstance(result, dict):
        from scripts.idea_inbox import IDEAS_DIR
        from app.git_ops import push_file_immediately

        push_file_immediately(IDEAS_DIR / f"{result['id']}.json", f"cns-vault: {action} idea {result['id']}")
    elif domain == "idea" and action == "promote" and isinstance(result, dict):
        from scripts.idea_inbox import IDEAS_DIR
        from app.git_ops import push_file_immediately

        iid = result["idea"]["id"]
        push_file_immediately(IDEAS_DIR / f"{iid}.json", f"cns-vault: promote idea {iid}")
    elif domain == "session" and action in ("start", "done", "save", "fork") and isinstance(result, dict):
        from scripts.session_store import SESSIONS_DIR
        from app.git_ops import push_file_immediately

        push_file_immediately(SESSIONS_DIR / f"{result['id']}.json", f"cns-vault: {action} {result['id']}")


def _build_cns_tools() -> list[Any]:
    """Bygg de feta SDK-verktygen ur den delade taxonomin. Lazy (SDK krävs ej för import)."""
    return [_make_fat_tool(spec) for spec in _registry.FAT_TOOLS]


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

# Externa MCP-verktyg (github m.fl.) saknar action-fält, så läs/skriv härleds ur namnet.
# Läsverb släpps i read-läge; skrivverb nekas även när routern monterat verktyget (#137).
_EXTERNAL_READ_VERBS = ("read", "get", "list", "search", "view", "show", "fetch", "find", "describe")
_EXTERNAL_WRITE_VERBS = (
    "write", "create", "update", "delete", "add", "remove", "set",
    "close", "merge", "push", "edit", "comment", "rename", "move",
)


def _external_is_read_shaped(tool_name: str) -> bool:
    """Är ett externt MCP-verktyg läsformat? Skrivverb i namnet vinner (säkert default).

    T.ex. ``mcp__github__issue_read`` → läs; ``mcp__github__create_pull_request`` → skriv.
    Ambiguösa namn utan läsverb behandlas som icke-läs (nekas i read-läge).
    """
    leaf = tool_name.split("__")[-1].lower()
    if any(w in leaf for w in _EXTERNAL_WRITE_VERBS):
        return False
    return any(r in leaf for r in _EXTERNAL_READ_VERBS)


def _make_read_gate(external_read: frozenset[str] = frozenset()) -> Any:
    """Bygg en read-first-grind (can_use_tool) som känner routerns externa läsverktyg.

    Feta CNS-verktyg grindas på *action* (namnet blandar läs/skriv). Read/Glob/Grep + web
    tillåts. ``external_read`` = router-monterade externa MCP-läsverktyg passet fått (#137) —
    annars hade en monterad github-server nekats fast routern gett rollen åtkomst. Allt annat
    (Write/Edit/Bash, skrivformade externa verktyg, verkligt olistat) nekas.
    """
    async def _gate(tool_name: str, _input: dict, _ctx: Any) -> Any:
        from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

        if tool_name in _READ_ACTIONS_BY_TOOL:
            action = (_input or {}).get("action")
            if action in _READ_ACTIONS_BY_TOOL[tool_name]:
                return PermissionResultAllow()
            return PermissionResultDeny(
                message=f"'{tool_name}(action={action})' är en skriv-action — nekad i CNS read-läge."
            )
        allowed = set(READ_TOOLS + WEB_TOOL_NAMES)
        if tool_name in allowed or tool_name.startswith(f"mcp__{WEB_SERVER_NAME}__"):
            return PermissionResultAllow()
        if tool_name in external_read:
            return PermissionResultAllow()
        return PermissionResultDeny(message=f"'{tool_name}' nekat i CNS read-läge.")

    return _gate


# Bakåtkompatibel modulsymbol: grind utan externa läsverktyg (= strikt read-first).
_deny_unlisted = _make_read_gate()


def _external_read_tools(allowed: list[str]) -> frozenset[str]:
    """Plocka ut router-monterade EXTERNA läsverktyg ur passets allowed_tools (#137).

    Externt = ``mcp__*`` som varken är cns- eller web-servern. Bara läsformade släpps in
    i read-grinden; skrivformade externa verktyg lämnas utanför (nekas i read-läge).
    """
    cns_prefix = f"mcp__{CNS_SERVER_NAME}__"
    web_prefix = f"mcp__{WEB_SERVER_NAME}__"
    return frozenset(
        t for t in allowed
        if t.startswith("mcp__")
        and not t.startswith(cns_prefix)
        and not t.startswith(web_prefix)
        and _external_is_read_shaped(t)
    )


def build_options(
    slug: str | None = None,
    resume: str | None = None,
    allow_writes: bool = False,
    permission_check: Any = None,
    role: dict | None = None,
    cwd: str | None = None,
    warnings: list[str] | None = None,
    guard: Any = None,
) -> Any:
    """Bygg ClaudeAgentOptions för ett agent-pass (read-first som default).

    ``permission_check`` (om satt) ersätter den router-medvetna read-grinden helt som
    ``can_use_tool``. ``guard`` (#60): om satt wrappas read-grinden med guardrails
    (turn/token-tak + upprepat-anrop) — grinden förblir router-medveten (#137).
    ``role`` (roll-medveten exekvering, #90): sätter rollens systemprompt + modell
    (den routade agentens modellnivå) — så passet körs SOM agenten, inte generiskt.
    ``cwd`` (worktree-isolering, #59): kör passet i en annan arbetskatalog än repo-roten
    — så ett SKRIVANDE dispatch-pass jobbar i en isolerad git-worktree i stället för main.
    ``warnings`` (out-param): router-varningar (saknad/ej konfigurerad MCP-server) läggs
    här så run_turn kan yielda dem.

    **MCP-router (config-router):** vilka MCP-servrar + verktyg passet får avgörs av
    ``mcp_router.resolve`` utifrån rollens ``## Tillåtna verktyg`` — inte längre hårdkodat
    till bara CNS. In-process-servrarna (cns/web) byggs här och injiceras som builders;
    externa servrar (GitHub-MCP m.fl.) monteras per roll ur ``config/mcp_servers.json``.
    Se ``decisions/mcp-router.md``.
    """
    from claude_agent_sdk import ClaudeAgentOptions

    from scripts import mcp_router

    role_tools = (role or {}).get("tools", []) if role else []
    def _sdk_role_resolver(tools: list[str], server: str) -> list[str]:
        # Bara cns-servern översätter rollens tokens till lokala feta namn; web har egna.
        return _registry.local_names_for(tools) if server == CNS_SERVER_NAME else []

    mcp_servers, allowed, router_warnings = mcp_router.resolve(
        role_tools,
        allow_writes=allow_writes,
        builders={CNS_SERVER_NAME: build_cns_server, WEB_SERVER_NAME: build_web_server},
        sdk_tool_names={CNS_SERVER_NAME: list(BASELINE_CNS_TOOLS),
                        WEB_SERVER_NAME: list(WEB_TOOL_NAMES)},
        sdk_role_resolver=_sdk_role_resolver,
        read_tools=list(READ_TOOLS),
        write_tools=list(WRITE_TOOLS),
    )
    if warnings is not None:
        warnings.extend(router_warnings)
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
        # Router-medveten read-grind: släpp externa läsverktyg routern monterat (#137).
        base_gate = permission_check or _make_read_gate(_external_read_tools(allowed))
        if guard is not None and permission_check is None:
            from claude_agent_sdk import PermissionResultDeny

            async def _gated(tool_name: str, tool_input: dict, ctx: Any, _base=base_gate, _g=guard) -> Any:
                ok_call, reason = _g.check(tool_name, tool_input)
                if not ok_call:
                    return PermissionResultDeny(message=f"guardrail: {reason}")
                return await _base(tool_name, tool_input, ctx)

            kwargs["can_use_tool"] = _gated
        else:
            kwargs["can_use_tool"] = base_gate
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
        ResultMessage,
        SystemMessage,
        TextBlock,
        ToolUseBlock,
    )

    # Read-grinden byggs router-medvetet i build_options; guardrails (turn/token-tak +
    # upprepat-anrop, #60) komponeras ovanpå där så den externa-läsverktygs-listan (#137)
    # bevaras.
    router_warnings: list[str] = []
    options = build_options(
        slug=slug, resume=resume, allow_writes=allow_writes,
        role=role, cwd=cwd, warnings=router_warnings,
        guard=guard if not allow_writes else None,
    )
    for _w in router_warnings:
        yield ("warning", _w)
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
