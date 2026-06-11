"""Guardrails för agent-host-loopen (issue #60): hindra runaway/loop.

Ren, testbar logik som ``agent_host.can_use_tool`` anropar för att NEKA fler anrop när:
- samma verktygsanrop upprepas för många gånger (vår 580k-token-incident),
- turn-taket nås,
- token-budgeten är slut.

Tvingar inget på egen hand — ``check()`` returnerar ``(allow, reason)``; anroparen nekar.
Plan A-tooling (agent-host); produktkod (``app/``) rör det ej. Trösklarna är
konservativa defaults — höj/sänk per pass eller agentroll.
"""
from __future__ import annotations

import json

DEFAULT_MAX_TURNS = 50
DEFAULT_TOKEN_BUDGET = 200_000
DEFAULT_MAX_REPEATS = 3


def _call_key(tool_name: str, args) -> tuple[str, str]:
    """Stabil nyckel för (verktyg, args) så identiska anrop kan räknas."""
    try:
        return (tool_name, json.dumps(args, sort_keys=True, default=str) if args else "")
    except Exception:
        return (tool_name, str(args))


class Guardrails:
    """Per-pass-räknare. ``agent_host`` matar in varje verktygsanrop (+ ev. tokens)."""

    def __init__(
        self,
        *,
        max_turns: int = DEFAULT_MAX_TURNS,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
        max_repeats: int = DEFAULT_MAX_REPEATS,
    ) -> None:
        self.max_turns = max_turns
        self.token_budget = token_budget
        self.max_repeats = max_repeats
        self.turns = 0
        self.tokens = 0
        self._calls: dict[tuple[str, str], int] = {}

    def check(self, tool_name: str, args=None, *, tokens: int = 0) -> tuple[bool, str | None]:
        """Räkna upp och bedöm anropet. Returnerar ``(allow, reason)``.

        ``reason`` är None när tillåtet, annars en mänsklig förklaring till nekandet.
        """
        self.turns += 1
        self.tokens += int(tokens)
        key = _call_key(tool_name, args)
        self._calls[key] = self._calls.get(key, 0) + 1

        if self._calls[key] > self.max_repeats:
            return False, f"upprepat anrop '{tool_name}' ({self._calls[key]}× > {self.max_repeats})"
        if self.turns > self.max_turns:
            return False, f"turn-tak nått ({self.turns} > {self.max_turns})"
        if self.tokens > self.token_budget:
            return False, f"token-budget slut ({self.tokens} > {self.token_budget})"
        return True, None

    def snapshot(self) -> dict:
        """Aktuellt läge — matar gärna session_store.record_metrics (#58)."""
        return {"turns": self.turns, "tokens": self.tokens, "distinct_calls": len(self._calls)}
