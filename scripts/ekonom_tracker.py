"""Stop-hook: Ekonomens kostnadsstatistik och tröskelvarning.

Körs vid varje session-stop. Estimerar kostnad per agent baserat på
sessionslängd × modell-tier, sparar ackumulerad statistik till
exports/ekonom_stats.json, och injicerar [EKONOMEN]-varning om
trösklar överskrids.

Estimering (approximation — faktisk fakturering: kör /usage):
- Haiku:  ~200 tokens/sekund aktivt = 1x
- Sonnet: ~200 tokens/sekund aktivt = 10x
- Opus:   ~200 tokens/sekund aktivt = 70x

Crash-proof: exit 0 alltid.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORTS_DIR = ROOT / "exports"
STATS_FILE = EXPORTS_DIR / "ekonom_stats.json"

# Modell-tier relativkostnad (Haiku = 1x)
AGENT_MODEL_TIER: dict[str, float] = {
    "ekonomen": 1.0,
    "ide-agent": 1.0,
    "github-agent": 1.0,
    "kontext-agent": 1.0,
    "dirigenten": 1.0,
    "wiki-skribent": 10.0,
    "research-agent": 10.0,
    "backend-agent": 10.0,
    "frontend-agent": 10.0,
    "scripts-agent": 10.0,
    "stadaren": 10.0,
    "hr-chefen": 10.0,
    "tui-agent": 10.0,
    "fullstack-agent": 10.0,
    "tranaren": 10.0,
    "teamleader": 70.0,
}
DEFAULT_TIER = 10.0  # Sonnet-standard för okänd agent

# Trösklar
WARN_ESTIMATED_UNITS = 500      # ~500 Haiku-enheter = ~1 Sonnet-session
ESCALATE_ESTIMATED_UNITS = 2000  # ~2000 = lång Sonnet eller kort Opus


def load_stats() -> dict:
    try:
        return json.loads(STATS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"agents": {}, "total_units": 0.0, "sessions_tracked": 0}


def save_stats(stats: dict) -> None:
    try:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def agent_from_session(session: dict) -> str:
    """Försök utläsa agent-slug från fork_name eller summary."""
    fork = session.get("fork_name") or ""
    if fork:
        return fork
    summary = (session.get("summary") or "").lower()
    for agent in AGENT_MODEL_TIER:
        if agent in summary:
            return agent
    return "unknown"


def estimate_units(session: dict) -> float:
    """Estimera relativa kostnadsenheter för en session."""
    try:
        created = datetime.fromisoformat(
            session["created_at"].replace("Z", "+00:00")
        ).timestamp()
        updated = datetime.fromisoformat(
            session["updated_at"].replace("Z", "+00:00")
        ).timestamp()
        duration_min = max(0.0, (updated - created) / 60)
    except Exception:
        duration_min = 5.0  # fallback

    agent = agent_from_session(session)
    tier = AGENT_MODEL_TIER.get(agent, DEFAULT_TIER)
    # Grov estimering: 10 enheter per minut × tier-multiplikator
    return duration_min * 10 * tier


def check_recent_sessions() -> list[dict]:
    """Läs lokala session-filer, returnera de som stängdes senaste 5 min."""
    sessions_dir = EXPORTS_DIR / "sessions"
    if not sessions_dir.exists():
        return []
    result = []
    cutoff = time.time() - 300  # 5 min
    for f in sessions_dir.glob("session-*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status") == "done":
                updated = datetime.fromisoformat(
                    data["updated_at"].replace("Z", "+00:00")
                ).timestamp()
                if updated > cutoff:
                    result.append(data)
        except Exception:
            pass
    return result


def main() -> None:
    import sys
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")

        stats = load_stats()
        recent = check_recent_sessions()
        session_units = 0.0

        for session in recent:
            units = estimate_units(session)
            agent = agent_from_session(session)
            session_units += units

            # Uppdatera per-agent-statistik
            if agent not in stats["agents"]:
                stats["agents"][agent] = {"sessions": 0, "total_units": 0.0}
            stats["agents"][agent]["sessions"] += 1
            stats["agents"][agent]["total_units"] += units
            stats["total_units"] = stats.get("total_units", 0.0) + units
            stats["sessions_tracked"] = stats.get("sessions_tracked", 0) + 1

        save_stats(stats)

        # Varning om tröskel överskrids
        if session_units >= ESCALATE_ESTIMATED_UNITS:
            top = sorted(
                stats["agents"].items(),
                key=lambda x: x[1]["total_units"],
                reverse=True
            )[:3]
            top_str = ", ".join(f"@{a}={int(v['total_units'])}u" for a, v in top)
            print(
                f"[EKONOMEN] 🔴 HÖG FÖRBRUKNING: ~{int(session_units)} enheter denna session "
                f"— kör /usage för faktisk fakturering. Dyraste totalt: {top_str}"
            )
        elif session_units >= WARN_ESTIMATED_UNITS:
            print(
                f"[EKONOMEN] ⚠️ FÖRBRUKNING: ~{int(session_units)} enheter denna session "
                f"— kör /usage för faktisk fakturering"
            )

    except Exception:
        pass


if __name__ == "__main__":
    main()
