"""Migrate the legacy quest JSON store (exports/quests/*.json) to GitHub Issues.

Mapping (decided — option 1): each quest -> ONE issue tied to its node via the
``node:<slug>`` label. completed/archived quests -> a CLOSED issue (the quest's
result_summary becomes the closing comment); suggested/active/in_progress ->
an OPEN issue. Milestones (quests-as-groupings) are reserved for new multi-issue
work packages, so the migration does not create one per legacy quest.

Idempotent: skips a quest whose title already has a matching ``node:<slug>``
issue in any state, so re-running is safe.

Dry-run by default. ``--apply`` creates issues for real (needs GITHUB_REPO +
CNS_GITHUB_TOKEN). Writes are rate-limited with a small sleep.

Usage:
    python scripts/migrate_quests_to_issues.py            # dry-run
    python scripts/migrate_quests_to_issues.py --apply    # for real
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import issues_client as ic  # noqa: E402

QUESTS_DIR = REPO_ROOT / "exports" / "quests"
CLOSED_STATES = {"completed", "archived"}


def _load_quests() -> list[dict]:
    if not QUESTS_DIR.exists():
        return []
    quests = []
    for p in sorted(QUESTS_DIR.glob("*.json")):
        try:
            quests.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception as exc:
            print(f"  ! skip {p.name}: {exc}")
    return quests


def _issue_body(q: dict) -> str:
    parts = [(q.get("description") or "").strip()]
    if q.get("estimated_impact"):
        parts.append(f"**Estimated impact:** {q['estimated_impact']}")
    parts.append(f"_Migrated from quest {q.get('id', '')}._")
    return "\n\n".join(p for p in parts if p).strip()


def migrate(apply: bool, token: str | None = None, sleep: float = 0.5) -> dict:
    quests = _load_quests()
    summary = {"total": len(quests), "created": 0, "closed": 0, "skipped": 0, "errors": 0}

    for q in quests:
        slug = q.get("slug")
        title = q.get("title")
        status = q.get("status", "")
        if not slug or not title:
            print(f"  ! skip {q.get('id')}: missing slug/title")
            summary["skipped"] += 1
            continue

        action = "closed-issue" if status in CLOSED_STATES else "open-issue"
        if not apply:
            print(f"  [dry] {q.get('id')} ({status}) -> {action}  node:{slug}  \"{title[:60]}\"")
            continue

        try:
            existing = [
                i for i in ic.list_issues(node_slug=slug, state="all", token=token)
                if i.get("title") == title
            ]
            if existing:
                print(f"  = skip {q.get('id')}: issue #{existing[0]['number']} already exists")
                summary["skipped"] += 1
                continue

            issue = ic.create_issue(node_slug=slug, title=title, body=_issue_body(q), token=token)
            summary["created"] += 1
            print(f"  + created #{issue['number']} for {q.get('id')} ({status})")
            time.sleep(sleep)

            if status in CLOSED_STATES:
                note = q.get("result_summary") or f"Migrated as {status}."
                ic.close_issue(issue["number"], comment=note, token=token)
                summary["closed"] += 1
                time.sleep(sleep)
        except Exception as exc:
            print(f"  ! error {q.get('id')}: {exc}")
            summary["errors"] += 1

    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Migrate legacy quests to GitHub Issues.")
    ap.add_argument("--apply", action="store_true",
                    help="actually create issues (default: dry-run)")
    args = ap.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== Quest -> Issues migration ({mode}) ===")
    summary = migrate(apply=args.apply)
    print(f"\nSummary: {summary}")
    if not args.apply:
        print("Dry-run only. Re-run with --apply to create issues (needs CNS_GITHUB_TOKEN).")


if __name__ == "__main__":
    main()
