"""Lease layer for issue coordination — ephemeral claims over GitHub Issues.

When many agent-runs work a shared repo, two can pick the same open issue and
double-work or clobber each other. A lease is an atomic "I've got this": only one
run owns an issue at a time. The issue stays the source of truth on GitHub; the
live claim lives only in Redis (ephemeral, TTL'd), so there's no body-PATCH storm.

Design (see ``plans/lease-layer-spec.md``):
  - key    ``lease:issue:<number>``  (own namespace, separate from eventstream)
  - value  JSON {owner, claimed_at, heartbeat_at, ttl}
  - claim  ``SET key value NX EX ttl`` — NX = only if absent → atomic, one winner
  - the owner is the GitHub login from the OAuth token (set by the MCP wrapper)

**Fail-open:** if Redis is unavailable (REDIS_URL unset or down) every operation
returns False/empty WITHOUT raising — agents coordinate as before. Fail-closed
would turn a Redis outage into a work stoppage. This mirrors ``eventstream.py``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

# Reuse the single Redis-connection helper (same client/config as the live-buffer).
from scripts.eventstream import _get_redis

logger = logging.getLogger(__name__)

LEASE_KEY_PREFIX = "lease:issue:"
DEFAULT_TTL_SECONDS = 300  # 5 min; an abandoned (crashed) run auto-releases.

# Owner-checked release: DEL only if the stored owner matches (atomic).
_RELEASE_LUA = """
local v = redis.call('GET', KEYS[1])
if not v then return 0 end
local ok, data = pcall(cjson.decode, v)
if ok and data['owner'] == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""

# Owner-checked heartbeat: refresh heartbeat_at + TTL only if the owner matches,
# preserving the original claimed_at (atomic — reads, merges and writes in one script).
# ARGV: [1] owner, [2] new heartbeat_at (iso), [3] ttl seconds.
_HEARTBEAT_LUA = """
local v = redis.call('GET', KEYS[1])
if not v then return 0 end
local ok, data = pcall(cjson.decode, v)
if ok and data['owner'] == ARGV[1] then
    data['heartbeat_at'] = ARGV[2]
    data['ttl'] = tonumber(ARGV[3])
    return redis.call('SET', KEYS[1], cjson.encode(data), 'XX', 'EX', tonumber(ARGV[3]))
        and 1 or 0
end
return 0
"""


def _key(number: int) -> str:
    return f"{LEASE_KEY_PREFIX}{int(number)}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def claim(number: int, owner: str, ttl: int = DEFAULT_TTL_SECONDS) -> dict:
    """Atomically claim an issue for *owner*.

    Returns ``{"claimed": True, "owner", "claimed_at", "ttl"}`` on success, or
    ``{"claimed": False, "owner": <current owner or None>}`` if already held.
    Fail-open: ``{"claimed": False, "reason": "redis-unavailable"}`` if no Redis.
    """
    r = _get_redis()
    if r is None:
        return {"claimed": False, "reason": "redis-unavailable"}
    now = _now_iso()
    payload = json.dumps(
        {"owner": owner, "claimed_at": now, "heartbeat_at": now, "ttl": ttl},
        ensure_ascii=False,
    )
    try:
        won = r.set(_key(number), payload, nx=True, ex=ttl)
        if won:
            return {"claimed": True, "owner": owner, "claimed_at": now, "ttl": ttl}
        current = get_lease(number)
        return {"claimed": False, "owner": (current or {}).get("owner")}
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("Lease claim failed for #%s: %s", number, exc)
        return {"claimed": False, "reason": "redis-error"}


def release(number: int, owner: str) -> dict:
    """Release a lease, but only if *owner* holds it (atomic owner-check)."""
    r = _get_redis()
    if r is None:
        return {"released": False, "reason": "redis-unavailable"}
    try:
        deleted = r.eval(_RELEASE_LUA, 1, _key(number), owner)
        return {"released": bool(deleted)}
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("Lease release failed for #%s: %s", number, exc)
        return {"released": False, "reason": "redis-error"}


def heartbeat(number: int, owner: str, ttl: int = DEFAULT_TTL_SECONDS) -> dict:
    """Renew a lease's TTL, but only if *owner* holds it (keeps a long run alive).

    Updates ``heartbeat_at`` and TTL while preserving the original ``claimed_at``
    (the Lua script merges into the stored value rather than rebuilding it).
    """
    r = _get_redis()
    if r is None:
        return {"renewed": False, "reason": "redis-unavailable"}
    try:
        renewed = r.eval(_HEARTBEAT_LUA, 1, _key(number), owner, _now_iso(), str(ttl))
        return {"renewed": bool(renewed)}
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("Lease heartbeat failed for #%s: %s", number, exc)
        return {"renewed": False, "reason": "redis-error"}


def get_lease(number: int) -> Optional[dict]:
    """Return the current lease for an issue, or None if free/unavailable."""
    r = _get_redis()
    if r is None:
        return None
    try:
        raw = r.get(_key(number))
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("Lease get failed for #%s: %s", number, exc)
        return None
    if not raw:
        return None
    try:
        lease = json.loads(raw)
    except json.JSONDecodeError:
        return None
    lease["number"] = int(number)
    return lease


def list_leases() -> list[dict]:
    """List all active leases (uses SCAN, not KEYS). Empty if Redis unavailable."""
    r = _get_redis()
    if r is None:
        return []
    leases: list[dict] = []
    try:
        for key in r.scan_iter(match=f"{LEASE_KEY_PREFIX}*"):
            raw = r.get(key)
            if not raw:
                continue
            try:
                lease = json.loads(raw)
            except json.JSONDecodeError:
                continue
            try:
                lease["number"] = int(str(key)[len(LEASE_KEY_PREFIX):])
            except ValueError:
                pass
            leases.append(lease)
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("Lease list failed: %s", exc)
        return []
    return leases
