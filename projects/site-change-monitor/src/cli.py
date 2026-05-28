"""CLI entry point for Site Change Monitor.

Usage:
    python -m src.cli                    # uses config.yaml in cwd
    python -m src.cli --config path.yaml # custom config path
    python -m src.cli --verbose          # show diff details even for noise
"""

import argparse
import sys
from pathlib import Path

from .config import load_config
from .fetcher import fetch_html
from .extractor import extract_text
from .snapshot import save_snapshot, load_latest_snapshots, load_latest_snapshot_paths
from .redis_store import RedisSnapshotStore
from .differ import compute_diff
from .reporter import generate_report
from .html_report import generate_html_report


def _print_result(result, verbose: bool):
    """Print a single URL's diff result to stdout."""
    status = ""
    if not result.has_change:
        status = "[NO CHANGE]"
    elif result.is_meaningful:
        status = "[MEANINGFUL CHANGE]"
    else:
        status = "[NOISE]"

    print(f"\n{'='*60}")
    print(f"  {status}  {result.label}")
    print(f"  URL: {result.url}")
    print(f"  {result.reason}")

    if result.has_change and (result.is_meaningful or verbose):
        print(f"\n  +++ Added ({len(result.added_lines)} lines):")
        for line in result.added_lines[:20]:
            print(f"    + {line}")
        if len(result.added_lines) > 20:
            print(f"    ... and {len(result.added_lines) - 20} more")

        print(f"  --- Removed ({len(result.removed_lines)} lines):")
        for line in result.removed_lines[:20]:
            print(f"    - {line}")
        if len(result.removed_lines) > 20:
            print(f"    ... and {len(result.removed_lines) - 20} more")

    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Site Change Monitor - detect meaningful webpage changes")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML (default: config.yaml)")
    parser.add_argument("--verbose", action="store_true", help="Show diff details even for noise changes")
    parser.add_argument("--data-dir", default="data", help="Directory for snapshots (default: data)")
    args = parser.parse_args()

    config_path = Path(args.config)
    data_dir = Path(args.data_dir)

    if not config_path.exists():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    cfg = load_config(config_path)
    filters = cfg["filters"]
    urls = cfg["urls"]

    # Initialize Redis store if configured (optional backend)
    redis_store = RedisSnapshotStore.from_config(cfg.get("redis"))
    use_redis = False
    if redis_store:
        if redis_store.ping():
            use_redis = True
            print("  Redis store: connected")
        else:
            print("  Redis store: configured but unreachable, falling back to files")

    print(f"Site Change Monitor - checking {len(urls)} URL(s)...")

    results = []
    snapshot_paths = {}       # url -> Path of current snapshot
    prev_snapshot_paths = {}  # url -> Path of previous snapshot or None
    for entry in urls:
        url = entry["url"]
        label = entry["label"]
        print(f"\n  Fetching: {label} ({url})")

        try:
            html = fetch_html(url)
        except Exception as e:
            print(f"  ERROR fetching {url}: {e}", file=sys.stderr)
            continue

        text = extract_text(html)

        # Load previous snapshot -- prefer Redis for O(1) lookup
        old_text = None
        if use_redis:
            prev_snap = redis_store.load_latest_snapshot(url)
            if prev_snap:
                old_text = prev_snap.get("text")
        else:
            previous = load_latest_snapshots(data_dir, url, count=1)
            old_text = previous[0]["text"] if previous else None

        # Track previous snapshot path (file-based, for report generation)
        prev_paths = load_latest_snapshot_paths(data_dir, url, count=1)
        prev_snapshot_paths[url] = prev_paths[0] if prev_paths else None

        # Save current snapshot to both file system (for reports) and Redis
        snap_path = save_snapshot(data_dir, url, label, text)
        snapshot_paths[url] = snap_path
        print(f"  Saved snapshot: {snap_path}")

        if use_redis:
            redis_store.save_snapshot(url, label, text)
            print(f"  Saved to Redis store")

        # Compute diff
        diff_result = compute_diff(url, label, old_text, text, filters)
        results.append(diff_result)

        # Record change in Redis stats
        if use_redis and diff_result.is_meaningful:
            redis_store.record_change(url)

    # Print summary
    print(f"\n\n{'#'*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'#'*60}")

    for r in results:
        _print_result(r, args.verbose)

    # Quick stats
    meaningful = sum(1 for r in results if r.is_meaningful)
    noise = sum(1 for r in results if r.has_change and not r.is_meaningful)
    unchanged = sum(1 for r in results if not r.has_change)
    print(f"\nDone. {meaningful} meaningful, {noise} noise, {unchanged} unchanged.")

    # Generate reports
    if results:
        run_dir = generate_report(data_dir, results, snapshot_paths, prev_snapshot_paths)
        html_path = generate_html_report(run_dir)
        print(f"\nReports saved:")
        print(f"  JSON: {run_dir / 'report.json'}")
        print(f"  HTML: {html_path}")

    # Show Redis stats summary if available
    if use_redis:
        print(f"\n  Redis Statistics:")
        for entry in urls:
            stats = redis_store.get_stats(entry["url"])
            if stats:
                print(f"    {entry['label']}: "
                      f"{stats.get('check_count', 0)} checks, "
                      f"{stats.get('change_count', 0)} changes")
            history = redis_store.load_snapshot_history(entry["url"], count=3)
            if history:
                print(f"      Recent snapshots: {', '.join(history)}")


if __name__ == "__main__":
    main()
