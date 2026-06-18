"""Verktygstaxonomi — enkälla för de konsoliderade feta verktygen.

Ren data: domäner, families, actions (med läs/skriv-flagga) och namnhjälpare. **Inga**
FastMCP/SDK-importer och ingen exekvering här — domän-handlers bor i ``<domän>_core.py``
och resolveras lazy via :func:`get_handler`. Konsumeras av A-wrappers, B-wrappern,
alias-shimmen, C1-härledningen och routern (se paketets ``__init__``).

**Namnkonvention (centraliserad här för att undvika namnkollisioner):**
- connector (universum A, claude.ai): ``cortxt_<domän>``
- lokalt (universum B, SDK in-process): ``mcp__<TOOL_NAMESPACE>__<domän>``

**Läs/skriv per action** driver read-first-grinden: feta verktyg blandar läsning och
skrivning per ``action``, så verktygsnamnet räcker inte — grinden inspekterar action.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# Servernamn för in-process SDK-servern (universum B). Speglar agent_host.CNS_SERVER_NAME.
TOOL_NAMESPACE = "cns"


@dataclass(frozen=True)
class Action:
    """En action på ett fett verktyg. ``write=True`` = muterande (grindas i read-läge)."""

    name: str
    write: bool = False
    required: tuple[str, ...] = ()
    doc: str = ""


@dataclass(frozen=True)
class FatTool:
    """Ett fett verktyg = en domän. ``family`` mappar mot matrisens ``tool_families``."""

    domain: str
    family: str
    summary: str
    actions: tuple[Action, ...]

    @property
    def cortxt_name(self) -> str:
        return f"cortxt_{self.domain}"

    @property
    def local_name(self) -> str:
        return f"mcp__{TOOL_NAMESPACE}__{self.domain}"

    @property
    def action_names(self) -> tuple[str, ...]:
        return tuple(a.name for a in self.actions)

    def get_action(self, name: str) -> Action:
        for a in self.actions:
            if a.name == name:
                return a
        raise ValueError(
            f"okänd action '{name}' för {self.cortxt_name}; giltiga: {', '.join(self.action_names)}"
        )

    def read_actions(self) -> tuple[str, ...]:
        return tuple(a.name for a in self.actions if not a.write)


# --- Taxonomin: 10 feta verktyg som ersätter 43 granulära cortxt_*-verktyg ---------
# family-värdena matchar bemanning_matris.json:cells[*].tool_families. De fyra som inte
# finns i matrisen idag (gh_projects/actions/wiki/leases) blir override-only i C1 tills
# matriscellerna ev. utökas — se scripts/tool_families.py.

FAT_TOOLS: tuple[FatTool, ...] = (
    FatTool(
        "issue", "issues",
        "Arbetsuppgifter (GitHub Issues): lista/läs/skapa/stäng + todos, typ, beroenden, acceptanskriterier.",
        (
            Action("list", doc="Lista öppna issues, valfritt filtrerat på node_slug."),
            Action("get", required=("number",), doc="Hämta en issue med nodkontext."),
            Action("create", write=True, required=("node_slug", "title"),
                   doc="Skapa en issue (params: node_slug, title, body, quest_number, issue_type, depends_on)."),
            Action("close", write=True, required=("number", "result_summary"),
                   doc="Stäng en issue med en avslutskommentar (result_summary)."),
            Action("move_to_quest", write=True, required=("number",),
                   doc="Flytta issue till quest_number (milestone), eller None för att ta bort."),
            Action("add_todo", write=True, required=("number", "text"),
                   doc="Lägg en todo (checkbox) i issue-body."),
            Action("check_todo", write=True, required=("number", "index"),
                   doc="Bocka todo på/av via 0-baserat index (done=bool)."),
            Action("set_type", write=True, required=("number", "issue_type"),
                   doc="Sätt issue-typ: story|bug|spike|chore."),
            Action("set_depends_on", write=True, required=("number", "depends_on"),
                   doc="Sätt beroende-issues (lista av nummer; tom lista rensar)."),
            Action("add_acceptance", write=True, required=("number", "given", "when", "then"),
                   doc="Lägg ett Given/When/Then-acceptanskriterium (agent-DoD)."),
        ),
    ),
    FatTool(
        "quest", "quests",
        "Quests (GitHub Milestones som grupperar issues): lista/läs/skapa/stäng.",
        (
            Action("list", doc="Lista öppna quests med progress (closed/total)."),
            Action("get", required=("number",), doc="Hämta en quest med dess issues."),
            Action("create", write=True, required=("title",),
                   doc="Skapa en quest (params: title, description, initiative)."),
            Action("close", write=True, required=("number",), doc="Stäng en quest."),
        ),
    ),
    FatTool(
        "idea", "ideas",
        "Idé-inkorg: fånga/lista/promota till issue/resolvera.",
        (
            Action("capture", write=True, required=("text",),
                   doc="Fånga en idé (params: text, source, slug, session_id)."),
            Action("list", doc="Lista idéer (params: status, slug, session_id)."),
            Action("update", write=True, required=("idea_id",),
                   doc="Redigera en befintlig idé i stället för en dubblett (params: idea_id, text|append, slug)."),
            Action("promote", write=True, required=("idea_id", "title"),
                   doc="Promota en idé till en issue (params: idea_id, title, slug, body, quest_number)."),
            Action("resolve", write=True, required=("idea_id", "resolution", "reason"),
                   doc="Stäng en idé utan issue (resolution: done|wontfix|duplicate)."),
        ),
    ),
    FatTool(
        "session", "sessions",
        "AI-arbetspass som förstklassigt objekt: start/done/save/list/fork/tree.",
        (
            Action("start", write=True,
                   doc="Registrera ett pågående pass (params: link_kind, link_ref, summary, source, transcript_id)."),
            Action("done", write=True, required=("session_id",),
                   doc="Flippa ett pass till done (params: session_id, summary)."),
            Action("save", write=True, required=("summary",),
                   doc="Spara ett pass i ett svep (default status=done)."),
            Action("list", doc="Lista pass (params: status, link_ref)."),
            Action("fork", write=True, required=("parent_id",),
                   doc="Forka ett barnpass under ett befintligt (bygger sessionsträdet)."),
            Action("tree", doc="Returnera sessionsträdet (params: root_id)."),
        ),
    ),
    FatTool(
        "pr", "prs",
        "Pull Requests: lista/läs/skapa/sätt granskare.",
        (
            Action("list", doc="Lista PR:er (state: open|closed|all)."),
            Action("get", required=("number",), doc="Hämta en PR med review-status och checks."),
            Action("create", write=True, required=("title", "head"),
                   doc="Skapa en PR (params: title, head, base, body, draft)."),
            Action("set_reviewers", write=True, required=("number", "reviewers"),
                   doc="Begär granskning av GitHub-användare (reviewers: lista av login)."),
        ),
    ),
    FatTool(
        "project", "projects",
        "Katalognoder (catalog.yaml): lista alla / hämta en. Läs-only.",
        (
            Action("list", doc="Lista alla katalognoder med metadata."),
            Action("get", required=("slug",), doc="Hämta en nods meta + decisions-prosa."),
        ),
    ),
    FatTool(
        "gh_project", "gh_projects",
        "GitHub Projects v2: lista boards/items, flytta kort.",
        (
            Action("list", doc="Lista GitHub Projects v2 för repo-ägaren."),
            Action("list_items", required=("project_id",), doc="Lista items i en board (params: project_id, first)."),
            Action("move_item", write=True, required=("project_id", "item_id", "field_id", "option_id"),
                   doc="Flytta ett item till ny kolumn via single-select-fält."),
        ),
    ),
    FatTool(
        "action", "actions",
        "GitHub Actions: lista körningar, trigga workflow, hämta körstatus.",
        (
            Action("list_runs", doc="Lista senaste workflow-körningar (params: workflow_id, limit)."),
            Action("trigger", write=True, required=("workflow_id",),
                   doc="Trigga workflow_dispatch (params: workflow_id, ref, inputs)."),
            Action("get_run", required=("run_id",), doc="Hämta status/conclusion för en körning."),
        ),
    ),
    FatTool(
        "wiki", "wiki",
        "GitHub Wiki: lista/läs/skriv sidor.",
        (
            Action("list", doc="Lista wiki-sidor (root)."),
            Action("read", required=("page",), doc="Läs en wiki-sida (utan .md)."),
            Action("write", write=True, required=("page", "content"),
                   doc="Skapa/uppdatera en wiki-sida (params: page, content, message)."),
        ),
    ),
    FatTool(
        "lease", "leases",
        "Efemära issue-claims för multi-agent-koordinering (Redis, fail-open).",
        (
            Action("claim", write=True, required=("number",), doc="Claima en issue atomiskt."),
            Action("release", write=True, required=("number",), doc="Släpp din claim på en issue."),
            Action("heartbeat", write=True, required=("number",), doc="Förnya din claims TTL."),
            Action("list", doc="Lista alla hållna claims just nu."),
        ),
    ),
)

# --- Uppslag ------------------------------------------------------------------------

_BY_DOMAIN: dict[str, FatTool] = {t.domain: t for t in FAT_TOOLS}
_BY_CORTXT: dict[str, FatTool] = {t.cortxt_name: t for t in FAT_TOOLS}
_BY_LOCAL: dict[str, FatTool] = {t.local_name: t for t in FAT_TOOLS}

ALL_FAMILIES: tuple[str, ...] = tuple(t.family for t in FAT_TOOLS)


def by_domain(domain: str) -> FatTool:
    try:
        return _BY_DOMAIN[domain]
    except KeyError:
        raise ValueError(f"okänd domän '{domain}'; giltiga: {', '.join(_BY_DOMAIN)}") from None


def by_name(name: str) -> FatTool | None:
    """Slå upp ett fett verktyg på connector- eller lokalt namn (None om okänt)."""
    return _BY_CORTXT.get(name) or _BY_LOCAL.get(name)


def get_handler(domain: str) -> Callable[..., object]:
    """Lazy-importera och returnera ``scripts.tools.<domain>_core.<domain>``.

    Lazy så registry-modulen kan importeras (för ren taxonomi i router/C1) utan att
    dra in datalager-beroenden. Kastar ImportError/AttributeError om kärnan saknas.
    """
    import importlib

    mod = importlib.import_module(f"scripts.tools.{domain}_core")
    return getattr(mod, domain)


FAMILY_TO_DOMAIN: dict[str, str] = {t.family: t.domain for t in FAT_TOOLS}

# Gamla granulära cortxt_*-namn → domän. Enkälla för router-resolution (rollernas
# ``## Tillåtna verktyg`` kan under övergången innehålla gamla namn). Exekverings-
# mappningen (namn → action) bor i ``app/tools/_aliases.py``; här behövs bara domänen.
LEGACY_TOOL_DOMAINS: dict[str, str] = {
    # issue
    "cortxt_list_open_issues": "issue", "cortxt_get_issue": "issue",
    "cortxt_create_issue": "issue", "cortxt_close_issue": "issue",
    "cortxt_move_issue_to_quest": "issue", "cortxt_add_todo": "issue",
    "cortxt_check_todo": "issue", "cortxt_set_issue_type": "issue",
    "cortxt_set_depends_on": "issue", "cortxt_add_acceptance": "issue",
    # quest
    "cortxt_list_quests": "quest", "cortxt_get_quest": "quest",
    "cortxt_create_quest": "quest", "cortxt_close_quest": "quest",
    # idea
    "cortxt_capture_idea": "idea", "cortxt_list_ideas": "idea",
    "cortxt_promote_idea_to_issue": "idea", "cortxt_resolve_idea": "idea",
    # session
    "cortxt_start_session": "session", "cortxt_mark_session_done": "session",
    "cortxt_save_session": "session", "cortxt_list_sessions": "session",
    "cortxt_fork_session": "session", "cortxt_get_session_tree": "session",
    # pr
    "cortxt_list_prs": "pr", "cortxt_get_pr": "pr",
    "cortxt_create_pr": "pr", "cortxt_set_pr_reviewers": "pr",
    # project
    "cortxt_list_projects": "project", "cortxt_get_project": "project",
    # gh_project
    "cortxt_list_gh_projects": "gh_project", "cortxt_list_gh_project_items": "gh_project",
    "cortxt_move_gh_project_item": "gh_project",
    # action
    "cortxt_list_workflow_runs": "action", "cortxt_trigger_workflow": "action",
    "cortxt_get_workflow_run": "action",
    # wiki
    "cortxt_list_wiki_pages": "wiki", "cortxt_read_wiki_page": "wiki",
    "cortxt_write_wiki_page": "wiki",
    # lease (OBS: dessa är lease-domänen, inte issue)
    "cortxt_claim_issue": "lease", "cortxt_release_issue": "lease",
    "cortxt_heartbeat_issue": "lease", "cortxt_list_leases": "lease",
}


def domain_for_token(token: str) -> str | None:
    """Lös ett rollverktygs-token till en domän, oavsett form.

    Hanterar: family (``issues``), fett connector-namn (``cortxt_issue``), lokalt namn
    (``mcp__cns__issue``) och gammalt granulärt namn (``cortxt_create_issue``). None om okänt.
    """
    if token in FAMILY_TO_DOMAIN:
        return FAMILY_TO_DOMAIN[token]
    tool = by_name(token)
    if tool is not None:
        return tool.domain
    return LEGACY_TOOL_DOMAINS.get(token)


def local_names_for(tokens: object) -> list[str]:
    """Rollens verktygs-tokens → unika lokala feta namn (universum B, ``mcp__cns__*``)."""
    out: list[str] = []
    seen: set[str] = set()
    for tok in tokens or []:
        dom = domain_for_token(tok)
        if dom and dom not in seen:
            seen.add(dom)
            out.append(by_domain(dom).local_name)
    return out


def dispatch(domain: str, action: str, **kwargs: object) -> object:
    """Validera action + required-params mot taxonomin och kör handlern. Kastar ValueError.

    ``None`` räknas som saknat för required-params (connector-wrappern skickar typade
    valfria args som default None, så ett utelämnat required-värde fångas här).
    """
    tool = by_domain(domain)
    spec = tool.get_action(action)  # validerar action-namnet (kastar ValueError)
    missing = [p for p in spec.required if kwargs.get(p) is None]
    if missing:
        raise ValueError(
            f"{tool.cortxt_name}(action='{action}') kräver: {', '.join(missing)}"
        )
    return get_handler(domain)(action, **kwargs)
