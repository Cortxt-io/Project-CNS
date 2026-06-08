"""Save and load text snapshots.

Storage layout:
  data/snapshots/<url_slug>/
    <timestamp>.json   -- each run produces one file

Each JSON file contains:
  { "url", "label", "fetched_at", "text" }

Why JSON: easy to inspect, no extra dependency, good enough for MVP.
Why not a database: files are simpler to debug and version-control.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _slug(url: str) -> str:
    """Deterministic short directory name for a URL."""
    h = hashlib.sha256(url.encode()).hexdigest()[:12]
    # Keep a readable prefix from the domain
    safe = url.split("//")[-1].split("/")[0].replace(".", "_")
    return f"{safe}__{h}"


def save_snapshot(data_dir: Path, url: str, label: str, text: str) -> Path:
    """Persist a snapshot and return the file path."""
    slug = _slug(url)
    snap_dir = data_dir / "snapshots" / slug
    snap_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    filename = now.strftime("%Y%m%d_%H%M%S") + ".json"
    path = snap_dir / filename

    payload = {
        "url": url,
        "label": label,
        "fetched_at": now.isoformat(),
        "text": text,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_latest_snapshots(data_dir: Path, url: str, count: int = 2) -> list[dict]:
    """Return the `count` most recent snapshots for a URL, newest first."""
    slug = _slug(url)
    snap_dir = data_dir / "snapshots" / slug
    if not snap_dir.exists():
        return []

    files = sorted(snap_dir.glob("*.json"), reverse=True)
    results = []
    for f in files[:count]:
        results.append(json.loads(f.read_text(encoding="utf-8")))
    return results


def load_latest_snapshot_paths(data_dir: Path, url: str, count: int = 2) -> list[Path]:
    """Return paths to the `count` most recent snapshot files, newest first."""
    slug = _slug(url)
    snap_dir = data_dir / "snapshots" / slug
    if not snap_dir.exists():
        return []
    return sorted(snap_dir.glob("*.json"), reverse=True)[:count]
