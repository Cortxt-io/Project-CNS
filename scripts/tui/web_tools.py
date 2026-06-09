"""Web-verktyg: exponerar webbnavigering via Browser Use som in-process MCP-verktyg.

Isolerat: lazy import av browser_use (degraderar tydligt om paketet saknas),
rör inte agent_host.py:s CNS-verktyg. Read-first: inga formulärsubmit/
inloggningar/betalningar — bara läsning och navigering.

Aktiveras automatiskt av agent_host.py om browser_use är installerat.
Utan paketet degraderar verktygen och returnerar ett tydligt felmeddelande.
"""

from __future__ import annotations

import json
from typing import Any

# Servernamn — speglar CNS_SERVER_NAME-mönstret i agent_host.py.
WEB_SERVER_NAME = "web"

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

    Returnerar (False, förklaring) om browser_use saknas; kraschar aldrig.
    """
    try:
        import browser_use  # noqa: F401
        return (True, "ok (browser-use tillgängligt)")
    except Exception:
        return (False, "browser-use saknas (pip install -r requirements-agent.txt)")


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
            from browser_use import Agent, Browser, BrowserConfig
            from langchain_anthropic import ChatAnthropic

            browser = Browser(config=BrowserConfig(headless=True))
            llm = ChatAnthropic(model="claude-haiku-4-5", max_tokens=1024)
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
            text = str(result) if result else "(tomt svar från webbläsaren)"
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
            from browser_use import Agent, Browser, BrowserConfig
            from langchain_anthropic import ChatAnthropic

            # Förhindra skrivoperationer — lägg en läs-first-barrier i instruktionen.
            safe_instruction = (
                f"{instruction}\n\n"
                "VIKTIGT: Gör INGA inloggningar, fyll INTE i formulär och genomför "
                "INGA betalningar. Returnera bara vad du läst."
            )
            browser = Browser(config=BrowserConfig(headless=True))
            llm = ChatAnthropic(model="claude-haiku-4-5", max_tokens=1024)
            agent = Agent(task=safe_instruction, llm=llm, browser=browser)
            result = await agent.run(max_steps=15)
            text = str(result) if result else "(tomt svar från webbläsaren)"
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
