"""Cortxt Eventstream — unified event logging with six dimensions.

Three-layer persistence:
  1. Redis live-buffer  — webhook writes, dashboard reads (near-realtime)
  2. Local .jsonl       — CI pull appends, durable daily archive
  3. CI commit          — .jsonl + aggregated JSON committed once daily

Event schema (six dimensions):
  what  — event type (push, pull_request, workflow_run, deploy, config_change, manual)
  when  — ISO 8601 UTC timestamp
  why   — commit message / PR title / deploy reason
  how   — summary of change (file count, deploy result)
  who   — user or system that triggered
  where — repo:branch / platform:environment
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"

# Redis key for the live buffer
REDIS_KEY = "eventstream:recent"
REDIS_MAX_EVENTS = 500
REDIS_TTL_SECONDS = 7 * 24 * 3600  # 7 days

# Valid event sources
VALID_SOURCES = {"github", "railway", "cloudflare", "devwatch", "quest", "manual"}


# ---------------------------------------------------------------------------
# Event creation
# ---------------------------------------------------------------------------


def make_event(
    *,
    what: str,
    when: str | None = None,
    why: str = "",
    how: str = "",
    who: str = "",
    where: str = "",
    source: str,
    slug: str | None = None,
    event_id: str | None = None,
    meta: dict | None = None,
) -> dict:
    """Create a normalized event dict with six dimensions.

    Args:
        what: Event type (push, pull_request, workflow_run, deploy, etc.)
        when: ISO 8601 UTC. Defaults to now.
        why: Commit message / PR title / reason.
        how: Summary of change.
        who: User or system that triggered.
        where: repo:branch or platform:environment.
        source: One of VALID_SOURCES.
        slug: CNS node slug this event relates to (None for global).
        event_id: Unique ID. Auto-generated if not provided.
        meta: Source-specific metadata.
    """
    if source not in VALID_SOURCES:
        raise ValueError(f"Invalid source '{source}'. Allowed: {', '.join(sorted(VALID_SOURCES))}")

    if when is None:
        when = datetime.now(timezone.utc).isoformat()

    if event_id is None:
        event_id = f"evt:{source}:{what}:{uuid.uuid4().hex[:8]}"

    return {
        "id": event_id,
        "what": what,
        "when": when,
        "why": why,
        "how": how,
        "who": who,
        "where": where,
        "source": source,
        "slug": slug,
        "meta": meta or {},
    }


# ---------------------------------------------------------------------------
# Redis live-buffer
# ---------------------------------------------------------------------------


def _get_redis():
    """Get Redis client from REDIS_URL, or None if not configured."""
    url = os.getenv("REDIS_URL", "")
    if not url:
        return None
    try:
        import redis
        return redis.from_url(url, decode_responses=True)
    except Exception as exc:
        logger.warning("Redis connection failed: %s", exc)
        return None


def push_to_redis(event: dict) -> bool:
    """Push an event to the Redis live-buffer.

    Returns True if written, False if Redis unavailable.
    """
    r = _get_redis()
    if r is None:
        return False

    try:
        pipe = r.pipeline()
        pipe.lpush(REDIS_KEY, json.dumps(event, ensure_ascii=False))
        pipe.ltrim(REDIS_KEY, 0, REDIS_MAX_EVENTS - 1)
        pipe.expire(REDIS_KEY, REDIS_TTL_SECONDS)
        pipe.execute()
        return True
    except Exception as exc:
        logger.warning("Redis push failed: %s", exc)
        return False


def read_from_redis(limit: int = 100, slug: str | None = None,
                    source: str | None = None) -> list[dict]:
    """Read recent events from Redis live-buffer.

    Returns list of events (newest first), empty list if Redis unavailable.
    """
    r = _get_redis()
    if r is None:
        return []

    try:
        raw_events = r.lrange(REDIS_KEY, 0, limit - 1)
    except Exception as exc:
        logger.warning("Redis read failed: %s", exc)
        return []

    events = []
    for raw in raw_events:
        try:
            evt = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if slug and evt.get("slug") != slug:
            continue
        if source and evt.get("source") != source:
            continue
        events.append(evt)

    return events


# ---------------------------------------------------------------------------
# .jsonl permanent archive
# ---------------------------------------------------------------------------


def append_to_jsonl(event: dict, date_str: str | None = None) -> Path:
    """Append an event to the daily .jsonl archive file.

    Args:
        event: Normalized event dict.
        date_str: YYYY-MM-DD. Defaults to today (UTC).

    Returns:
        Path to the .jsonl file.
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORTS_DIR / f"eventstream_{date_str}.jsonl"

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    return path


def load_existing_ids(path: Path) -> set[str]:
    """Load all event IDs from a .jsonl file for dedup."""
    ids: set[str] = set()
    if not path.exists():
        return ids
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
                eid = evt.get("id", "")
                if eid:
                    ids.add(eid)
            except json.JSONDecodeError:
                continue
    return ids


def generate_aggregate(max_events: int = 500) -> Path:
    """Generate eventstream_latest.json from all .jsonl files.

    Returns path to the aggregated file.
    """
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    all_events: list[dict] = []

    for jsonl_path in sorted(EXPORTS_DIR.glob("eventstream_*.jsonl")):
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    all_events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # Sort by when descending, take most recent
    all_events.sort(key=lambda e: e.get("when", ""), reverse=True)
    recent = all_events[:max_events]

    out_path = EXPORTS_DIR / "eventstream_latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(recent, f, ensure_ascii=False, indent=2, default=str)

    return out_path


# ---------------------------------------------------------------------------
# GitHub adapters — push normalization
# ---------------------------------------------------------------------------


def normalize_push_event(payload: dict) -> list[dict]:
    """Normalize a GitHub push webhook payload into events (one per commit).

    Returns list of event dicts.
    """
    events = []
    repo = payload.get("repository", {}).get("full_name", "")
    ref = payload.get("ref", "")
    branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref

    for commit in payload.get("commits", []):
        sha = commit.get("id", "")[:8]
        events.append(make_event(
            what="push",
            when=commit.get("timestamp", ""),
            why=commit.get("message", ""),
            how=_summarize_commit(commit),
            who=commit.get("author", {}).get("username", "") or commit.get("author", {}).get("name", ""),
            where=f"{repo}:{branch}",
            source="github",
            slug=_slug_from_repo(repo),
            event_id=f"evt:github:push:{sha}",
            meta={"sha": commit.get("id", ""), "url": commit.get("url", "")},
        ))

    return events


def normalize_pr_event(payload: dict) -> list[dict]:
    """Normalize a GitHub pull_request webhook payload into an event."""
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {}).get("full_name", "")
    action = payload.get("action", "")
    number = pr.get("number", "")
    branch = pr.get("head", {}).get("ref", "")

    return [make_event(
        what="pull_request",
        when=pr.get("updated_at", "") or pr.get("created_at", ""),
        why=pr.get("title", ""),
        how=f"PR #{number} {action}",
        who=pr.get("user", {}).get("login", ""),
        where=f"{repo}:{branch}",
        source="github",
        slug=_slug_from_repo(repo),
        event_id=f"evt:github:pr:{number}",
        meta={"number": number, "action": action, "merged": pr.get("merged", False)},
    )]


def normalize_workflow_run_event(payload: dict) -> list[dict]:
    """Normalize a GitHub workflow_run webhook payload into an event."""
    run = payload.get("workflow_run", {})
    repo = payload.get("repository", {}).get("full_name", "")
    conclusion = run.get("conclusion", "")
    name = run.get("name", "")

    return [make_event(
        what="workflow_run",
        when=run.get("updated_at", "") or run.get("run_started_at", ""),
        why=run.get("display_title", "") or name,
        how=f"Workflow {name}: {conclusion}",
        who=run.get("actor", {}).get("login", ""),
        where=f"{repo}:{run.get('head_branch', '')}",
        source="github",
        slug=_slug_from_repo(repo),
        event_id=f"evt:github:workflow:{run.get('id', '')}",
        meta={"run_id": run.get("id"), "conclusion": conclusion, "name": name},
    )]


# ---------------------------------------------------------------------------
# GitHub API pull adapter (CI)
# ---------------------------------------------------------------------------


def fetch_github_commits(since: str, repo: str | None = None,
                         token: str | None = None) -> list[dict]:
    """Fetch commits from GitHub API since a given timestamp.

    Used by CI to backfill the permanent archive.
    """
    import requests as req

    if repo is None:
        repo = os.getenv("GITHUB_REPO", "")
    if token is None:
        token = os.getenv("CNS_GITHUB_TOKEN", "")
    if not repo or not token:
        logger.warning("GITHUB_REPO or CNS_GITHUB_TOKEN not set — skipping GitHub commits pull")
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    events = []
    page = 1
    while page <= 5:  # limit to 5 pages = 500 commits max
        url = f"https://api.github.com/repos/{repo}/commits"
        params = {"since": since, "per_page": 100, "page": page}
        try:
            resp = req.get(url, headers=headers, params=params, timeout=30)
        except Exception as exc:
            logger.warning("GitHub commits fetch failed: %s", exc)
            break

        if resp.status_code != 200:
            logger.warning("GitHub commits API returned %s", resp.status_code)
            break

        commits = resp.json()
        if not commits:
            break

        for c in commits:
            sha = c.get("sha", "")[:8]
            commit_data = c.get("commit", {})
            events.append(make_event(
                what="push",
                when=commit_data.get("committer", {}).get("date", ""),
                why=commit_data.get("message", "").split("\n")[0],
                how="CI backfill",
                who=commit_data.get("author", {}).get("name", ""),
                where=f"{repo}:main",
                source="github",
                slug=_slug_from_repo(repo),
                event_id=f"evt:github:push:{sha}",
            ))

        if len(commits) < 100:
            break
        page += 1

    return events


def fetch_github_workflow_runs(since: str, repo: str | None = None,
                                token: str | None = None) -> list[dict]:
    """Fetch completed workflow runs from GitHub API since a given timestamp."""
    import requests as req

    if repo is None:
        repo = os.getenv("GITHUB_REPO", "")
    if token is None:
        token = os.getenv("CNS_GITHUB_TOKEN", "")
    if not repo or not token:
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    events = []
    try:
        url = f"https://api.github.com/repos/{repo}/actions/runs"
        params = {"since": since, "status": "completed", "per_page": 100}
        resp = req.get(url, headers=headers, params=params, timeout=30)
    except Exception as exc:
        logger.warning("GitHub workflow runs fetch failed: %s", exc)
        return events

    if resp.status_code != 200:
        logger.warning("GitHub workflow runs API returned %s", resp.status_code)
        return events

    for run in resp.json().get("workflow_runs", []):
        events.append(make_event(
            what="workflow_run",
            when=run.get("updated_at", ""),
            why=run.get("display_title", "") or run.get("name", ""),
            how=f"Workflow {run.get('name', '')}: {run.get('conclusion', '')}",
            who=run.get("actor", {}).get("login", ""),
            where=f"{repo}:{run.get('head_branch', '')}",
            source="github",
            slug=_slug_from_repo(repo),
            event_id=f"evt:github:workflow:{run.get('id', '')}",
            meta={"run_id": run.get("id"), "conclusion": run.get("conclusion")},
        ))

    return events


# ---------------------------------------------------------------------------
# Stubbed adapters — Railway / Cloudflare
# ---------------------------------------------------------------------------


def fetch_railway_deploys(since: str) -> list[dict]:
    """Fetch Railway deploy events since `since`.

    Status: NOT_CONFIGURED — requires RAILWAY_API_TOKEN and verified API.
    Returns empty list. Replace implementation when API is verified.
    """
    token = os.getenv("RAILWAY_API_TOKEN", "")
    if not token:
        logger.info("Railway adapter: not configured (RAILWAY_API_TOKEN not set)")
        return []
    # TODO: Verify Railway API exposes deploy events + token is valid.
    # Once verified, implement fetch logic here. The adapter interface
    # (takes since, returns list[dict]) stays the same — only this
    # function body changes.
    logger.info("Railway adapter: token present but adapter not yet implemented")
    return []


def fetch_cloudflare_builds(since: str) -> list[dict]:
    """Fetch Cloudflare Pages builds since `since`.

    Status: NOT_CONFIGURED — requires CLOUDFLARE_API_TOKEN and verified API.
    Returns empty list. Replace implementation when API is verified.
    """
    token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    if not token:
        logger.info("Cloudflare adapter: not configured (CLOUDFLARE_API_TOKEN not set)")
        return []
    # TODO: Verify Cloudflare API exposes Pages build events + token is valid.
    # Once verified, implement fetch logic here. The adapter interface
    # (takes since, returns list[dict]) stays the same — only this
    # function body changes.
    logger.info("Cloudflare adapter: token present but adapter not yet implemented")
    return []


# ---------------------------------------------------------------------------
# Sync command (CI)
# ---------------------------------------------------------------------------


def run_sync(since: str | None = None) -> dict:
    """Pull events from all adapters, dedup, append to .jsonl, generate aggregate.

    This is the main entry point for `cns eventstream sync`.

    Returns dict with counts per source.
    """
    if since is None:
        # Default: last 24 hours
        from datetime import timedelta
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    jsonl_path = EXPORTS_DIR / f"eventstream_{today}.jsonl"

    # Load existing IDs for dedup
    existing_ids = load_existing_ids(jsonl_path)

    # Also dedup against Redis buffer
    redis_ids: set[str] = set()
    try:
        redis_events = read_from_redis(limit=REDIS_MAX_EVENTS)
        redis_ids = {e.get("id", "") for e in redis_events}
    except Exception:
        pass

    all_known_ids = existing_ids | redis_ids

    # Fetch from all adapters
    all_new: list[dict] = []
    counts: dict[str, int] = {}

    adapter_funcs = [
        ("github_commits", lambda: fetch_github_commits(since)),
        ("github_workflows", lambda: fetch_github_workflow_runs(since)),
        ("railway", lambda: fetch_railway_deploys(since)),
        ("cloudflare", lambda: fetch_cloudflare_builds(since)),
    ]

    for name, func in adapter_funcs:
        try:
            events = func()
        except Exception as exc:
            logger.warning("Adapter %s failed: %s", name, exc)
            events = []
            counts[name] = -1
            continue

        new_count = 0
        for evt in events:
            if evt.get("id", "") not in all_known_ids:
                all_new.append(evt)
                all_known_ids.add(evt.get("id", ""))
                new_count += 1
        counts[name] = new_count

    # Append to .jsonl
    for evt in all_new:
        append_to_jsonl(evt, date_str=today)

    # Also push to Redis for immediate availability
    for evt in all_new:
        push_to_redis(evt)

    # Generate aggregate
    generate_aggregate()

    counts["total_new"] = len(all_new)
    return counts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slug_from_repo(repo: str) -> str | None:
    """Best-effort mapping from GitHub repo full_name to CNS slug.

    The repo name might match a project directory directly.
    """
    if not repo:
        return None
    # repo is like "rian010194/prompt-cns" — the repo name is "prompt-cns"
    # For this repo, events relate to whatever project was touched
    # The webhook handler does per-file slug matching; this is a fallback
    return None


def _summarize_commit(commit: dict) -> str:
    """Create a brief summary of a commit's changes."""
    added = len(commit.get("added", []))
    modified = len(commit.get("modified", []))
    removed = len(commit.get("removed", []))
    total = added + modified + removed
    if total == 0:
        return "no files changed"
    parts = []
    if added:
        parts.append(f"+{added}")
    if modified:
        parts.append(f"~{modified}")
    if removed:
        parts.append(f"-{removed}")
    return f"{total} files ({', '.join(parts)})"
