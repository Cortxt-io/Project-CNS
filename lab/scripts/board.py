"""board_state — delad datakomponerare för Control Tower (fas-kolumn-aktivitetstavla).

Ren data, ingen textual/React-import — testbar fristående och renderbar av både TUI
(`scripts/tui`) och webben (`/api/board`). En datakälla, två renderingar (spec:
`cns-internal/plans/control-tower-spec.md`). Komponerar BEFINTLIGA lager (issues,
sessioner, recommend, health) — ingen ny datakälla.

Injicerbar (husmönstret från `dispatch.py`): alla hämtare kan stoppas in för test utan
GitHub/nätverk. Defaultar till de riktiga klienterna och degraderar tyst per källa.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

# Fas-kolumnerna vänster→höger (livscykeln). Enablement är INTE en kolumn — den är ett
# parallellt spår. Speglar session_store.VALID_SESSION_TYPES minus enablement.
PHASES: list[str] = ["triage", "discovery", "definition", "delivery", "review", "retro"]

# WIP-tak per fas (forskningsrevidering: constraints/pull drar arbete vidare, inte passiv
# synlighet). None = inget tak. Delivery är den fas Rikard fastnar i → hårdast tak.
WIP_CAPS: dict[str, int | None] = {
    "triage": None,
    "discovery": 2,
    "definition": 2,
    "delivery": 3,
    "review": None,
    "retro": None,
}

# En länkad session äldre än detta räknas som ett inaktuellt underlag för fas-härledningen
# (synlig "stale"-markering, inte tyst fallback — dbt/Soundcheck/DORA-mönstret).
PHASE_STALE_HOURS = 12.0


def _age_hours(iso: str | None, now: datetime) -> float | None:
    if not iso:
        return None
    try:
        return (now - datetime.fromisoformat(iso)).total_seconds() / 3600
    except Exception:
        return None


def _explicit_phase(labels: list[str]) -> str | None:
    """Explicit `phase:<type>`-label överstyr härledningen (F1-hybrid)."""
    for lab in labels or []:
        if lab.startswith("phase:"):
            val = lab.split(":", 1)[1].strip()
            if val in PHASES:
                return val
    return None


def _explicit_leverage(labels: list[str]) -> int | None:
    """Explicit strategisk vikt `leverage:<1-5>` (bedömd term, default neutral när saknas)."""
    for lab in labels or []:
        if lab.startswith("leverage:"):
            try:
                return max(1, min(5, int(lab.split(":", 1)[1].strip())))
            except (ValueError, IndexError):
                return None
    return None


def _sessions_for_issue(number: int, sessions: list[dict]) -> list[dict]:
    """Sessioner länkade till issuen (link.kind=issue, link.ref=number), nyast först."""
    ref = str(number)
    linked = [
        s for s in sessions
        if (s.get("link") or {}).get("kind") == "issue"
        and str((s.get("link") or {}).get("ref")) == ref
    ]
    linked.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return linked


def _derive_phase(card_number: int, labels: list[str], sessions: list[dict], now: datetime) -> tuple[str, bool, bool]:
    """(phase, explicit, stale) per F1: explicit label överstyr; annars senaste länkade
    sessionens typ; annars TRIAGE. Stale om härledd ur ett inaktuellt pass."""
    explicit = _explicit_phase(labels)
    if explicit:
        return explicit, True, False
    linked = _sessions_for_issue(card_number, sessions)
    for s in linked:
        stype = s.get("type")
        if stype in PHASES:
            age = _age_hours(s.get("updated_at") or s.get("created_at"), now)
            stale = age is not None and age >= PHASE_STALE_HOURS
            return stype, False, stale
    return "triage", False, False


def _who_acts(card_number: int, sessions: list[dict], health_level: str) -> str | None:
    """⚠ väntar på dig vs 🟢 agent jobbar. Running-länkat pass → agent; annars driver
    health (degraded/attention → dig). Horvitz: markören operationaliserar initiativ."""
    linked = _sessions_for_issue(card_number, sessions)
    if any(s.get("status") == "running" for s in linked):
        return "agent"
    if health_level in ("degraded", "attention"):
        return "you"
    return None


def _build_unlocks(cards_raw: list[dict]) -> dict[int, int]:
    """Reverse depends_on-graf: number → antal andra öppna objekt som (transitivt) väntar
    på det. Avblockerings-hävstången (a) — ren WSJF missar denna."""
    direct: dict[int, set[int]] = {}  # number → de som direkt beror på den
    by_number = {c["number"]: c for c in cards_raw if c.get("number") is not None}
    for c in cards_raw:
        for dep in c.get("depends_on") or []:
            if dep in by_number:
                direct.setdefault(dep, set()).add(c["number"])

    unlocks: dict[int, int] = {}
    for num in by_number:
        seen: set[int] = set()
        stack = list(direct.get(num, set()))
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(direct.get(n, set()))
        unlocks[num] = len(seen)
    return unlocks


def _leverage_score(unlocks: int, strategic: int, size: int, time_criticality: int) -> float:
    """WSJF-ekonomi + beroendegraf: (avblockering + strategiskt + tidskritikalitet) / storlek.
    Storleks-nämnaren ger shortest-job-first; saknade bedömda termer = neutrala (1)."""
    return (unlocks + strategic + time_criticality) / max(1, size)


def board_state(
    *,
    issues_fn: Callable[[], list[dict]] | None = None,
    closed_numbers_fn: Callable[[], set[int]] | None = None,
    sessions_fn: Callable[[], list[dict]] | None = None,
    recommend_fn: Callable[[], list[dict]] | None = None,
    health_fn: Callable[..., dict] | None = None,
    now: datetime | None = None,
) -> dict:
    """Komponera fas-kolumn-tavlan i EN läsning. Ren data; degraderar tyst per källa.

    Returnerar:
      phases · columns{phase→{cards,count,wip_cap,over_wip}} · enablement[] ·
      nudges[] · pulse{phase→count} · freshness.
    """
    now = now or datetime.now()

    # Lazy default-wiring (undvik import vid varje cns-anrop, samma som cockpit_state).
    if issues_fn is None:
        from scripts.issues_client import list_issues
        issues_fn = lambda: list_issues(state="open")  # noqa: E731
    if closed_numbers_fn is None:
        def closed_numbers_fn() -> set[int]:
            from scripts.issues_client import list_issues
            return {i["number"] for i in list_issues(state="closed") if i.get("number")}
    if sessions_fn is None:
        from scripts.session_store import list_sessions
        sessions_fn = lambda: list_sessions()  # noqa: E731
    if recommend_fn is None:
        from scripts.recommend import recommend
        recommend_fn = lambda: recommend()  # noqa: E731
    if health_fn is None:
        from scripts.health import health_for_issue
        health_fn = health_for_issue

    try:
        cards_raw = issues_fn() or []
    except Exception:
        cards_raw = []
    try:
        closed_numbers = closed_numbers_fn() or set()
    except Exception:
        closed_numbers = set()
    try:
        sessions = sessions_fn() or []
    except Exception:
        sessions = []
    try:
        nudges = recommend_fn() or []
    except Exception:
        nudges = []

    unlocks = _build_unlocks(cards_raw)

    columns: dict[str, dict] = {p: {"cards": [], "count": 0, "wip_cap": WIP_CAPS.get(p), "over_wip": False} for p in PHASES}

    for raw in cards_raw:
        number = raw.get("number")
        if number is None:
            continue
        labels = raw.get("labels") or []
        try:
            health = health_fn(raw, closed_numbers=closed_numbers, now=now)
        except Exception:
            health = {"level": "unknown", "checks": []}
        phase, explicit, stale = _derive_phase(number, labels, sessions, now)
        todos = raw.get("todos") or []
        acc = raw.get("acceptance_criteria") or []
        size = max(1, len(todos) + len(acc))
        strategic = _explicit_leverage(labels) or 1  # bedömd term, neutral när osatt
        time_criticality = 1  # seam: härleds ur SLA/deadline senare; neutral i v1
        unlock_n = unlocks.get(number, 0)
        card = {
            "number": number,
            "title": raw.get("title", ""),
            "type": raw.get("type") or "story",
            "epic": raw.get("quest"),
            "node_slug": raw.get("node_slug"),
            "phase": phase,
            "phase_explicit": explicit,
            "phase_stale": stale,
            "health": health.get("level", "unknown"),
            "who_acts": _who_acts(number, sessions, health.get("level", "unknown")),
            "depends_on": raw.get("depends_on") or [],
            "unlocks": unlock_n,
            "size": size,
            "progress": {"done": sum(1 for t in todos if t.get("done")), "total": len(todos)},
            "strategic": strategic,
            "leverage": _leverage_score(unlock_n, strategic, size, time_criticality),
        }
        columns[phase]["cards"].append(card)

    # Sortera kort inom varje kolumn på hävstång (vilket redo kort föreslås först).
    for p in PHASES:
        col = columns[p]
        col["cards"].sort(key=lambda c: (c["leverage"], c["unlocks"]), reverse=True)
        col["count"] = len(col["cards"])
        cap = col["wip_cap"]
        col["over_wip"] = cap is not None and col["count"] > cap

    # Enablement-spår: running/öppna enablement-sessioner, separat (inte en kolumn).
    enablement = [
        {
            "summary": s.get("summary", ""),
            "status": s.get("status"),
            "link": s.get("link"),
        }
        for s in sessions
        if s.get("type") == "enablement" and s.get("status") == "running"
    ]

    pulse = {p: columns[p]["count"] for p in PHASES}

    return {
        "phases": PHASES,
        "columns": columns,
        "enablement": enablement,
        "nudges": nudges,
        "pulse": pulse,
        "freshness": _freshness(),
    }


def _freshness() -> dict:
    """Färskhetsmarkör ur recommend-cachen (samma källa som cockpit_state)."""
    import time

    try:
        import json

        from scripts import recommend as _rec

        cache = json.loads(_rec.CACHE_FILE.read_text(encoding="utf-8"))
        return {"reachable": True, "age_s": time.time() - cache.get("fetched_at", 0)}
    except Exception:
        return {"reachable": False, "age_s": None}
