"""Generate per-run JSON report and diff artifacts.

Creates:
  data/reports/<run_id>/
    report.json       -- structured run summary
    diffs/
      <url_slug>.diff.txt  -- unified diff per changed URL
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from .differ import DiffResult
from .snapshot import _slug


def _severity(result: DiffResult) -> str:
    """Map existing diff classification to severity label."""
    if not result.has_change:
        return "none"
    if result.is_meaningful:
        return "major"
    return "minor"


def _status(result: DiffResult) -> str:
    return "changed" if result.has_change else "unchanged"


def generate_report(
    data_dir: Path,
    results: list[DiffResult],
    snapshot_paths: dict[str, Path],
    previous_snapshot_paths: dict[str, Path | None],
) -> Path:
    """Write report.json and diff artifacts. Returns the run directory path."""
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%d_%H%M%S")
    run_dir = data_dir / "reports" / run_id
    diffs_dir = run_dir / "diffs"
    diffs_dir.mkdir(parents=True, exist_ok=True)

    result_entries = []
    for r in results:
        slug = _slug(r.url)
        diff_path = None

        # Write diff artifact if there's actual diff text
        if r.diff_text:
            diff_file = diffs_dir / f"{slug}.diff.txt"
            diff_file.write_text(r.diff_text, encoding="utf-8")
            diff_path = str(diff_file.relative_to(data_dir))

        snap_current = snapshot_paths.get(r.url)
        snap_previous = previous_snapshot_paths.get(r.url)

        result_entries.append({
            "url": r.url,
            "label": r.label,
            "status": _status(r),
            "severity": _severity(r),
            "summary": r.reason,
            "snapshot_current": str(snap_current.relative_to(data_dir)) if snap_current else None,
            "snapshot_previous": str(snap_previous.relative_to(data_dir)) if snap_previous else None,
            "diff_path": diff_path,
        })

    total = len(results)
    changed = sum(1 for r in results if r.has_change)

    report = {
        "run_id": run_id,
        "generated_at": now.isoformat(),
        "summary": {
            "total_urls": total,
            "changed": changed,
            "unchanged": total - changed,
            "major": sum(1 for r in results if _severity(r) == "major"),
            "minor": sum(1 for r in results if _severity(r) == "minor"),
        },
        "results": result_entries,
    }

    report_path = run_dir / "report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return run_dir
