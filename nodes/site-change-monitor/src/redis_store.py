"""Redis-backed snapshot store for Site Change Monitor.

Provides fast O(1) latest-snapshot lookups, a change-history timeline
via Sorted Sets, and atomic check/change counters -- replacing the
filesystem scan that the file-based snapshot module relies on.

Redis data model (follows Redis best-practice rules from the plugin):
  Hash    scm:snapshot:<slug>   -- latest snapshot metadata + text
  ZSET    scm:history:<slug>    -- change timeline (score=unix_ts, member=ts_iso)
  Hash    scm:stats:<slug>      -- per-URL statistics (check_count, change_count)

Rules applied:
  - data-choose-structure: Hash for flat objects, Sorted Set for rankings/ranges
  - data-key-naming:       colon-separated, service-prefixed keys
  - data-incr:             INCR for atomic counters
  - ram-ttl:               TTL on snapshot hashes to prevent unbounded growth
  - conn-pooling:          ConnectionPool for reuse
  - conn-timeouts:         socket_timeout + socket_connect_timeout
  - data-transactions:     pipeline for atomic multi-key writes
  - conn-blocking:         SCAN instead of KEYS for production safety
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Key helpers -- consistent colon-separated naming (rule: data-key-naming)
# ---------------------------------------------------------------------------

def _slug(url: str) -> str:
    """Deterministic short identifier for a URL (same logic as snapshot.py)."""
    h = hashlib.sha256(url.encode()).hexdigest()[:12]
    safe = url.split("//")[-1].split("/")[0].replace(".", "_")
    return f"{safe}__{h}"


def _snap_key(slug: str) -> str:
    return f"scm:snapshot:{slug}"


def _history_key(slug: str) -> str:
    return f"scm:history:{slug}"


def _stats_key(slug: str) -> str:
    return f"scm:stats:{slug}"


def _decode_dict(data: dict) -> dict:
    """Decode bytes keys/values from redis-py to str."""
    return {k.decode() if isinstance(k, bytes) else k:
            v.decode() if isinstance(v, bytes) else v
            for k, v in data.items()}


# ---------------------------------------------------------------------------
# Redis store
# ---------------------------------------------------------------------------

class RedisSnapshotStore:
    """Redis-backed store for site-change-monitor snapshots.

    All methods catch Redis errors and degrade gracefully (return None/empty)
    so the caller can fall back to file-based storage if Redis becomes
    unavailable at runtime.

    Usage:
        store = RedisSnapshotStore.from_config(cfg.get("redis"))
        store.save_snapshot(url, label, text)
        latest = store.load_latest_snapshot(url)
        history = store.load_snapshot_history(url, count=5)
    """

    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 6379
    DEFAULT_DB = 0
    DEFAULT_SNAPSHOT_TTL = 7 * 24 * 3600  # 7 days (rule: ram-ttl)
    DEFAULT_MAX_HISTORY = 100

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        db: int = DEFAULT_DB,
        password: Optional[str] = None,
        snapshot_ttl: int = DEFAULT_SNAPSHOT_TTL,
        max_history: int = DEFAULT_MAX_HISTORY,
    ):
        import redis  # lazy import -- redis is an optional dependency

        # rule: conn-pooling -- reuse connections via pool
        pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=10,
            # rule: conn-timeouts -- tuned timeouts
            socket_timeout=5.0,
            socket_connect_timeout=2.0,
        )
        self._client = redis.Redis(connection_pool=pool)
        self._snapshot_ttl = snapshot_ttl
        self._max_history = max_history

    # -- Factory ------------------------------------------------------------

    @classmethod
    def from_config(cls, redis_cfg: Optional[dict]) -> Optional["RedisSnapshotStore"]:
        """Create a store from the 'redis' section of config.yaml.

        Returns None if the redis section is missing or disabled, so the
        caller can fall back to file-based storage.
        """
        if not redis_cfg or not redis_cfg.get("enabled", False):
            return None
        try:
            import redis  # noqa: F401 -- verify redis-py is installed
        except ImportError:
            logger.warning("redis-py not installed; Redis store disabled. "
                           "Install with: pip install redis")
            return None
        return cls(
            host=redis_cfg.get("host", cls.DEFAULT_HOST),
            port=redis_cfg.get("port", cls.DEFAULT_PORT),
            db=redis_cfg.get("db", cls.DEFAULT_DB),
            password=redis_cfg.get("password"),
            snapshot_ttl=redis_cfg.get("snapshot_ttl_seconds", cls.DEFAULT_SNAPSHOT_TTL),
            max_history=redis_cfg.get("max_history", cls.DEFAULT_MAX_HISTORY),
        )

    # -- Ping / health ------------------------------------------------------

    def ping(self) -> bool:
        """Return True if Redis is reachable."""
        try:
            return self._client.ping()
        except Exception:
            return False

    # -- Write operations ---------------------------------------------------

    def save_snapshot(self, url: str, label: str, text: str) -> Optional[dict]:
        """Persist a snapshot and update history/stats.

        Uses a pipeline (rule: data-transactions) so the snapshot hash,
        history entry, and stats counter are written atomically.

        Returns the snapshot dict that was stored, or None on error.
        """
        slug = _slug(url)
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        now_ts = now.timestamp()
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

        snap = {
            "url": url,
            "label": label,
            "fetched_at": now_iso,
            "content_hash": content_hash,
        }

        try:
            # rule: data-transactions -- atomic multi-key write via pipeline
            pipe = self._client.pipeline(transaction=True)

            # rule: data-choose-structure -- Hash for flat snapshot metadata
            pipe.hset(_snap_key(slug), mapping=snap)
            # Store text in a separate field (could be large)
            pipe.hset(_snap_key(slug), "text", text)
            # rule: ram-ttl -- set TTL on snapshot hash
            pipe.expire(_snap_key(slug), self._snapshot_ttl)

            # rule: data-choose-structure -- Sorted Set for timeline
            pipe.zadd(_history_key(slug), {now_iso: now_ts})

            # rule: data-incr -- atomic counter for check count
            pipe.hincrby(_stats_key(slug), "check_count", 1)
            pipe.hset(_stats_key(slug), "last_checked_at", now_iso)

            pipe.execute()

            # Trim history to max_history entries (keep newest)
            self._client.zremrangebyrank(
                _history_key(slug), 0, -(self._max_history + 1)
            )

            snap["text"] = text
            logger.info("Saved snapshot to Redis: %s (%s)", label, slug)
            return snap
        except Exception as exc:
            logger.warning("Redis save_snapshot failed for %s: %s", slug, exc)
            return None

    def record_change(self, url: str) -> None:
        """Increment the change counter for a URL.

        Call this after detecting a meaningful change.
        """
        slug = _slug(url)
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            # rule: data-incr -- atomic increment
            self._client.hincrby(_stats_key(slug), "change_count", 1)
            self._client.hset(_stats_key(slug), "last_change_at", now_iso)
        except Exception as exc:
            logger.warning("Redis record_change failed for %s: %s", slug, exc)

    # -- Read operations ----------------------------------------------------

    def load_latest_snapshot(self, url: str) -> Optional[dict]:
        """Return the latest snapshot dict for a URL, or None.

        O(1) lookup via Hash -- no filesystem scan needed.
        """
        slug = _slug(url)
        try:
            data = self._client.hgetall(_snap_key(slug))
            if not data:
                return None
            return _decode_dict(data)
        except Exception as exc:
            logger.warning("Redis load_latest_snapshot failed for %s: %s", slug, exc)
            return None

    def load_snapshot_history(
        self, url: str, count: int = 5
    ) -> list[str]:
        """Return the `count` most recent snapshot timestamps, newest first.

        Uses ZREVRANGE on the Sorted Set -- efficient range query by score.
        """
        slug = _slug(url)
        try:
            members = self._client.zrevrange(_history_key(slug), 0, count - 1)
            return [m.decode() if isinstance(m, bytes) else m for m in members]
        except Exception as exc:
            logger.warning("Redis load_snapshot_history failed for %s: %s", slug, exc)
            return []

    def get_stats(self, url: str) -> Optional[dict]:
        """Return check/change statistics for a URL."""
        slug = _slug(url)
        try:
            data = self._client.hgetall(_stats_key(slug))
            if not data:
                return None
            return _decode_dict(data)
        except Exception as exc:
            logger.warning("Redis get_stats failed for %s: %s", slug, exc)
            return None

    def get_all_slugs(self) -> list[str]:
        """Return all URL slugs that have snapshots in Redis.

        Uses SCAN with MATCH (rule: conn-blocking -- avoid KEYS in production).
        """
        slugs = []
        try:
            cursor = 0
            while True:
                cursor, keys = self._client.scan(
                    cursor, match="scm:snapshot:*", count=100
                )
                for key in keys:
                    k = key.decode() if isinstance(key, bytes) else key
                    slug = k.split(":", 2)[-1]
                    slugs.append(slug)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.warning("Redis get_all_slugs failed: %s", exc)
        return slugs
