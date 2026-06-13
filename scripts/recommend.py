"""Sessionsrekommendationer för CNS — regelbaserat lager ovanpå datalagret.

Läser idé-inkorgen (lokalt), quests/issues (GitHub, graceful degrade) och
sessioner, och föreslår vilken standardiserad sessionstyp som bör startas
härnäst. Sessionstyperna definieras i ``sessions/profiles/<typ>.md``.

Två konsumenter:
  - ``--statusline`` — kompakt enrading för Claude Codes statusrad.
    Får köras ofta ⇒ GitHub-delen cachas i ``exports/recommend_cache.json``
    (TTL) så statusraden aldrig hänger på nätet.
  - ``--json`` — full rekommendationslista för ``/sessions``-skillen.

Rent datalager-konsument: rör inte ``cns.py``, pushar inget.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # körbar både som modul och som fil (statusline)
    sys.path.insert(0, str(ROOT))

from scripts.idea_inbox import list_ideas  # noqa: E402
from scripts.session_store import list_sessions  # noqa: E402

EXPORTS_DIR = ROOT / "exports"
CACHE_FILE = EXPORTS_DIR / "recommend_cache.json"
CACHE_TTL_S = 300
PROFILES_DIR = ROOT / "sessions" / "profiles"

# Trösklar för triage-regeln
TRIAGE_IDEA_COUNT = 10
TRIAGE_UNTRIAGED_COUNT = 5

SESSION_TYPES = ("discovery", "definition", "delivery", "triage", "review", "enablement", "retro")


def _load_env() -> None:
    """Läs .env så issues_client får token även när vi körs utanför servern."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _fetch_quests() -> list[dict] | None:
    """Öppna quests (milestones) från GitHub; None = kunde inte nås."""
    try:
        _load_env()
        from scripts.issues_client import list_milestones

        return list_milestones(state="open")
    except Exception:
        return None


def _cached_quests() -> list[dict] | None:
    """Quests via TTL-cache så statusraden inte gör nätanrop varje rendering."""
    try:
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if time.time() - cache.get("fetched_at", 0) < CACHE_TTL_S:
            return cache.get("quests")
    except Exception:
        pass
    quests = _fetch_quests()
    if quests is not None:
        try:
            EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(
                json.dumps({"fetched_at": time.time(), "quests": quests}),
                encoding="utf-8",
            )
        except Exception:
            pass
    return quests


def gather_state() -> dict:
    """Samla underlaget: idéer (lokalt), quests (cache/GitHub), sessioner."""
    try:
        ideas = list_ideas(status="open")
    except Exception:
        ideas = []
    try:
        running = list_sessions(status="running")
    except Exception:
        running = []
    return {
        "ideas": ideas,
        "quests": _cached_quests(),  # None ⇒ quest-reglerna hoppar över sig själva
        "running_sessions": running,
    }


def recommend(state: dict | None = None) -> list[dict]:
    """Regelbaserade rekommendationer, sorterade på poäng (högst först).

    Varje post: {type, title, motivation, refs, score}. Reglerna är medvetet
    enkla och deterministiska — agent-driven förfining sker i /sessions-skillen
    ovanpå denna lista, inte här.
    """
    state = state or gather_state()
    ideas = state["ideas"]
    quests = state["quests"]
    recs: list[dict] = []

    untriaged = [i for i in ideas if not i.get("slug")]
    if len(ideas) >= TRIAGE_IDEA_COUNT or len(untriaged) >= TRIAGE_UNTRIAGED_COUNT:
        recs.append(
            {
                "type": "triage",
                "title": f"Triage: {len(ideas)} öppna idéer ({len(untriaged)} utan nod)",
                "motivation": "Idé-inkorgen har växt — resolva/promota/klustra innan den blir brus.",
                "refs": [i["id"] for i in ideas[:10]],
                "score": 40 + len(ideas),
            }
        )

    for quest in quests or []:
        open_issues = quest.get("open_issues", 0)
        closed_issues = quest.get("closed_issues", 0)
        ref = f"quest #{quest.get('number')}"
        if open_issues > 0:
            # Färsk quest (öppna issues, inget stängt än) → spec:a innan bygg.
            # Proxy, inte acceptance-medveten: vi har bara quest-aggregat här,
            # inte acceptanskriterier per issue (skulle kräva N+1-fetch i den
            # ofta körda statusraden). När bygget startar (issues stängs) tar
            # bygg-regeln nedan över.
            if closed_issues == 0:
                recs.append(
                    {
                        "type": "definition",
                        "title": f"Definition: \"{quest.get('title')}\" ({open_issues} issues, inget stängt än)",
                        "motivation": "Questen har issues men inget byggt — definiera vad/varför + acceptanskriterier innan delivery.",
                        "refs": [ref],
                        "score": 45 + open_issues,
                    }
                )
            recs.append(
                {
                    "type": "delivery",
                    "title": f"Delivery: \"{quest.get('title')}\" ({open_issues} öppna issues)",
                    "motivation": "Questen har definierat arbete som väntar på exekvering.",
                    "refs": [ref],
                    "score": 50 + open_issues,
                }
            )
        elif closed_issues > 0:
            recs.append(
                {
                    "type": "review",
                    "title": f"Review: \"{quest.get('title')}\" är 100 % klar men öppen",
                    "motivation": "Alla issues stängda — stäng questen eller fyll på med nästa steg.",
                    "refs": [ref],
                    "score": 60,
                }
            )

    direction_ideas = [
        i for i in ideas if "riktningsfråga" in i.get("text", "").lower()
    ]
    has_buildable_quest = any(q.get("open_issues", 0) > 0 for q in quests or [])
    if direction_ideas or (quests is not None and not has_buildable_quest):
        why = (
            "Öppna riktningsfrågor blockerar annat arbete."
            if direction_ideas
            else "Ingen quest har öppna issues — nästa spår behöver definieras."
        )
        recs.append(
            {
                "type": "discovery",
                "title": f"Discovery/planering ({len(direction_ideas)} riktningsfrågor)",
                "motivation": why,
                "refs": [i["id"] for i in direction_ideas],
                "score": 30 + 10 * len(direction_ideas),
            }
        )

    return sorted(recs, key=lambda r: r["score"], reverse=True)


# Emoji per sessionstyp för snabb visuell identifiering i statusraden
SESSION_ICONS: dict[str, str] = {
    "discovery": "🟣",
    "definition": "🟠",
    "delivery": "🟢",
    "triage": "🟡",
    "review": "🔵",
}


# ANSI-färg per sessionstyp (idea-2cc3ae24) — statusraden renderar ANSI.
# Ger varje typ en visuell identitet utöver emoji-ikonen.
SESSION_COLORS: dict[str, str] = {
    "discovery": "35",        # magenta  🟣
    "definition": "38;5;208", # orange   🟠
    "delivery": "32",         # grön     🟢
    "triage": "33",           # gul      🟡
    "review": "34",           # blå      🔵
    "enablement": "36",       # cyan
    "retro": "90",            # grå
}


def _colored(text: str, session_type: str | None) -> str:
    """Färga ``text`` med sessionstypens ANSI-färg (okänd typ → oförändrad)."""
    code = SESSION_COLORS.get(session_type or "")
    return f"\033[{code}m{text}\033[0m" if code else text


def _focus_label(session_id: str | None) -> str | None:
    """Läsbar fokus-etikett ur den aktiva sessionens ``link`` (vad man jobbar på).

    Fokus härleds ur markörens ``session_id`` → sessionens ``link`` — ingen separat
    fokusmarkör behövs för v1 (orienteringsyta, idea-7548a67a).
    """
    if not session_id:
        return None
    try:
        from scripts.session_store import get_session
        link = (get_session(session_id) or {}).get("link") or {}
    except Exception:
        return None
    kind, ref = link.get("kind"), link.get("ref")
    if not ref:
        return None
    return {
        "node": str(ref),
        "quest": f"quest #{ref}",
        "issue": f"#{ref}",
        "idea": f"idé {ref}",
    }.get(kind, str(ref))


# Session-boundary-signal (idea-fe8aa0bf): när kontextfönstret fylls blir passet
# dyrt/laggigt och tappar tråden → föreslå /compact (SAMMA fönster, ej ny chatt;
# kunskapen flushas ändå löpande till CNS). Tröskel i % kontextanvändning så den
# funkar oavsett 200k/1M-modell.
CONTEXT_COMPACT_THRESHOLD = 75


def _context_pct(stdin_json: dict | None) -> float | None:
    """Kontextanvändning i % ur Claude Codes statusLine-stdin (None om okänt/tidigt)."""
    try:
        cw = (stdin_json or {}).get("context_window") or {}
        pct = cw.get("used_percentage")
        return float(pct) if pct is not None else None
    except Exception:
        return None


def _compact_segment(ctx_pct: float | None) -> str | None:
    """Statusrads-segment som föreslår /compact när kontexten passerat tröskeln."""
    if ctx_pct is None or ctx_pct < CONTEXT_COMPACT_THRESHOLD:
        return None
    return f"\033[33m⚠ kontext {ctx_pct:.0f}% → /compact\033[0m"


def statusline(state: dict | None = None, ctx_pct: float | None = None) -> str:
    """Kompakt orienteringsrad för Claude Codes statusrad.

    Visar lägesbilden där man står — sessionstyp, fokus (vad man jobbar på),
    pågående pass och nästa rekommendation — så man slipper sätta ihop den
    själv ur flera datalager (orienteringsyta, idea-7548a67a).
    """
    state = state or gather_state()
    recs = recommend(state)

    # Aktiv markör: sessionstyp + vilket pass (vars link = fokus).
    try:
        from scripts.session_store import get_active
        marker = get_active() or {}
    except Exception:
        marker = {}
    active = marker.get("type")
    focus = _focus_label(marker.get("session_id"))

    # Aktiv routing (modell + agent) från router.py-sidfil
    try:
        routing_file = ROOT / "exports" / "active_routing.json"
        routing = json.loads(routing_file.read_text(encoding="utf-8")) if routing_file.exists() else {}
    except Exception:
        routing = {}

    if active:
        icon = SESSION_ICONS.get(active, "⚪")
        parts = [_colored(f"{icon} {active}", active)]
    else:
        parts = [f"💡 {len(state['ideas'])} idéer"]

    if focus:
        parts.append(f"📍 {focus}")

    if routing.get("model"):
        # Modell-ID:t bär redan familjeordet (claude-haiku-4-5 osv) — plocka ut det
        # i stället för att substituera versionssuffix (gav dubbletter som "haiku haiku").
        _m = routing["model"]
        model_short = next((f for f in ("opus", "sonnet", "haiku", "fable") if f in _m), _m.replace("claude-", ""))
        agent_part = f"@{routing['agent']}" if routing.get("agent") else ""
        parts.append(f"{model_short}{' · ' + agent_part if agent_part else ''}")

    running_sessions = state["running_sessions"]
    running = len(running_sessions)
    if running:
        parts.append(f"{running} pass igång")
    # Fantom-signal (issue #58): running-pass utan framsteg men med tokenförbrukning.
    try:
        from scripts.session_store import is_phantom
        phantoms = sum(1 for s in running_sessions if is_phantom(s))
    except Exception:
        phantoms = 0
    if phantoms:
        parts.append(f"\033[31m⚠ {phantoms} fantom\033[0m")
    # Härledd hälsa (degraded/attention) över pass + cachade epics — ingen nätrunda,
    # läser bara redan insamlat tillstånd. Degraderar tyst om health saknas.
    try:
        from scripts.health import health_for_session, health_for_milestone
        entities = [health_for_session(s) for s in running_sessions]
        entities += [health_for_milestone(q) for q in (state.get("quests") or [])]
        degraded = sum(1 for h in entities if h.get("level") == "degraded")
        attention = sum(1 for h in entities if h.get("level") == "attention")
    except Exception:
        degraded = attention = 0
    if degraded:
        parts.append(f"\033[31m⚠ {degraded} degraded\033[0m")
    if attention:
        parts.append(f"\033[33m▲ {attention} attention\033[0m")
    if recs:
        top = recs[0]
        more = f" (+{len(recs) - 1} — /sessions)" if len(recs) > 1 else ""
        parts.append(f"Rek: {_colored(top['type'], top['type'])}-session{more}")

    seg = _compact_segment(ctx_pct)
    if seg:
        parts.append(seg)
    return " · ".join(parts)


def main(argv: list[str]) -> int:
    # Windows-konsoler defaultar till cp1252 som inte klarar emoji/å-ä-ö.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "--statusline" in argv:
        # Claude Code matar statusLine-kommandot med sessions-JSON på stdin.
        # Vi läser context_window.used_percentage för /compact-signalen (idea-fe8aa0bf).
        ctx_pct = None
        try:
            if not sys.stdin.isatty():
                raw = sys.stdin.read()
                ctx_pct = _context_pct(json.loads(raw)) if raw.strip() else None
        except Exception:
            ctx_pct = None
        print(statusline(ctx_pct=ctx_pct))
        return 0
    state = gather_state()
    print(
        json.dumps(
            {
                "open_ideas": len(state["ideas"]),
                "running_sessions": len(state["running_sessions"]),
                "quests_reachable": state["quests"] is not None,
                "recommendations": recommend(state),
                "session_types": list(SESSION_TYPES),
                "profiles_dir": str(PROFILES_DIR),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
