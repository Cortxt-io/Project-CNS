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
    prs_fn: Callable[[], list[dict]] | None = None,
    infra_fn: Callable[[], dict] | None = None,
    verticals_fn: Callable[[], list[dict]] | None = None,
    now: datetime | None = None,
) -> dict:
    """Komponera Command Center i EN läsning. Ren data; degraderar tyst per källa.

    Returnerar: missions[] (sorterade degraded→operational, sen hävstång) · sitrep{readiness→antal} ·
    logistics[] (enablement-pass) · orders[] (FRAGO) · freshness.
    """
    now = now or datetime.now()

    if milestones_fn is None:
        # Missionerna läser samma recommend-cache som ORDERS (hybrid-källan i specen) så
        # FRONTLINE kommer till liv UTAN lokal GitHub-token. Faller tillbaka på live-hämtning.
        from scripts.recommend import _cached_quests

        def milestones_fn():
            cached = _cached_quests()
            if cached:
                return [q for q in cached if q.get("state") != "closed"]
            from scripts.issues_client import list_milestones
            return list_milestones(state="open")
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

    decisions = council_decisions(prs_fn)

    return {
        "missions": missions,
        "sitrep": sitrep,
        "logistics": logistics,
        "orders": orders,
        "command": {"dispatch": "IDLE", "decisions": len(decisions), "fobs": 0},
        "freshness": _freshness(),
        "infra": (infra_fn or _infra_health)(),
        "verticals": (verticals_fn or _verticals)(),
    }


def council_decisions(prs_fn: Callable[[], list[dict]] | None = None) -> list[dict]:
    """Väntande beslut för Council = öppna PR:er agenturen/dispatch producerat. Draft (väntar på
    'ready'/review) först, sen övriga öppna (väntar på merge). Degraderar tyst (ingen token → tom)."""
    if prs_fn is None:
        from scripts.prs_client import list_prs

        prs_fn = lambda: list_prs(state="open")  # noqa: E731
    try:
        prs = prs_fn() or []
    except Exception:
        return []
    prs.sort(key=lambda p: (not p.get("draft"), p.get("created_at", "")))
    return prs


def _freshness() -> dict:
    import time

    try:
        import json

        from scripts import recommend as _rec

        cache = json.loads(_rec.CACHE_FILE.read_text(encoding="utf-8"))
        return {"reachable": True, "age_s": time.time() - cache.get("fetched_at", 0)}
    except Exception:
        return {"reachable": False, "age_s": None}


_INFRA_CACHE_TTL_S = 300  # cockpit laddas ofta — cacha GitHub-rundan, överlev gunicorn-workers


def _infra_health() -> dict:
    """Deploy-/infra-hälsa: kör prod main HEAD?

    Jämför Railways auto-injicerade ``RAILWAY_GIT_COMMIT_SHA`` (körande commit) mot
    GitHub ``main`` HEAD, och hur gammal den körande committen är. Cachad (fil, TTL
    300s) så per-request-laddningar inte hamrar GitHub. Kastar aldrig — degraderar
    till ``unknown`` (aldrig falsk grön: så här kunde en 5-dygns frysning gömma sig).
    """
    import json
    import os
    import time
    from datetime import datetime, timezone
    from pathlib import Path

    from scripts.health import health_for_deploy

    cache_file = Path(__file__).resolve().parent.parent / "exports" / "infra_health_cache.json"
    try:
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        if time.time() - cached.get("checked_at", 0) < _INFRA_CACHE_TTL_S:
            return cached["infra"]
    except Exception:
        pass

    running = os.getenv("RAILWAY_GIT_COMMIT_SHA") or None
    main_sha = None
    gap_s = None
    try:
        import requests as req

        repo = os.getenv("GITHUB_REPO", "")
        token = os.getenv("CNS_GITHUB_TOKEN", "")
        if repo and token:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            base = f"https://api.github.com/repos/{repo}/commits"
            head = req.get(f"{base}/main", headers=headers, timeout=15)
            if head.status_code == 200:
                main_sha = head.json().get("sha")
            # Bara om prod ligger bakom behöver vi den körande committens ålder.
            if running and main_sha and running[:12] != main_sha[:12]:
                run = req.get(f"{base}/{running}", headers=headers, timeout=15)
                if run.status_code == 200:
                    date = run.json().get("commit", {}).get("committer", {}).get("date")
                    dt = datetime.fromisoformat(date.replace("Z", "+00:00")) if date else None
                    if dt is not None:
                        gap_s = (datetime.now(timezone.utc) - dt).total_seconds()
    except Exception:
        pass

    sc = health_for_deploy(running, main_sha, gap_seconds=gap_s)
    infra = {
        **sc,
        "running": running[:8] if running else None,
        "main_head": main_sha[:8] if main_sha else None,
        "behind_s": gap_s,
    }
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({"checked_at": time.time(), "infra": infra}), encoding="utf-8")
    except Exception:
        pass
    return infra


# ---------------------------------------------------------------------------
# Vertikaler — per-produkt läge + nästa steg (beskrivande, ej recept)
# ---------------------------------------------------------------------------

VERTICAL_STALE_DAYS = 7             # live men inga commits på > N dagar → driver/parkera-beslut
_VERTICALS_CACHE_TTL_S = 300


def _repo_slug(url_repo: str | None) -> str | None:
    """``https://github.com/Cortxt-io/juvahem`` → ``Cortxt-io/juvahem`` (annars None)."""
    if not url_repo or "github.com/" not in url_repo:
        return None
    return url_repo.rstrip("/").split("github.com/")[-1]


def _vertical_next_step(rec: dict) -> str:
    """Beskrivande nästa drag, härlett ur en vertikals signaler (INTE ett recept).

    Ren och IO-fri → testbar. Ordnad: ej-live slår allt, sen staleness, sen öppet arbete.
    """
    if not rec.get("url_live"):
        return "Skeppa/deploya MVP"
    age = rec.get("activity", {}).get("last_commit_age_s")
    if age is not None and age > VERTICAL_STALE_DAYS * 86400:
        return "Stale — besluta: driv eller parkera"
    if rec.get("open_issues"):
        top = rec.get("top_issue")
        return f"Bygg: {top}" if top else "Bygg öppna issues"
    return "Definiera nästa arbete / skaffa användare"


def _verticals() -> list[dict]:
    """Per-vertikal läge: deploy + aktivitet + öppet arbete + härlett nästa steg.

    En post per vertikal (katalognod där ``slug == domain`` och domänen ej cortxt).
    Signalerna hämtas cross-repo (vertikalerna är egna repon): deploy via Vercel-adaptern
    (``find_project(url_repo) → status``), aktivitet via ``eventstream`` (per-repo commits),
    öppet arbete via ``issues_client(repo=…)``. Cachad (fil, TTL 300s); kastar aldrig —
    varje signal degraderar tyst till unknown (aldrig falsk grön, samma princip som infra).
    """
    import json
    import time
    from datetime import datetime, timedelta, timezone
    from pathlib import Path

    cache_file = Path(__file__).resolve().parent.parent / "exports" / "verticals_cache.json"
    try:
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        if time.time() - cached.get("checked_at", 0) < _VERTICALS_CACHE_TTL_S:
            return cached["verticals"]
    except Exception:
        pass

    try:
        from scripts.catalog import load_catalog
        cat = load_catalog()
    except Exception:
        cat = {}

    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=30)).isoformat()
    out: list[dict] = []
    for slug, n in cat.items():
        dom = n.get("domain")
        if not dom or dom == "cortxt" or slug != dom:
            continue
        url_repo = n.get("url_repo") or ""
        repo = _repo_slug(url_repo)

        deploy = {"state": "unknown"}
        try:
            from scripts.adapters import vercel
            if url_repo and vercel.configured():
                proj = vercel.find_project(url_repo)
                if proj:
                    st = vercel.status(proj["id"])
                    if st.get("ok"):
                        deploy = {"state": st.get("state", "unknown")}
        except Exception:
            pass

        last_age = None
        try:
            if repo:
                from scripts.eventstream import fetch_github_commits
                commits = fetch_github_commits(since, repo=repo)
                if commits:
                    when = commits[0].get("when")
                    dt = datetime.fromisoformat(when.replace("Z", "+00:00")) if when else None
                    if dt is not None:
                        last_age = (now - dt).total_seconds()
                else:
                    last_age = 30 * 86400.0  # inga commits i 30-dagarsfönstret → minst 30d stale
        except Exception:
            pass

        open_issues, top_issue, milestones = 0, None, []
        try:
            if repo:
                from scripts.issues_client import list_issues, list_milestones
                issues = list_issues(state="open", repo=repo) or []
                open_issues = len(issues)
                if issues:
                    top_issue = issues[0].get("title")
                milestones = [m.get("title") for m in (list_milestones(state="open", repo=repo) or [])]
        except Exception:
            pass

        rec = {
            "slug": slug,
            "domain": dom,
            "title": n.get("title", slug),
            "url_live": n.get("url_live") or "",
            "url_repo": url_repo,
            "deploy": deploy,
            "activity": {"last_commit_age_s": last_age},
            "open_issues": open_issues,
            "top_issue": top_issue,
            "open_milestones": milestones,
        }
        rec["next_step"] = _vertical_next_step(rec)
        out.append(rec)

    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({"checked_at": time.time(), "verticals": out}), encoding="utf-8")
    except Exception:
        pass
    return out
