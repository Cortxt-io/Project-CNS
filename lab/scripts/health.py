"""Härledd hälso-scorecard för CNS-entiteter.

Hälsa **härleds** vid läsning ur objektiva signaler — den lagras aldrig och kan
därför aldrig bli stale (samma princip som ``catalog.derive_kind`` och
``session_store.is_phantom``). En handsatt status vore tvärtom det dyraste
felet: den motsägs tyst av verkligheten (research: dbt data-health,
"continuous context", RAG-best-practice — objektiva trösklar, inte omdöme).

En entitets hälsa = en **scorecard**: en komposition av namngivna *checks*
(Backstage Soundcheck-stil), var och en ``pass/fail/unknown`` med kort feedback
("varför + hur fixar jag"). Entitetsnivån = värsta check-nivån; ``unknown`` bara
om ingen check gav signal.

Vokabulär (4 nivåer, dbt data-health): ``healthy`` · ``attention`` · ``degraded``
· ``unknown``.

Modulen är transport-fri och importerar nedåt mot datalagren. Konsumenter:
``json_exporter`` (per-nod ``health`` i nodes.json), ``recommend`` (statusrad),
och det framtida kontrolltornet (renderar ``checks[]`` direkt).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# --- Vokabulär -------------------------------------------------------------

LEVELS = ("healthy", "attention", "degraded", "unknown")
_RANK = {"unknown": -1, "healthy": 0, "attention": 1, "degraded": 2}

# --- Färskhets-SLA per entitetstyp (olika ting blir stale olika fort) ------
# Tunables som modulkonstanter, samma konvention som
# ``session_store.PHANTOM_TOKEN_THRESHOLD`` och ``recommend.CACHE_TTL_S``.
SESSION_SLA_HOURS = 12      # running-pass tyst > 12h → attention
ISSUE_SLA_WEEKS = 2         # öppen issue, todos ej klara, > 2v → attention
EPIC_SLA_WEEKS = 4          # epic öppen, inget stängt, > 4v → attention
NODE_SLA_MONTHS = 6         # reserverad för ev. nod-ålderscheck
# Deploy-staleness: prod kör en annan commit än main HEAD. Korta avvikelser är
# normala (en deploy tar minuter), så bara en gammal avvikelse är degraded.
DEPLOY_LAG_ATTENTION_S = 1800     # < 30 min bakom → troligen en deploy som pågår
DEPLOY_LAG_DEGRADED_S = 3 * 3600  # > 3h bakom → prod stale, deployen kan ha failat


@dataclass
class Check:
    """En namngiven hälso-check: stabilt id, nivå, kort feedback."""

    name: str
    level: str
    feedback: str


def _rollup(checks: list[Check]) -> str:
    """Entitetsnivå = värsta check-nivån; unknown bara om alla är unknown.

    unknown får aldrig övertrumfa en riktig signal (``_RANK['unknown'] = -1``
    + filtrering före ``max``).
    """
    signal = [c for c in checks if c.level != "unknown"]
    if not signal:
        return "unknown"
    return max(signal, key=lambda c: _RANK[c.level]).level


def _scorecard(checks: list[Check]) -> dict:
    """Forma en lista checks till en scorecard-dict {level, checks:[...]}."""
    return {
        "level": _rollup(checks),
        "checks": [
            {"name": c.name, "level": c.level, "feedback": c.feedback} for c in checks
        ],
    }


def _parse_dt(value: str | None) -> datetime | None:
    """Tolka en ISO-tidsstämpel (med eller utan trailing 'Z') till naiv datetime.

    GitHub ger UTC med 'Z'; session_store ger lokal naiv isoformat. För SLA på
    timmar/veckor är den lilla UTC↔lokal-skillnaden försumbar, så vi normaliserar
    till naiv för att undvika aware/naive-subtraktionsfel.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None


def _age_hours(value: str | None, now: datetime) -> float | None:
    dt = _parse_dt(value)
    if dt is None:
        return None
    return (now - dt).total_seconds() / 3600.0


def _todo_ratio(todos: list[dict]) -> tuple[int, int]:
    """(klara, totalt) ur en todo/acceptans-lista av {done: bool}."""
    total = len(todos or [])
    done = sum(1 for t in (todos or []) if t.get("done"))
    return done, total


# ---------------------------------------------------------------------------
# Session / run
# ---------------------------------------------------------------------------

def check_phantom(session: dict) -> Check:
    """Fantom-arbete (running + tokenförbrukning men inga artefakter) ⇒ degraded."""
    try:
        from scripts.session_store import is_phantom
    except ImportError:
        return Check("phantom", "unknown", "Kan inte avgöra fantom-status.")
    if is_phantom(session):
        return Check(
            "phantom", "degraded",
            "Token-förbrukning utan artefakter — kör /save eller markera done.",
        )
    return Check("phantom", "healthy", "Producerar artefakter eller under tröskel.")


def check_session_staleness(session: dict, *, now: datetime, sla_hours: float = SESSION_SLA_HOURS) -> Check:
    """Running-pass utan uppdatering > SLA ⇒ attention."""
    if session.get("status") != "running":
        return Check("staleness", "unknown", "Inte ett pågående pass.")
    age = _age_hours(session.get("updated_at"), now)
    if age is None:
        return Check("staleness", "unknown", "Saknar tolkbar updated_at.")
    if age > sla_hours:
        return Check(
            "staleness", "attention",
            f"Pass igång {age:.0f}h utan uppdatering — heartbeat eller mark_done.",
        )
    return Check("staleness", "healthy", "Nyligen uppdaterat.")


def check_session_done(session: dict) -> Check:
    """Avslutat pass ⇒ healthy."""
    if session.get("status") == "done":
        return Check("done", "healthy", "Avslutat.")
    return Check("done", "unknown", "Inte avslutat.")


def health_for_session(session: dict, *, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    return _scorecard([
        check_phantom(session),
        check_session_staleness(session, now=now),
        check_session_done(session),
    ])


# ---------------------------------------------------------------------------
# Issue / story
# ---------------------------------------------------------------------------

def unmet_dependencies(issue: dict, closed_numbers: set[int]) -> list[int]:
    """Vilka depends_on som ännu inte är stängda (samma regel som dispatch)."""
    return [n for n in (issue.get("depends_on") or []) if n not in closed_numbers]


def check_blocked(issue: dict, closed_numbers: set[int]) -> Check:
    """Issue med ouppfyllda depends_on ⇒ degraded."""
    unmet = unmet_dependencies(issue, closed_numbers)
    if unmet:
        refs = ", ".join(f"#{n}" for n in sorted(unmet))
        return Check("blocked", "degraded", f"Blockerad av {refs} — stäng beroendena först.")
    return Check("blocked", "healthy", "Inga ouppfyllda beroenden.")


def check_partial_stale(issue: dict, *, now: datetime, sla_weeks: float = ISSUE_SLA_WEEKS) -> Check:
    """Öppen issue med ofullständiga todos äldre än SLA ⇒ attention."""
    if issue.get("state") != "open":
        return Check("partial_stale", "unknown", "Inte öppen.")
    done, total = _todo_ratio(issue.get("todos") or [])
    if total == 0 or done >= total:
        return Check("partial_stale", "healthy", "Inga öppna todos.")
    age = _age_hours(issue.get("created_at"), now)
    if age is None:
        return Check("partial_stale", "unknown", "Saknar tolkbar created_at.")
    if age > sla_weeks * 7 * 24:
        return Check(
            "partial_stale", "attention",
            f"Öppen {age / (7 * 24):.0f}+ veckor, todos ej klara ({done}/{total}).",
        )
    return Check("partial_stale", "healthy", f"Pågår ({done}/{total} todos).")


def check_acceptance(issue: dict) -> Check:
    """Acceptanskriterier alla klara men issue öppen ⇒ attention (stäng den)."""
    criteria = issue.get("acceptance_criteria") or []
    if not criteria:
        return Check("acceptance", "unknown", "Inga acceptanskriterier definierade.")
    done, total = _todo_ratio(criteria)
    if done >= total and issue.get("state") == "open":
        return Check(
            "acceptance", "attention",
            "Acceptanskriterier klara men issue öppen — stäng den.",
        )
    return Check("acceptance", "healthy", f"Acceptans {done}/{total}.")


def health_for_issue(issue: dict, *, closed_numbers: set[int] | None = None, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    closed_numbers = closed_numbers or set()
    return _scorecard([
        check_blocked(issue, closed_numbers),
        check_partial_stale(issue, now=now),
        check_acceptance(issue),
    ])


# ---------------------------------------------------------------------------
# Epic / milestone
# ---------------------------------------------------------------------------

def check_epic_stalled(ms: dict, *, now: datetime, sla_weeks: float = EPIC_SLA_WEEKS) -> Check:
    """Epic startad (öppna issues) men inget stängt på > SLA ⇒ attention."""
    open_n = ms.get("open_issues", 0) or 0
    closed_n = ms.get("closed_issues", 0) or 0
    if not (open_n > 0 and closed_n == 0):
        return Check("epic_stalled", "healthy", "Har rörelse eller är tom.")
    age = _age_hours(ms.get("created_at"), now)
    if age is None:
        return Check("epic_stalled", "unknown", "Saknar tolkbar created_at.")
    if age > sla_weeks * 7 * 24:
        return Check(
            "epic_stalled", "attention",
            f"Epic startad men inget stängt på {age / (7 * 24):.0f} veckor.",
        )
    return Check("epic_stalled", "healthy", "Nystartad epic.")


def check_bookkeeping_lag(ms: dict) -> Check:
    """Billig proxy för bokföringssläp: alla issues klara men epic öppen ⇒ attention.

    Den djupa detektorn (merged-PR-vs-öppen-issue) kräver N+1 PR-fetch och är för
    dyr för read-time — den är ett eget follow-up-issue.
    """
    total = (ms.get("open_issues", 0) or 0) + (ms.get("closed_issues", 0) or 0)
    if total == 0:
        return Check("bookkeeping_lag", "unknown", "Epic utan issues.")
    if ms.get("progress") == 1.0 and ms.get("state") == "open":
        return Check(
            "bookkeeping_lag", "attention",
            "Alla issues klara men epic öppen — stäng epicen (bokföringssläp).",
        )
    return Check("bookkeeping_lag", "healthy", "Progress speglar tillståndet.")


def check_milestone_staleness(ms: dict, *, now: datetime, sla_weeks: float = EPIC_SLA_WEEKS) -> Check:
    """Milstolpe utan aktivitet > SLA ⇒ attention. unknown om updated_at saknas."""
    age = _age_hours(ms.get("updated_at"), now)
    if age is None:
        return Check("milestone_staleness", "unknown", "Saknar updated_at.")
    if age > sla_weeks * 7 * 24:
        return Check(
            "milestone_staleness", "attention",
            f"Ingen aktivitet på {age / (7 * 24):.0f} veckor.",
        )
    return Check("milestone_staleness", "healthy", "Nyligen rörd.")


def health_for_milestone(ms: dict, *, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    return _scorecard([
        check_epic_stalled(ms, now=now),
        check_bookkeeping_lag(ms),
        check_milestone_staleness(ms, now=now),
    ])


# ---------------------------------------------------------------------------
# Initiativ (roll-up av epic-hälsa)
# ---------------------------------------------------------------------------

def health_for_initiative(initiative_name: str, milestones: list[dict], *, now: datetime | None = None) -> dict:
    """Initiativ-hälsa = värsta hälsan bland dess epics. Ingen egen signal."""
    now = now or datetime.now()
    children = [m for m in (milestones or []) if m.get("initiative") == initiative_name]
    checks = [
        Check(
            name=f"epic:{m.get('number')}",
            level=health_for_milestone(m, now=now)["level"],
            feedback=m.get("title", ""),
        )
        for m in children
    ]
    if not checks:
        return _scorecard([Check("rollup", "unknown", "Inga epics under initiativet.")])
    return _scorecard(checks)


# ---------------------------------------------------------------------------
# Nod / system
# ---------------------------------------------------------------------------

def check_node_issue_rollup(slug: str, issues: list[dict], *, now: datetime | None = None) -> Check:
    """Nod-hälsa ur dess öppna issues: värsta issue-nivån bubblar upp."""
    now = now or datetime.now()
    closed = {i.get("number") for i in (issues or []) if i.get("state") == "closed"}
    mine = [i for i in (issues or []) if i.get("node_slug") == slug and i.get("state") == "open"]
    if not mine:
        return Check("issue_rollup", "unknown", "Inga öppna issues på noden.")
    worst = "healthy"
    for issue in mine:
        lvl = health_for_issue(issue, closed_numbers=closed, now=now)["level"]
        if _RANK.get(lvl, -1) > _RANK[worst]:
            worst = lvl
    return Check("issue_rollup", worst, f"{len(mine)} öppna issues; värst: {worst}.")


def check_node_structural(slug: str, systems: dict | None = None) -> Check:
    """Katalog-validering för noden: fel ⇒ degraded, varning ⇒ attention."""
    try:
        from scripts.validator import validate_catalog
        errors, warnings = validate_catalog(systems)
    except Exception:
        return Check("structural", "unknown", "Kunde inte validera katalogen.")
    prefix = f"{slug}:"
    my_errors = [e for e in errors if e.startswith(prefix)]
    my_warnings = [w for w in warnings if w.startswith(prefix)]
    if my_errors:
        return Check("structural", "degraded", f"Katalogfel: {my_errors[0]}")
    if my_warnings:
        return Check("structural", "attention", f"Katalogvarning: {my_warnings[0]}")
    return Check("structural", "healthy", "Katalogvalidering ren.")


def health_for_node(slug: str, *, issues: list[dict] | None = None, systems: dict | None = None, now: datetime | None = None) -> dict:
    """Nod-hälsa = roll-up av öppna issues + strukturell katalog-check.

    Livscykel/mognad (de pensionerade stage/status-enumsen) är en SEPARAT axel
    och medvetet INTE en hälso-check.
    """
    now = now or datetime.now()
    return _scorecard([
        check_node_issue_rollup(slug, issues or [], now=now),
        check_node_structural(slug, systems),
    ])


# ---------------------------------------------------------------------------
# Deploy / infra (prod vs main HEAD)
# ---------------------------------------------------------------------------

def check_deploy_staleness(
    running_sha: str | None,
    main_head_sha: str | None,
    gap_seconds: float | None,
) -> Check:
    """Kör prod main HEAD? Annars: hur länge har den varit bakom?

    Ren och IO-fri (jämför SHA + ålder) så den är testbar; `_infra_health` i
    ``command_center`` gör nätrundan och matar in värdena. Saknad SHA / onåbar
    källa ⇒ ``unknown`` (aldrig en falsk grön — det var precis så en 5-dygns
    frysning kunde gömma sig bakom "allt operativt").
    """
    if not running_sha or not main_head_sha:
        return Check("deploy_staleness", "unknown",
                     "Kan inte avgöra deploy-läge (saknar körande SHA eller main HEAD).")
    if running_sha[:12] == main_head_sha[:12]:
        return Check("deploy_staleness", "healthy", "Prod kör main HEAD.")
    behind = f" ({int(gap_seconds // 3600)}h bakom)" if gap_seconds else ""
    if gap_seconds is not None and gap_seconds >= DEPLOY_LAG_DEGRADED_S:
        return Check("deploy_staleness", "degraded",
                     f"Prod stale — kör inte main{behind}; senaste deployen kan ha failat. "
                     "Kolla Railway Deployments-loggen.")
    return Check("deploy_staleness", "attention",
                 f"Prod ligger bakom main{behind} — troligen en deploy som pågår.")


def health_for_deploy(
    running_sha: str | None,
    main_head_sha: str | None,
    *,
    gap_seconds: float | None = None,
) -> dict:
    """Scorecard för prod-deployens färskhet (körande commit vs main HEAD)."""
    return _scorecard([check_deploy_staleness(running_sha, main_head_sha, gap_seconds)])
