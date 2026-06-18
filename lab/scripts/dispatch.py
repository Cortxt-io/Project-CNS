"""Dispatch-loop (issue #59, Fas 3) — agenturens puls i ÖVERVAKAD CRAWL-form.

Plockar EN lämplig issue → claim → route till roll → kör ETT pass via agent_host
→ stannar för människa vid varje muterande grind (föreslå-sen-utför). Crawl:
inget muterande sker utan att en injicerad ``approve``-callback säger ja; default
NEKAR allt. Bounded: en issue per varv, ingen fan-out, ingen parallellism.

**Komponerar befintliga primitiver — bygger inga nya:**
  - ``issues_client.list_issues`` / ``get_issue``     — kandidater, depends_on, typ, DoD
  - ``lease_store.claim`` / ``release`` / ``get_lease`` — atomiskt plock, orphan-TTL
  - ``agent_roles.role_for_node`` (→ ``agentur_routing.route``) — route → roll + modell
  - ``agent_guardrails.check_session_overlap``        — cns-sync (dubbelarbete)
  - ``agent_eval.evaluate``                           — eval-grind före done (#57)
  - ``session_store`` start/mark_done/record_metrics  — bokföring + observabilitet (#58)
  - ``scripts.tui.agent_host.run_turn``               — kör passet roll-medvetet

**Designval (öppen fråga i pickup-briefen):** lokal ``agent_host``-loop, inte
@claude-molntransport — roll-medvetenheten (rätt identitet/modell per nod) finns
redan lokalt; molnet kör generisk Claude. PR-/transportsteget hålls ändå
injicerbart (``open_pr_fn``) så @claude eller en annan yta kan wiras senare utan
att röra crawl-logiken.

**Crawl v1 = föreslå-sen-utför:** arbetspasset körs READ-FIRST (förslag, inga
skrivningar) under Guardrails. Det muterande steget — skriva kod + öppna draft-PR
— är en separat, människa-godkänd grind (``open_pr_fn``, default ej wirad). Så
"aldrig auto-merge" hålls trivialt: crawlen kan i sig inte ens öppna en PR utan en
godkänd approver + injicerad transport. Worktree-isolering hör till den grinden
(när passet får skriva), inte till read-first-förslaget.

Ren, injicerbar logik (samma mönster som ``agent_eval``/``agentur_routing``): allt
I/O går via injicerbara beroenden så crawlen testas utan GitHub/Redis/LLM/SDK.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# --- Lämplighetspolicy (steg 1: hoppa diffusa/feature-tunga) -----------------
# Typer som per default anses avgränsade nog för autonom dispatch i crawl.
SUITABLE_TYPES = {"bug", "chore", "spike"}
# 'story' släpps bara igenom med litet scope (få öppna todos) — annars feature-tung.
MAX_STORY_TODOS = 5

# Crawl-grindar (muterande steg som kräver människa-godkännande).
ACTION_CLAIM = "claim"
ACTION_RUN = "run_pass"
ACTION_OPEN_PR = "open_pr"
ACTION_MERGE = "merge"  # Fas 5: self-merge av lågrisk-PR (annars eskalering)

# Eval-kontext för dispatch-körda pass (#124): domaren ska bedöma agentens KOD/ARBETE,
# inte straffa processkriterier som LOOPEN äger. I dispatch-flödet skriver agenten bara
# kod i en isolerad worktree; dispatchern committar, öppnar draft-PR + kopplar den till
# issuen EFTER passet. Annars failar varje pass kriterier som "skapar alltid PR".
DISPATCH_EVAL_CONTEXT = (
    "Detta pass kördes av dispatch-loopen. AGENTEN skrev BARA kod i en isolerad "
    "git-worktree. Dispatch-loopen (INTE agenten) committar ändringarna, öppnar en "
    "draft-PR och kopplar den till issuen EFTER detta pass. Bedöm därför agentens "
    "KOD och ARBETE mot kriterierna. Kriterier som handlar om att SKAPA en PR, koppla "
    "PR till issue, eller merga hanteras av loopen och ska räknas som UPPFYLLDA så länge "
    "agentens kodarbete är korrekt — straffa inte agenten för det loopen äger."
)

# --- Autonomi-policy (Fas 5, #61 + #60 merge-beslutspolicy) ------------------
# "Self-merge bara lågrisk" (beslut Rikard): loopen får merga TESTAD/ADDITIV/lågrisk
# (docs/deps/tooling) men ALDRIG feature-kod, schema-brott eller produktions-vägar —
# de eskaleras till människa. Allowlist är POSITIV (whitelist) = konservativ default:
# bara det som matchar räknas som lågrisk, allt annat eskalerar. Glesa upp vid behov.
LOW_RISK_GLOBS = (
    "docs/", "plans/", "decisions/", "tests/", ".claude/", "skills/",
    "requirements", "README", ".md",  # docs/deps (suffix/prefix-match nedan)
)
# Vägar som ALLTID eskalerar oavsett allowlist (produktion/schema/connector-kontrakt).
ESCALATE_GLOBS = (
    "app/server.py", "app/asgi.py", "app/mcp_server.py", "app/tools/",
    "schemas/", "enums.json", "catalog.yaml", "nodes/", ".github/", "Procfile",
)


# ---------------------------------------------------------------------------
# Steg 1 — lämplighetsbedömning
# ---------------------------------------------------------------------------


@dataclass
class Suitability:
    """Utfall av lämplighetsbedömningen för EN issue."""

    suitable: bool
    reason: str


def assess_suitability(issue: dict, *, closed_numbers: set[int]) -> Suitability:
    """Är issuen lämplig att dispatcha autonomt i crawl? (suitable, skäl).

    Hoppar: ej öppna; ouppfyllda ``depends_on`` (dep-issue ej stängd); diffusa (saknar
    både todos och acceptanskriterier ⇒ ingen tydlig DoD); feature-tunga stories (för
    många öppna todos). ``bug``/``chore``/``spike`` med tydlig DoD släpps igenom.
    """
    if issue.get("state") and issue.get("state") != "open":
        return Suitability(False, "ej öppen")

    unmet = [n for n in (issue.get("depends_on") or []) if n not in closed_numbers]
    if unmet:
        return Suitability(False, f"depends_on ouppfyllt: {sorted(unmet)}")

    open_todos = [t for t in (issue.get("todos") or []) if not t.get("done")]
    accept = issue.get("acceptance_criteria") or []
    if not open_todos and not accept:
        return Suitability(False, "diffus: saknar både todos och acceptanskriterier")

    itype = issue.get("type") or "story"
    if itype in SUITABLE_TYPES:
        return Suitability(True, f"typ '{itype}' med tydlig DoD")
    if itype == "story":
        if len(open_todos) > MAX_STORY_TODOS:
            return Suitability(
                False, f"feature-tung: {len(open_todos)} öppna todos > {MAX_STORY_TODOS}"
            )
        return Suitability(True, f"story med avgränsat scope ({len(open_todos)} öppna todos)")
    return Suitability(False, f"okänd/oavsedd typ '{itype}'")


def select_next_issue(
    candidates: list[dict],
    *,
    closed_numbers: set[int],
    is_claimable: Callable[[int], bool],
) -> tuple[Optional[dict], str]:
    """Första kandidaten som är BÅDE lämplig och claimbar (lease fri).

    Returnerar ``(issue, skäl)`` eller ``(None, skäl)``. Kandidatordningen är
    anroparens ansvar (t.ex. GitHubs öppna-issues-ordning) — crawlen tar den första
    som passerar grindarna, en i taget.
    """
    saw_suitable_but_held = False
    for issue in candidates:
        s = assess_suitability(issue, closed_numbers=closed_numbers)
        if not s.suitable:
            continue
        if not is_claimable(int(issue["number"])):
            saw_suitable_but_held = True
            continue
        return issue, s.reason
    if saw_suitable_but_held:
        return None, "lämpliga issues fanns men alla är redan claimade"
    return None, "ingen lämplig issue bland kandidaterna"


# ---------------------------------------------------------------------------
# Autonomi-policy (Fas 5) — self-merge bara lågrisk, annars eskalera
# ---------------------------------------------------------------------------


@dataclass
class RiskVerdict:
    """Risknivå för ett skrivpass: ``low`` = får self-mergas, ``escalate`` = människa."""

    level: str  # "low" | "escalate"
    reasons: list[str]


def _matches(path: str, globs: tuple[str, ...]) -> bool:
    """True om sökvägen matchar något mönster (prefix ELLER suffix, normaliserade \\→/)."""
    p = path.replace("\\", "/")
    return any(p.startswith(g) or p.endswith(g) for g in globs)


def classify_risk(
    issue: dict,
    changed_paths: list[str],
    *,
    eval_verdict: dict | None = None,
) -> RiskVerdict:
    """Avgör om ett skrivpass får self-mergas (lågrisk) eller måste eskaleras.

    "Self-merge bara lågrisk" (beslut Rikard, [[delegera-rutin-merge]]): mergas bara om
    ALLA ändrade filer ligger i ``LOW_RISK_GLOBS`` och INGEN i ``ESCALATE_GLOBS``, **OCH
    eval är GRÖN** (status ok + all_pass). Allt annat — feature-kod (scripts/app),
    schema/connector, produktion, eval som inte passerade/inte kördes, tomt — eskaleras.
    Ren funktion (testbar utan git/GitHub).
    """
    reasons: list[str] = []
    if not changed_paths:
        reasons.append("inga ändringar att merga")
    # Eval-gate (#112): self-merge KRÄVER en grön eval. Skipped/error/fail/saknad eval
    # ⇒ eskalera — autonomin får aldrig merga ett pass som inte bedömts mot DoD. Detta
    # stänger hålet där en ogated pass (t.ex. eval hoppad pga saknad nyckel) self-mergades.
    if not (eval_verdict and eval_verdict.get("status") == "ok" and eval_verdict.get("all_pass")):
        status = (eval_verdict or {}).get("status")
        reasons.append(f"eval ej grön (status={status!r}) — self-merge kräver passerad eval")
    # Skyddade vägar eskalerar alltid (produktion/schema/connector-kontrakt).
    escalate_hits = [p for p in changed_paths if _matches(p, ESCALATE_GLOBS)]
    if escalate_hits:
        reasons.append(f"rör skyddade vägar: {escalate_hits}")
    # Feature-kod: allt som INTE är på lågrisk-allowlistan.
    non_low = [
        p for p in changed_paths
        if not _matches(p, LOW_RISK_GLOBS) and p not in escalate_hits
    ]
    if non_low:
        reasons.append(f"icke-lågrisk-filer (feature-kod): {non_low}")
    return RiskVerdict("escalate" if reasons else "low", reasons)


# ---------------------------------------------------------------------------
# Crawl-orkestrering (steg 2–4) — en issue, gripbart steg för steg
# ---------------------------------------------------------------------------


def deny_all(action: str, context: dict) -> bool:
    """Default-approver i crawl: neka alla muterande steg (människa måste wira ja)."""
    return False


@dataclass
class CrawlResult:
    """Resultatet av ETT crawl-varv (en issue). ``journal`` = stegvis spår för människan."""

    status: str  # no-work | denied | blocked | ran | error
    issue: Optional[int] = None
    detail: str = ""
    session_id: Optional[str] = None
    eval: Optional[dict] = None
    pr: Optional[dict] = None
    journal: list[dict] = field(default_factory=list)

    def _log(self, step: str, ok: bool, detail: str = "") -> None:
        self.journal.append({"step": step, "ok": ok, "detail": detail})


def crawl_once(
    *,
    owner: str,
    candidates_fn: Callable[[], list[dict]],
    closed_numbers_fn: Callable[[], set[int]],
    approve: Callable[[str, dict], bool] = deny_all,
    run_pass: Optional[Callable[..., dict]] = None,
    is_claimable_fn: Optional[Callable[[int], bool]] = None,
    claim_fn: Optional[Callable[[int, str], dict]] = None,
    release_fn: Optional[Callable[[int, str], dict]] = None,
    overlap_fn: Optional[Callable[[Optional[str]], tuple[bool, list[dict]]]] = None,
    role_fn: Optional[Callable[[Optional[str], str], Optional[dict]]] = None,
    eval_fn: Optional[Callable[[str, str], dict]] = None,
    open_pr_fn: Optional[Callable[[dict, dict], dict]] = None,
    worktree_fn: Optional[Callable[[int], dict]] = None,
    commit_fn: Optional[Callable[[str, str], bool]] = None,
    cleanup_fn: Optional[Callable[[str], None]] = None,
    autonomy: bool = False,
    merge_fn: Optional[Callable[[dict, dict], dict]] = None,
    changed_paths_fn: Optional[Callable[[str], list[str]]] = None,
    should_abort: Optional[Callable[[], bool]] = None,
    session_store: Any = None,
) -> CrawlResult:
    """Kör ETT övervakat crawl-varv mot den första lämpliga+claimbara issuen.

    Sekvens: välj → [grind] claim → cns-sync → route→roll → [grind] kör pass → eval-grind
    (#57) → bokför session → [grind] draft-PR (om wirad). Varje muterande steg passerar
    ``approve(action, context)`` (default nekar). Lease + worktree släpps alltid i slutet
    (orphan-cleanup). ``should_abort`` är kill-switch: kollas mellan stegen.

    **Två pass-lägen styrt av ``worktree_fn``:**
      - ``None`` (default) → READ-FIRST-förslag: passet skriver inget, föreslår en diff i
        text. Säkrast; ``open_pr_fn`` är då bara en valfri vidarekoppling.
      - satt → SKRIV-läge: passet körs med skrivrätt i en isolerad git-worktree
        (``worktree_fn(number) → {path, branch}``), ändringarna committas (``commit_fn``),
        och ``open_pr_fn`` öppnar en DRAFT-PR. Worktree:t städas alltid (``cleanup_fn``).
        Fortfarande crawl: varje muterande steg gatas av ``approve`` och PR:n är aldrig
        auto-merge — skrivtröskeln passeras, autonomitröskeln (Fas 5) rörs inte.

    Alla beroenden injiceras (default = de riktiga modulerna) så varvet kan köras helt
    utan GitHub/Redis/LLM/SDK/git i test.
    """
    # Lazy default-bindning (modulerna ska inte krävas vid import/test).
    if session_store is None:
        from scripts import session_store as session_store  # type: ignore
    if is_claimable_fn is None or claim_fn is None or release_fn is None:
        from scripts import lease_store as _lease

        is_claimable_fn = is_claimable_fn or (lambda n: _lease.get_lease(n) is None)
        claim_fn = claim_fn or _lease.claim
        release_fn = release_fn or _lease.release
    if overlap_fn is None:
        from scripts.agent_guardrails import check_session_overlap

        overlap_fn = lambda slug: check_session_overlap(slug)  # noqa: E731
    if role_fn is None:
        from scripts.agent_roles import role_for_node

        role_fn = role_for_node
    if eval_fn is None:
        from scripts.agent_eval import evaluate

        eval_fn = lambda slug, output: evaluate(slug, output, context=DISPATCH_EVAL_CONTEXT)  # noqa: E731
    if run_pass is None:
        run_pass = _default_run_pass
    write_mode = worktree_fn is not None
    if write_mode and (commit_fn is None or cleanup_fn is None or changed_paths_fn is None):
        from scripts import worktree as _wt

        commit_fn = commit_fn or _wt.commit_all
        cleanup_fn = cleanup_fn or _wt.cleanup
        changed_paths_fn = changed_paths_fn or _wt.changed_paths

    res = CrawlResult(status="error")

    def aborted() -> bool:
        return bool(should_abort and should_abort())

    # --- Steg 1: välj ------------------------------------------------------
    candidates = candidates_fn()
    closed = closed_numbers_fn()
    issue, why = select_next_issue(
        candidates, closed_numbers=closed, is_claimable=is_claimable_fn
    )
    if issue is None:
        res.status, res.detail = "no-work", why
        res._log("select", False, why)
        return res
    number = int(issue["number"])
    slug = issue.get("node_slug")
    itype = issue.get("type") or "story"
    res.issue = number
    res._log("select", True, f"#{number} ({why})")

    if aborted():
        res.status, res.detail = "denied", "kill-switch före claim"
        return res

    claimed = False
    wt: Optional[dict] = None
    try:
        # --- Steg 2a: claim-grind -----------------------------------------
        if not approve(ACTION_CLAIM, {"issue": number, "slug": slug, "type": itype}):
            res.status, res.detail = "denied", "claim ej godkänt av människa"
            res._log(ACTION_CLAIM, False, "nekad")
            return res
        claim = claim_fn(number, owner)
        if not claim.get("claimed"):
            reason = claim.get("reason")
            # Fail-open (lease-lagrets kontrakt): Redis nere ⇒ lease degraderad, INTE
            # blockerad. Leasen finns bara för att hindra parallella pass att krocka;
            # solo/lokalt utan Redis finns ingen att koordinera med → kör vidare utan den.
            # 'redis-error' = transient fel, samma hantering. En upptagen lease (annan
            # owner, inget reason) är däremot en RIKTIG blockering.
            if reason in {"redis-unavailable", "redis-error"}:
                res._log(ACTION_CLAIM, True, f"lease degraderad ({reason}) — kör utan koordinering")
            else:
                res.status = "blocked"
                res.detail = f"#{number} redan claimad av {claim.get('owner')}"
                res._log(ACTION_CLAIM, False, res.detail)
                return res
        else:
            claimed = True
            res._log(ACTION_CLAIM, True, f"owner={owner}")

        # --- Steg 2b: cns-sync (dubbelarbete) -----------------------------
        clear, conflicting = overlap_fn(slug)
        if not clear:
            res._log(
                "cns-sync", False,
                f"{len(conflicting)} pass jobbar redan på '{slug}' — koordinera",
            )
        else:
            res._log("cns-sync", True, "fritt")

        # --- Steg 2c: route → roll ----------------------------------------
        role = role_fn(slug, itype) if slug else None
        agent_slug = (role or {}).get("slug")
        # Roll-lös-grind: routing gav ingen roll ⇒ ej dispatchbar i crawl. Utan roll finns
        # ingen modell och inga eval-kriterier, så ett generiskt pass kan ändå inte bedömas
        # (det blir ett tomt skal — orsaken till #95-felsöket). Vi litar på role_for_node-
        # seamet, INTE på nodmodellens filform: byggs CNS om ändras role_for_node, ej detta.
        if role is None:
            res.status = "blocked"
            res.detail = "ingen roll — routing gav inget (ej dispatchbar)"
            res._log("route", False, res.detail)
            return res
        res._log("route", True, f"roll={agent_slug} modell={role.get('model') or '?'}")

        if aborted():
            res.status, res.detail = "denied", "kill-switch före pass"
            return res

        # --- Steg 3: kör pass (grind) -------------------------------------
        # write_mode → skrivande pass i isolerad worktree; annars read-first-förslag.
        if not approve(
            ACTION_RUN,
            {"issue": number, "slug": slug, "agent": agent_slug, "write": write_mode},
        ):
            res.status, res.detail = "denied", "kör-pass ej godkänt av människa"
            res._log(ACTION_RUN, False, "nekad")
            return res

        cwd = None
        if write_mode:
            try:
                wt = worktree_fn(number)
            except Exception as exc:
                res.status = "error"
                res.detail = f"worktree-fel: {type(exc).__name__}: {exc}"
                res._log("worktree", False, res.detail)
                return res
            cwd = wt.get("path")
            res._log("worktree", True, f"branch={wt.get('branch')}")

        sess = session_store.start_session(
            link_kind="issue", link_ref=str(number),
            summary=f"dispatch crawl #{number}: {issue.get('title', '')}".strip(),
            source="code", session_type="delivery",
        )
        res.session_id = sess["id"]

        prompt = _build_pass_prompt(issue, write_mode=write_mode)
        try:
            outcome = run_pass(
                prompt=prompt, slug=slug, agent_slug=agent_slug,
                allow_writes=write_mode, cwd=cwd,
            )
        except Exception as exc:  # passet kraschade → släpp lease+worktree, lämna session running
            res.status = "error"
            res.detail = f"pass-fel: {type(exc).__name__}: {exc}"
            res._log(ACTION_RUN, False, res.detail)
            return res

        output = outcome.get("result") or ""
        metrics = outcome.get("metrics") or {}
        # Observabilitet (#58): bokför pass-metriker på sessionen.
        try:
            session_store.record_metrics(
                sess["id"],
                tokens_in=int(metrics.get("tokens", 0)),
                tools=None,
                artifact=None,
            )
        except Exception:
            pass
        res._log(ACTION_RUN, True, f"pass klart (turns={metrics.get('turns', '?')})")

        # --- Steg 3·ärlighet: tomt pass? --------------------------------
        # Agenten producerade inget förslag (tom output). Fira INTE detta som klart och
        # markera INTE sessionen done — lämna den running för retry/människa. (Detta var
        # #95: ett roll-löst pass såg "lyckat" ut trots turns=0 och tom output.)
        if not (output or "").strip():
            res.status = "ran"
            res.detail = f"tomt pass — agenten producerade inget förslag (turns={metrics.get('turns', 0)})"
            res._log("tomt-pass", False, "session lämnas running (ej done)")
            return res

        # --- Steg 3a: committa skrivpassets ändringar i worktree:t --------
        committed = False
        if write_mode:
            try:
                committed = commit_fn(wt["path"], f"dispatch #{number}: {issue.get('title', '')}".strip())
            except Exception as exc:
                res.status = "error"
                res.detail = f"commit-fel: {type(exc).__name__}: {exc}"
                res._log("commit", False, res.detail)
                return res
            res._log("commit", committed, "ändringar committade" if committed else "inga ändringar att committa")

        # --- Steg 3b: eval-grind (#57) före done --------------------------
        verdict = eval_fn(agent_slug, output) if agent_slug else {"status": "skipped", "reason": "ingen roll"}
        res.eval = verdict
        passed = verdict.get("all_pass")
        if verdict.get("status") == "skipped":
            res._log("eval", True, f"hoppad: {verdict.get('reason')}")
            session_store.mark_done(sess["id"], summary=f"crawl #{number}: förslag klart (eval hoppad)")
        elif passed:
            res._log("eval", True, f"{verdict.get('passed')}/{verdict.get('total')} pass")
            session_store.mark_done(sess["id"], summary=f"crawl #{number}: förslag klart, eval pass")
        else:
            res._log("eval", False, f"{verdict.get('passed')}/{verdict.get('total')} — sessionen lämnas running")
            res.status = "ran"
            res.detail = "eval-grind ej passerad — människa avgör"
            return res

        # --- Steg 4: draft-PR (grind; aldrig auto-merge) ------------------
        if write_mode and not committed:
            res.status, res.detail = "ran", "skrivpasset producerade inga ändringar — ingen PR"
            return res
        if open_pr_fn is None:
            res._log(ACTION_OPEN_PR, False, "PR-transport ej wirad (förslag väntar på människa)")
            res.status, res.detail = "ran", "förslag klart; draft-PR-steget ej wirat"
            return res
        if not approve(ACTION_OPEN_PR, {"issue": number, "slug": slug, "output": output}):
            res.status, res.detail = "ran", "draft-PR ej godkänd av människa"
            res._log(ACTION_OPEN_PR, False, "nekad")
            return res
        # Skrivpassets branch följer med via outcome["worktree"] så open_pr_fn kan pusha.
        pr = open_pr_fn(issue, {**outcome, "worktree": wt})  # förväntas: DRAFT-PR + reviewer
        res.pr = pr
        res._log(ACTION_OPEN_PR, True, f"draft-PR #{pr.get('number')}")

        # --- Steg 5: autonomi-merge (Fas 5) — bara LÅGRISK self-mergas ----
        # Av som default (crawl): draft-PR lämnas för människa. Slås autonomy på mergas
        # bara testad/additiv/lågrisk; feature-kod/schema/produktion/eval-fall eskaleras.
        if not (autonomy and merge_fn):
            res.status, res.detail = "ran", f"draft-PR #{pr.get('number')} öppnad (aldrig auto-merge)"
            return res
        changed = changed_paths_fn(wt["path"]) if (wt and changed_paths_fn) else []
        verdict = classify_risk(issue, changed, eval_verdict=res.eval)
        if verdict.level != "low":
            res.status = "escalated"
            res.detail = f"draft-PR #{pr.get('number')} — eskalerad till människa: {'; '.join(verdict.reasons)}"
            res._log(ACTION_MERGE, False, res.detail)
            return res
        if not approve(ACTION_MERGE, {"issue": number, "pr": pr.get("number"), "changed": changed}):
            res.status, res.detail = "ran", f"draft-PR #{pr.get('number')} — merge ej godkänd"
            res._log(ACTION_MERGE, False, "nekad")
            return res
        merged = merge_fn(issue, pr)  # förväntas: ready + merge av lågrisk-PR
        res.pr = {**pr, **(merged or {})}
        res.status = "merged"
        res.detail = f"lågrisk self-merge: PR #{pr.get('number')} mergad"
        res._log(ACTION_MERGE, True, res.detail)
        return res
    finally:
        # Orphan-cleanup: städa alltid worktree + släpp lease — människan tar vid via PR/issue.
        if wt and cleanup_fn:
            try:
                cleanup_fn(wt["path"])
                res._log("worktree-cleanup", True, "worktree borttaget (branch kvar)")
            except Exception as exc:  # noqa: BLE001
                res._log("worktree-cleanup", False, f"{type(exc).__name__}: {exc}")
        if claimed:
            try:
                release_fn(number, owner)
                res._log("release", True, "lease släppt")
            except Exception as exc:  # noqa: BLE001
                res._log("release", False, f"{type(exc).__name__}: {exc}")


def _build_pass_prompt(issue: dict, *, write_mode: bool = False) -> str:
    """Bygg arbetsprompten ur issuens DoD. ``write_mode`` växlar läs-först ↔ skriv-läge."""
    todos = "\n".join(
        f"- [{'x' if t.get('done') else ' '}] {t.get('text')}" for t in (issue.get("todos") or [])
    )
    accept = "\n".join(f"- {c.get('text')}" for c in (issue.get("acceptance_criteria") or []))
    parts = [
        f"Arbeta på issue #{issue.get('number')}: {issue.get('title', '')}",
        (issue.get("body") or "").strip(),
    ]
    if todos:
        parts.append("## Todos\n" + todos)
    if accept:
        parts.append("## Acceptanskriterier (DoD)\n" + accept)
    if write_mode:
        parts.append(
            "Du är i SKRIV-LÄGE i en ISOLERAD git-worktree (crawl): implementera "
            "ändringen — skriv/redigera filer och se till att tester är gröna. Rör bara "
            "det issuen kräver; en människa granskar din draft-PR innan merge (aldrig "
            "auto-merge). Commit + PR sköts av dispatchern."
        )
    else:
        parts.append(
            "Du är i LÄS-LÄGE (crawl): undersök koden och FÖRESLÅ en konkret ändring "
            "(filer + diff i text). Skriv eller kör inte själv — en människa godkänner "
            "innan något muteras."
        )
    return "\n\n".join(p for p in parts if p)


def _default_run_pass(
    *,
    prompt: str,
    slug: Optional[str],
    agent_slug: Optional[str],
    allow_writes: bool,
    cwd: Optional[str] = None,
) -> dict:
    """Default pass-adapter: kör ``agent_host.run_turn`` (async) och reducera händelser.

    Returnerar ``{result, metrics, agent_session_id, events}``. ``cwd`` kör passet i en
    isolerad worktree (skriv-läge). Isolerat bakom denna funktion så crawl_once kan testas
    med en injicerad ``run_pass`` utan SDK.
    """
    import asyncio

    from scripts.tui.agent_host import run_turn

    events: list[tuple[str, Any]] = []

    async def _collect() -> None:
        async for ev in run_turn(
            prompt, slug=slug, allow_writes=allow_writes, agent_slug=agent_slug, cwd=cwd
        ):
            events.append(ev)

    asyncio.run(_collect())
    return {**_reduce_events(events), "events": events}


def _reduce_events(events: list[tuple[str, Any]]) -> dict:
    """Reducera agent_host-händelser → ``{result, metrics, agent_session_id}``.

    Ren funktion (enhetstestbar utan SDK). **Fångar agentens textförslag:** ett pass som
    svarar i ``("text", …)``-block utan att producera ett ``("result", …)`` (ingen
    ResultMessage.result) tappades tidigare → tomt output (orsak #2 i #95-felsöket). Nu
    används ``result``-eventet om det är icketomt, annars de sammanfogade text-blocken.
    ``("error", …)`` kastar (passet misslyckades).
    """
    result_text, text_chunks, metrics, agent_session_id = "", [], {}, None
    for kind, payload in events:
        if kind == "session":
            agent_session_id = payload
        elif kind == "text":
            if payload:
                text_chunks.append(str(payload))
        elif kind == "result":
            result_text = payload or ""
        elif kind == "metrics":
            metrics = payload
        elif kind == "error":
            raise RuntimeError(payload)
    if not (result_text or "").strip():
        result_text = "\n".join(text_chunks).strip()
    return {"result": result_text, "metrics": metrics, "agent_session_id": agent_session_id}


# ---------------------------------------------------------------------------
# Default skriv-/PR-koppling (steg 4: worktree → draft-PR + reviewer)
# ---------------------------------------------------------------------------


def default_worktree_fn(number: int) -> dict:
    """Default ``worktree_fn``: skapa en isolerad worktree på ``dispatch/issue-<n>``."""
    from scripts import worktree

    return worktree.prepare(number)


def build_open_pr_fn(
    *, reviewer: Optional[str] = None, base: str = "main"
) -> Callable[[dict, dict], dict]:
    """Bygg ett ``open_pr_fn`` som pushar skrivpassets branch och öppnar en DRAFT-PR.

    ``reviewer`` (GitHub-login) sätts som required reviewer = den hårda människa-grinden
    (default ``CNS_PR_REVIEWER`` ur miljön). PR:n skapas alltid som **draft** → aldrig
    auto-merge. Branchen kommer ur ``outcome["worktree"]`` (satt av crawl_once).
    """
    import os

    from scripts import prs_client, worktree

    reviewer = reviewer or os.getenv("CNS_PR_REVIEWER") or None

    def open_pr(issue: dict, outcome: dict) -> dict:
        wt = outcome.get("worktree") or {}
        branch = wt["branch"]
        worktree.push(wt["path"], branch)
        title = f"dispatch #{issue.get('number')}: {issue.get('title', '')}".strip()
        body = (
            f"Automatiskt skriv-pass (dispatch crawl) för issue #{issue.get('number')}.\n\n"
            f"Closes #{issue.get('number')}\n\n"
            "**Draft + required reviewer = hård grind. Aldrig auto-merge.**"
        )
        pr = prs_client.create_pr(title, head=branch, base=base, body=body, draft=True)
        if reviewer and pr.get("number"):
            try:
                prs_client.set_reviewers(pr["number"], [reviewer])
            except Exception:
                pass  # PR:n finns ändå; reviewer-grind kan sättas manuellt
        return pr

    return open_pr


def build_merge_fn(*, delete_branch: bool = True) -> Callable[[dict, dict], dict]:
    """Bygg ett ``merge_fn`` som markerar en draft-PR ready och mergar den (Fas 5).

    Anropas BARA av crawl_once efter att ``classify_risk`` sagt ``low`` — alltså aldrig
    på feature-kod/schema/produktion. Använder ``gh`` (samma yta som dispatch redan kör mot).
    Returnerar ``{merged: bool, ...}``.
    """
    import subprocess

    def merge(issue: dict, pr: dict) -> dict:
        number = pr.get("number")
        ready = subprocess.run(
            ["gh", "pr", "ready", str(number)], capture_output=True, text=True
        )
        args = ["gh", "pr", "merge", str(number), "--merge"]
        if delete_branch:
            args.append("--delete-branch")
        merged = subprocess.run(args, capture_output=True, text=True)
        ok = merged.returncode == 0
        return {
            "merged": ok,
            "ready_rc": ready.returncode,
            "detail": (merged.stderr or merged.stdout).strip()[:300],
        }

    return merge


# ---------------------------------------------------------------------------
# CLI — övervakad crawl (ett varv, mänsklig godkännande i terminalen)
# ---------------------------------------------------------------------------


def _cli_approver(action: str, context: dict) -> bool:
    """Terminal-grind: fråga människan ja/nej för varje muterande steg (crawl)."""
    import sys

    prompt = {
        ACTION_CLAIM: f"Claima issue #{context.get('issue')} ({context.get('type')})?",
        ACTION_RUN: f"Kör läs-först-pass på #{context.get('issue')} som '{context.get('agent') or 'generisk'}'?",
        ACTION_OPEN_PR: f"Öppna DRAFT-PR för #{context.get('issue')}?",
        ACTION_MERGE: f"Self-merga LÅGRISK-PR #{context.get('pr')} (#{context.get('issue')})?",
    }.get(action, f"Godkänn '{action}'?")
    sys.stderr.write(f"\n[CRAWL-GRIND] {prompt} [y/N] ")
    sys.stderr.flush()
    try:
        return input().strip().lower() in {"y", "yes", "j", "ja"}
    except EOFError:
        return False


def main(argv: list[str]) -> int:
    import json
    import os
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Plocka upp GITHUB_REPO/CNS_GITHUB_TOKEN/CNS_PR_REVIEWER ur den otrackade .env
    # (samma flöde som resten av repo:t) — sätt en gång, läses varje körning.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass

    from scripts import issues_client

    owner = os.getenv("CNS_AGENT_OWNER") or os.getenv("GITHUB_ACTOR") or "dispatch-crawl"
    auto_yes = "--yes" in argv
    write_mode = "--write" in argv  # skriv-läge: worktree + draft-PR (annars read-first)
    autonomy = "--autonomy" in argv  # Fas 5: self-merge bara lågrisk (kräver --write)

    def candidates() -> list[dict]:
        return issues_client.list_issues(state="open")

    def closed_numbers() -> set[int]:
        return {int(i["number"]) for i in issues_client.list_issues(state="closed")}

    res = crawl_once(
        owner=owner,
        candidates_fn=candidates,
        closed_numbers_fn=closed_numbers,
        approve=(lambda a, c: True) if auto_yes else _cli_approver,
        worktree_fn=default_worktree_fn if write_mode else None,
        open_pr_fn=build_open_pr_fn() if write_mode else None,
        autonomy=autonomy and write_mode,
        merge_fn=build_merge_fn() if (autonomy and write_mode) else None,
    )
    print(json.dumps(res.__dict__, ensure_ascii=False, indent=2, default=str))
    return 0 if res.status in {"no-work", "ran"} else 1


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
