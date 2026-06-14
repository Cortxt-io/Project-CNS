"""command_center_state — datakomponerare för Command Center (CNS orienteringsyta).

Militär doktrin (spec: cns-internal/plans/command-center-spec.md). Ren data, ingen
textual-import — testbar fristående, injicerbar (husmönstret från dispatch.py/board.py).
Komponerar BEFINTLIGA lager (milestones=Missioner, health=readiness, sessions=vem-agerar,
recommend=orders, board._build_unlocks=hävstång). Ingen ny datakälla. Degraderar tyst per källa.

Vokabulär: Mission=epic(milestone) · Objective=story(issue) · readiness=health · Unit=agent ·
Commander=du · Contact report=blockering · Order/FRAGO=nästa drag.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from scripts.board import PHASES, _build_unlocks

# health-nivå → readiness-doktrin
_READINESS = {"healthy": "operational", "attention": "watch", "degraded": "degraded", "unknown": "dark"}
# sorteringsvikt: degraded först (mest brådskande)
_READINESS_RANK = {"degraded": 0, "watch": 1, "operational": 2, "dark": 3}


def _as_int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _mission_issue_numbers(issues: list[dict]) -> set[int]:
    return {i["number"] for i in issues if i.get("number") is not None}


def _active_fronts(issue_numbers: set[int], sessions: list[dict]) -> list[str]:
    """Aktiva fronter (faser) för en Mission = typerna på RUNNING-pass länkade till dess
    objekt. MULTI-FAS (en Mission kan vara i flera fronter samtidigt, idea-dab230b2)."""
    seen: set[str] = set()
    for s in sessions:
        if s.get("status") != "running":
            continue
        link = s.get("link") or {}
        if link.get("kind") == "issue" and _as_int(link.get("ref")) in issue_numbers:
            t = s.get("type")
            if t in PHASES:
                seen.add(t)
    return [p for p in PHASES if p in seen]  # fas-ordning bevarad


def _units_on(issue_numbers: set[int], sessions: list[dict]) -> int:
    """Antal enheter (agent-pass) som kör på Missionens objekt just nu."""
    return sum(
        1
        for s in sessions
        if s.get("status") == "running"
        and (s.get("link") or {}).get("kind") == "issue"
        and _as_int((s.get("link") or {}).get("ref")) in issue_numbers
    )


def _contact_report(health: dict) -> str | None:
    """Rotorsak i klarspråk = första icke-friska health-checkens feedback."""
    for c in health.get("checks") or []:
        if c.get("level") in ("attention", "degraded"):
            return c.get("feedback") or c.get("name")
    return None


def _order_for(number: int, fronts: list[str], orders: list[dict]) -> str | None:
    """Order = den FRAGO (recommend) som pekar på denna Mission (quest #N), annars
    härledd ur aktiv front."""
    ref = f"quest #{number}"
    for o in orders:
        if ref in (o.get("refs") or []):
            otype = o.get("type")
            return f"{otype} → /session {otype}"
    if fronts:
        return f"{fronts[-1]} → /session {fronts[-1]}"
    return None


def command_center_state(
    *,
    milestones_fn: Callable[[], list[dict]] | None = None,
    issues_for_fn: Callable[[int], list[dict]] | None = None,
    all_open_issues_fn: Callable[[], list[dict]] | None = None,
    sessions_fn: Callable[[], list[dict]] | None = None,
    recommend_fn: Callable[[], list[dict]] | None = None,
    health_fn: Callable[..., dict] | None = None,
    now: datetime | None = None,
) -> dict:
    """Komponera Command Center i EN läsning. Ren data; degraderar tyst per källa.

    Returnerar: missions[] (sorterade degraded→operational, sen hävstång) · sitrep{readiness→antal} ·
    logistics[] (enablement-pass) · orders[] (FRAGO) · freshness.
    """
    now = now or datetime.now()

    if milestones_fn is None:
        from scripts.issues_client import list_milestones
        milestones_fn = lambda: list_milestones(state="open")  # noqa: E731
    if issues_for_fn is None:
        from scripts.issues_client import list_issues
        issues_for_fn = lambda n: list_issues(state="open", milestone=n)  # noqa: E731
    if all_open_issues_fn is None:
        from scripts.issues_client import list_issues
        all_open_issues_fn = lambda: list_issues(state="open")  # noqa: E731
    if sessions_fn is None:
        from scripts.session_store import list_sessions
        sessions_fn = lambda: list_sessions()  # noqa: E731
    if recommend_fn is None:
        from scripts.recommend import recommend
        recommend_fn = lambda: recommend()  # noqa: E731
    if health_fn is None:
        from scripts.health import health_for_milestone
        health_fn = health_for_milestone

    try:
        milestones = milestones_fn() or []
    except Exception:
        milestones = []
    try:
        sessions = sessions_fn() or []
    except Exception:
        sessions = []
    try:
        orders = recommend_fn() or []
    except Exception:
        orders = []
    try:
        unlocks = _build_unlocks(all_open_issues_fn() or [])
    except Exception:
        unlocks = {}

    missions: list[dict] = []
    for ms in milestones:
        number = ms.get("number")
        if number is None:
            continue
        try:
            issues = issues_for_fn(number) or []
        except Exception:
            issues = []
        try:
            health = health_fn(ms, now=now)
        except Exception:
            health = {"level": "unknown", "checks": []}
        readiness = _READINESS.get(health.get("level", "unknown"), "dark")
        nums = _mission_issue_numbers(issues)
        fronts = _active_fronts(nums, sessions)
        units = _units_on(nums, sessions)
        leverage = sum(unlocks.get(n, 0) for n in nums)
        missions.append(
            {
                "number": number,
                "title": ms.get("title", ""),
                "readiness": readiness,
                "fronts": fronts,                       # aktiva faser (multi)
                "units": units,                         # agent-pass igång
                "commander": units == 0 and readiness in ("watch", "degraded"),  # väntar på dig
                "contact": _contact_report(health) if readiness != "operational" else None,
                "order": _order_for(number, fronts, orders),
                "leverage": leverage,
                "open_objectives": ms.get("open_issues", len(issues)),
            }
        )

    missions.sort(key=lambda m: (_READINESS_RANK.get(m["readiness"], 9), -m["leverage"]))

    sitrep = {r: 0 for r in ("operational", "watch", "degraded", "dark")}
    for m in missions:
        sitrep[m["readiness"]] = sitrep.get(m["readiness"], 0) + 1

    logistics = [
        {"summary": s.get("summary", ""), "link": s.get("link")}
        for s in sessions
        if s.get("type") == "enablement" and s.get("status") == "running"
    ]

    return {
        "missions": missions,
        "sitrep": sitrep,
        "logistics": logistics,
        "orders": orders,
        "freshness": _freshness(),
    }


def _freshness() -> dict:
    import time

    try:
        import json

        from scripts import recommend as _rec

        cache = json.loads(_rec.CACHE_FILE.read_text(encoding="utf-8"))
        return {"reachable": True, "age_s": time.time() - cache.get("fetched_at", 0)}
    except Exception:
        return {"reachable": False, "age_s": None}
