"""CLI entry point for DocsWatch.

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
    parser = argparse.ArgumentParser(description="DocsWatch - monitor changelogs and docs for meaningful changes")
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

    print(f"DocsWatch - checking {len(urls)} page(s)...")

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

        # Load previous snapshot before saving new one
        previous = load_latest_snapshots(data_dir, url, count=1)
        old_text = previous[0]["text"] if previous else None

        # Track previous snapshot path (before saving the new one)
        prev_paths = load_latest_snapshot_paths(data_dir, url, count=1)
        prev_snapshot_paths[url] = prev_paths[0] if prev_paths else None

        # Save current snapshot
        snap_path = save_snapshot(data_dir, url, label, text)
        snapshot_paths[url] = snap_path
        print(f"  Saved snapshot: {snap_path}")

        # Compute diff
        diff_result = compute_diff(url, label, old_text, text, filters)
        results.append(diff_result)

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


if __name__ == "__main__":
    main()
