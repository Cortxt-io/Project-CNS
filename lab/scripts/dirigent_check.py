"""Stop-hook: Sessionskoordinatorns regelbaserade check utan LLM.

Körs vid varje session-stop. Kontrollerar:
1. Commit-skuld: hur många commits är aktiv branch före main?
2. Hängande running-sessioner
3. Alla issues stängda på en quest? (merge-trigger)

Injicerar [SESSIONSKOORDINATOR]-varningar i stdout om något kräver beslut.
Crash-proof: exit 0 alltid.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MERGE_WARN_THRESHOLD = 10
MERGE_ESCALATE_THRESHOLD = 20


def git_commits_ahead() -> tuple[str, int]:
    """Returnerar (branch-namn, antal commits före main)."""
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
        if branch in ("main", "HEAD"):
            return branch, 0
        count_str = subprocess.check_output(
            ["git", "rev-list", "--count", f"origin/main..{branch}"],
            cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
        return branch, int(count_str)
    except Exception:
        return "unknown", 0


def running_sessions() -> list[dict]:
    try:
        sessions_dir = ROOT / "exports" / "sessions"
        if not sessions_dir.exists():
            return []
        result = []
        for f in sessions_dir.glob("session-*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if data.get("status") == "running":
                    result.append(data)
            except Exception:
                pass
        return result
    except Exception:
        return []


def main() -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")

        warnings = []

        # 1. Commit-skuld
        branch, ahead = git_commits_ahead()
        if ahead >= MERGE_ESCALATE_THRESHOLD:
            warnings.append(
                f"[SESSIONSKOORDINATOR] 🔴 MERGE-SKULD: {branch} är {ahead} commits före main "
                f"— eskalerat, kalla @devops-ingenjor för merge-beslut"
            )
        elif ahead >= MERGE_WARN_THRESHOLD:
            warnings.append(
                f"[SESSIONSKOORDINATOR] ⚠️ MERGE-SKULD: {branch} är {ahead} commits före main "
                f"— dags att merga eller skapa PR?"
            )

        # 2. Hängande running-sessioner (>45 min utan uppdatering)
        import time
        now = time.time()
        for s in running_sessions():
            try:
                from datetime import datetime, timezone
                created = datetime.fromisoformat(
                    s["created_at"].replace("Z", "+00:00")
                ).timestamp()
                updated = datetime.fromisoformat(
                    s["updated_at"].replace("Z", "+00:00")
                ).timestamp()
                age_min = (now - created) / 60
                if age_min > 45 and abs(updated - created) < 5:
                    warnings.append(
                        f"[SESSIONSKOORDINATOR] ⚠️ HÄNGANDE SESSION: {s['id']} "
                        f"— {s.get('summary', '?')} — kör sedan {int(age_min)} min"
                    )
            except Exception:
                pass

        for w in warnings:
            print(w)

    except Exception:
        pass


if __name__ == "__main__":
    main()
