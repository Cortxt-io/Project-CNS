"""Verifiering av lease-lagret (scripts/lease_store.py) — spec §8.

Kör de fyra krockscenarierna ur ``plans/lease-layer-spec.md`` utan att kräva en
riktig Redis-server: ``fakeredis`` (med ``lupa`` för Lua-scripten) backar
``_get_redis``. TTL-förnyelse verifieras via ``r.ttl`` i stället för långa
sleeps, så hela sviten kör på <1 s.

Körs fristående (``python tests/test_lease_store.py``) ELLER under pytest om det
finns. Exit ≠ 0 om något scenario fallerar.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fakeredis  # noqa: E402

from scripts import lease_store  # noqa: E402


def _fake():
    """Färsk in-memory Redis (decode_responses=True, som produktionsklienten)."""
    return fakeredis.FakeRedis(decode_responses=True)


def _patch(monkeyish_client):
    """Peka lease_store._get_redis på en given klient (eller None för fail-open)."""
    lease_store._get_redis = lambda: monkeyish_client  # type: ignore[assignment]


# --- Scenario 1: två claims mot samma issue ---------------------------------
def test_double_claim_single_winner():
    _patch(_fake())
    first = lease_store.claim(42, "alice")
    second = lease_store.claim(42, "bob")
    assert first["claimed"] is True, first
    assert second["claimed"] is False, second
    assert second["owner"] == "alice", second  # andra ser nuvarande ägare
    lease = lease_store.get_lease(42)
    assert lease and lease["owner"] == "alice", lease


# --- Scenario 2: release endast av ägare ------------------------------------
def test_release_owner_check():
    _patch(_fake())
    lease_store.claim(7, "alice")
    assert lease_store.release(7, "bob")["released"] is False  # fel ägare
    assert lease_store.release(7, "alice")["released"] is True  # rätt ägare
    # frisläppt → ny ägare kan claima
    assert lease_store.claim(7, "bob")["claimed"] is True


# --- Scenario 3: heartbeat förnyar TTL, bara av ägare, bevarar claimed_at ----
def test_heartbeat_renews_ttl():
    client = _fake()
    _patch(client)
    claimed = lease_store.claim(9, "alice", ttl=2)
    assert claimed["claimed"] is True
    assert client.ttl(lease_store._key(9)) <= 2

    # fel ägare → ingen förnyelse
    assert lease_store.heartbeat(9, "bob", ttl=300)["renewed"] is False
    # rätt ägare → TTL hoppar upp
    assert lease_store.heartbeat(9, "alice", ttl=300)["renewed"] is True
    assert client.ttl(lease_store._key(9)) > 2

    # claimed_at bevaras, heartbeat_at uppdateras
    lease = lease_store.get_lease(9)
    assert lease["claimed_at"] == claimed["claimed_at"], lease
    assert lease["heartbeat_at"] >= claimed["claimed_at"], lease


# --- list_leases ser aktiva leases ------------------------------------------
def test_list_leases():
    _patch(_fake())
    lease_store.claim(1, "alice")
    lease_store.claim(2, "bob")
    leases = lease_store.list_leases()
    nums = sorted(l["number"] for l in leases)
    assert nums == [1, 2], leases


# --- Scenario 4: fail-open när Redis saknas ---------------------------------
def test_fail_open_no_redis():
    _patch(None)  # _get_redis → None, som REDIS_URL osatt
    assert lease_store.claim(5, "alice") == {"claimed": False, "reason": "redis-unavailable"}
    assert lease_store.release(5, "alice") == {"released": False, "reason": "redis-unavailable"}
    assert lease_store.heartbeat(5, "alice") == {"renewed": False, "reason": "redis-unavailable"}
    assert lease_store.get_lease(5) is None
    assert lease_store.list_leases() == []


def _run_standalone() -> int:
    tests = [
        test_double_claim_single_winner,
        test_release_owner_check,
        test_heartbeat_renews_ttl,
        test_list_leases,
        test_fail_open_no_redis,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {t.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"ERROR {t.__name__}: {type(exc).__name__}: {exc}")
    print(f"--- {len(tests) - failed}/{len(tests)} gröna ---")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_standalone())
