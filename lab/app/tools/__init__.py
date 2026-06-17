"""MCP tool modules for the Cortxt server.

Each module exposes a ``register(mcp)`` that attaches its ``cortxt_*`` tools to
the shared FastMCP instance created in ``app/mcp_server.py``. Tools call the pure
data layer in ``scripts/`` and push via ``app/git_ops.py`` — the same
storage/push split used across CNS. Tool names are part of the public connector
contract (claude.ai), so they must stay stable when moved between modules.

Modules: issues, quests (milestones), ideas, projects, sessions.
"""
