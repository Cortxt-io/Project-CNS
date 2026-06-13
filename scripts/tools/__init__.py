"""Konsoliderade MCP-verktyg: delad taxonomi + transport-fria domänkärnor.

Detta paket är **enkällan** för agenturens verktyg, läst av båda universum:
- ``app/tools/*.py`` — FastMCP connector-wrappers (universum A, Railway/claude.ai)
- ``scripts/tui/agent_host.py`` — SDK-wrappers (universum B, agenturens lokala pass)
- ``app/tools/_aliases.py`` — bakåtkompat-shim för de gamla granulära ``cortxt_*``-namnen
- ``scripts/tool_families.py`` + ``scripts/agent_roles.py`` — C1-härledning (matris → verktyg)
- ``scripts/mcp_router.py`` — ``allowed_tools`` per pass

Lagret bor i ``scripts/`` (foundation-lagret där datalagret redan bor) så att både
servern (``app/``) och de lokala passen importerar **nedåt** — ingen ``scripts→app``-koppling
för kärnlogiken. ``registry`` håller ren taxonomi (inga FastMCP/SDK-importer); handlers i
``<domän>_core`` wrappar ``scripts/``-datalagret och kastar ``ValueError`` (transport-fritt).
Se ``decisions/mcp-router.md`` och ``plans/agentur-verktygsatkomst-spec.md``.
"""
