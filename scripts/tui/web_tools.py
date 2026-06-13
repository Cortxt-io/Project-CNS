"""Web-verktyg: exponerar webbnavigering via Browser Use som in-process MCP-verktyg.

Isolerat: lazy import av browser_use (degraderar tydligt om paketet saknas),
rör inte agent_host.py:s CNS-verktyg. Read-first: inga formulärsubmit/
inloggningar/betalningar — bara läsning och navigering.

Aktiveras automatiskt av agent_host.py om browser_use är installerat.
Utan paketet degraderar verktygen och returnerar ett tydligt felmeddelande.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Servernamn — speglar CNS_SERVER_NAME-mönstret i agent_host.py.
WEB_SERVER_NAME = "web"

# Webbläsar-agentens LLM väljs efter tillgänglig nyckel (billig modell räcker —
# den driver bara browser-use:s navigering/extraktion, inte huvudpasset).
# Prioritet: Anthropic (om saldo) → Gemini (gratis-tier) → Groq (gratis-tier).
# Nyckel läses från env ELLER en otrackad nyckelfil i repo-roten (aldrig i kod/chatt).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_LLM_PROVIDERS = (
    # (provider, modell, env-var(s), nyckelfil, genai-env-var att spegla nyckeln till)
    ("anthropic", "claude-haiku-4-5", ("ANTHROPIC_API_KEY",), ".cns-agent-key", "ANTHROPIC_API_KEY"),
    ("google", "gemini-2.0-flash", ("GEMINI_API_KEY", "GOOGLE_API_KEY"), ".cns-gemini-key", "GOOGLE_API_KEY"),
    ("groq", "meta-llama/llama-4-scout-17b-16e-instruct", ("GROQ_API_KEY",), ".cns-groq-key", "GROQ_API_KEY"),
)


def _resolve_key(env_vars: tuple[str, ...], key_file: str) -> str | None:
    """Hämta API-nyckel ur env eller otrackad nyckelfil — returnerar None om saknas."""
    for var in env_vars:
        val = os.environ.get(var)
        if val and val.strip():
            return val.strip()
    fp = _REPO_ROOT / key_file
    try:
        if fp.is_file():
            content = fp.read_text(encoding="utf-8").strip()
            if content:
                return content
    except OSError:
        pass
    return None


def _select_provider() -> tuple[str, str, str] | None:
    """(provider, modell, nyckel) för första provider med tillgänglig nyckel; annars None."""
    for provider, model, env_vars, key_file, genai_env in _LLM_PROVIDERS:
        key = _resolve_key(env_vars, key_file)
        if key:
            # Spegla nyckeln till den env-var providerns SDK-klient läser.
            os.environ.setdefault(genai_env, key)
            return (provider, model, key)
    return None


def _build_llm() -> Any:
    """Bygg browser-use LLM-wrappern för vald provider. Kastar RuntimeError om ingen nyckel."""
    sel = _select_provider()
    if sel is None:
        raise RuntimeError(
            "ingen LLM-nyckel hittad — sätt ANTHROPIC_API_KEY (eller GEMINI_API_KEY/GROQ_API_KEY) "
            "i env eller i en otrackad nyckelfil (.cns-agent-key / .cns-gemini-key / .cns-groq-key)."
        )
    provider, model, key = sel
    if provider == "anthropic":
        from browser_use import ChatAnthropic
        return ChatAnthropic(model=model, max_tokens=1024, api_key=key)
    if provider == "google":
        from browser_use import ChatGoogle
        return ChatGoogle(model=model)
    from browser_use import ChatGroq
    return ChatGroq(model=model, api_key=key)


# Tillåtna MCP-verktygsnamn (används i agent_host.py:s allowlist + _deny_unlisted).
WEB_TOOL_NAMES = [
    f"mcp__{WEB_SERVER_NAME}__web_extract",
    f"mcp__{WEB_SERVER_NAME}__web_act",
]


def _text(payload: Any) -> dict[str, Any]:
    """MCP-content-svar med JSON-text — identisk med agent_host.py:s hjälpare."""
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]}


def availability() -> tuple[bool, str]:
    """(ok, meddelande) — om webb-verktygen kan köras här.

    Returnerar (False, förklaring) om browser_use saknas eller ingen LLM-nyckel finns;
    kraschar aldrig.
    """
    try:
        import browser_use  # noqa: F401
    except Exception:
        return (False, "browser-use saknas (pip install -r requirements-agent.txt)")
    sel = _select_provider()
    if sel is None:
        return (False, "browser-use ok men ingen LLM-nyckel (ANTHROPIC_API_KEY/GEMINI_API_KEY/GROQ_API_KEY)")
    provider, model, _ = sel
    return (True, f"ok (browser-use + {provider}:{model})")


def _build_web_tools() -> list[Any]:
    """Definiera @tool-wrappers. Importeras lazy — kräver inte browser_use på modulnivå."""
    from claude_agent_sdk import tool

    @tool(
        "web_extract",
        (
            "Öppna en URL med en riktig webbläsare och extrahera innehåll relevant för "
            "en fråga. Lämplig för JS-renderade sidor där WebFetch ger tomt svar. "
            "Read-first: inga inloggningar, formulär eller betalningar."
        ),
        {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL att öppna."},
                "query": {
                    "type": "string",
                    "description": "Vad du letar efter på sidan (fokuserar extraheringen).",
                },
            },
            "required": ["url", "query"],
        },
    )
    async def web_extract(args: dict) -> dict:
        url: str = args.get("url", "")
        query: str = args.get("query", "")
        try:
            from browser_use import Agent, Browser

            browser = Browser(headless=True)
            llm = _build_llm()
            agent = Agent(
                task=(
                    f"Navigera till {url}. "
                    f"Extrahera och returnera allt textinnehåll som är relevant för: {query}. "
                    "Gör INGET annat — inga klick, inga formulär, inga inloggningar."
                ),
                llm=llm,
                browser=browser,
            )
            result = await agent.run(max_steps=10)
            text = (result.final_result() if result else None) or "(tomt svar från webbläsaren)"
            await browser.close()
            return _text({"url": url, "query": query, "content": text})
        except ImportError as exc:
            return _text({"error": f"browser-use eller beroende saknas: {exc}. Installera requirements-agent.txt."})
        except Exception as exc:
            return _text({"error": f"web_extract misslyckades: {type(exc).__name__}: {exc}"})

    @tool(
        "web_act",
        (
            "Kör en Browser Use-agent på en fritextinstruktion: navigera, klicka, läs "
            "och returnera resultatet. Sätt en rimlig scope — undvik öppna loopar. "
            "Read-first: inga inloggningar, formulärsubmit eller betalningar."
        ),
        {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": "Fritextinstruktion för webbläsaragenten (navigera/klicka/läs).",
                },
            },
            "required": ["instruction"],
        },
    )
    async def web_act(args: dict) -> dict:
        instruction: str = args.get("instruction", "")
        try:
            from browser_use import Agent, Browser

            # Förhindra skrivoperationer — lägg en läs-first-barrier i instruktionen.
            safe_instruction = (
                f"{instruction}\n\n"
                "VIKTIGT: Gör INGA inloggningar, fyll INTE i formulär och genomför "
                "INGA betalningar. Returnera bara vad du läst."
            )
            browser = Browser(headless=True)
            llm = _build_llm()
            agent = Agent(task=safe_instruction, llm=llm, browser=browser)
            result = await agent.run(max_steps=15)
            text = (result.final_result() if result else None) or "(tomt svar från webbläsaren)"
            await browser.close()
            return _text({"instruction": instruction, "result": text})
        except ImportError as exc:
            return _text({"error": f"browser-use eller beroende saknas: {exc}. Installera requirements-agent.txt."})
        except Exception as exc:
            return _text({"error": f"web_act misslyckades: {type(exc).__name__}: {exc}"})

    return [web_extract, web_act]


def build_web_server() -> Any:
    """Bygg in-process MCP-server för webb-verktygen."""
    from claude_agent_sdk import create_sdk_mcp_server

    return create_sdk_mcp_server(name=WEB_SERVER_NAME, tools=_build_web_tools())
