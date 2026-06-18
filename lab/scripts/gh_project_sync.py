"""Org-Project v2-spegling: projicera CNS-begrepp på ett GitHub org-Project (GraphQL).

Bygger ovanpå ``scripts/tools/gh_project_core`` (delad ``_graphql``-transport, kräver
``CNS_GITHUB_TOKEN`` med ``project``-scope/Projects:write). Det här lagret äger den
CNS-specifika *projektionen* — idag: sätt **Initiative** (single-select) på en issue i
org-Projektet. Det är hur initiativ-lagret får ett riktigt hem (ersätter ``Initiative:``-
textprefixet); se ``decisions/git-github-grund.md`` + ``plans/taxonomy-mirror-skeleton.md``.

Designval:
- **Resolva fält/options på NAMN, inte hårdkodade IDs** — robust mot ny-skapade projekt och
  tål att options läggs till. IDs cachas per (project, query) inom ett anrop.
- **Idempotent:** ``addProjectV2ItemById`` returnerar befintligt item om det redan finns.
- Transport är **injicerbar** (``graphql_fn``) så logiken testas utan live-GraphQL.

Sprint→Iteration-fältet (med defensiv läs-bygg-skriv pga GitHubs replace-hela-listan-bugg)
hör till nästa increment när sprint-nivån införs — medvetet inte här.
"""
from __future__ import annotations

import os
import subprocess
from typing import Callable, Optional

from scripts.issues_client import list_issues, list_milestones
from scripts.tools.gh_project_core import _GH_GRAPHQL, _TIMEOUT
from scripts.tools.gh_project_core import _graphql as _default_graphql

GraphQLFn = Callable[[str, dict], dict]


def _fields_query() -> str:
    return """
    query($id: ID!) {
      node(id: $id) {
        ... on ProjectV2 {
          fields(first: 50) {
            nodes {
              ... on ProjectV2SingleSelectField { id name options { id name } }
              ... on ProjectV2FieldCommon { id name }
            }
          }
        }
      }
    }
    """


def project_fields(project_id: str, graphql_fn: GraphQLFn = _default_graphql) -> list[dict]:
    """Alla fält på projektet (single-select-fält inkl. deras options)."""
    data = graphql_fn(_fields_query(), {"id": project_id})
    return (data.get("node") or {}).get("fields", {}).get("nodes", []) or []


def resolve_single_select(
    project_id: str, field_name: str, option_name: str, graphql_fn: GraphQLFn = _default_graphql
) -> tuple[str, str]:
    """Slå upp (field_id, option_id) på namn. Kastar ValueError om fält/option saknas."""
    for f in project_fields(project_id, graphql_fn):
        if f.get("name") == field_name and "options" in f:
            for opt in f.get("options", []):
                if opt.get("name") == option_name:
                    return f["id"], opt["id"]
            raise ValueError(
                f"option '{option_name}' saknas i fält '{field_name}'; "
                f"finns: {', '.join(o.get('name', '') for o in f.get('options', []))}"
            )
    raise ValueError(f"single-select-fält '{field_name}' saknas i projektet")


def add_item(project_id: str, content_id: str, graphql_fn: GraphQLFn = _default_graphql) -> str:
    """Lägg en issue/PR (content node-id) i projektet. Idempotent → returnerar item-id."""
    data = graphql_fn(
        """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item { id }
          }
        }
        """,
        {"projectId": project_id, "contentId": content_id},
    )
    return data["addProjectV2ItemById"]["item"]["id"]


def set_single_select(
    project_id: str, item_id: str, field_id: str, option_id: str,
    graphql_fn: GraphQLFn = _default_graphql,
) -> str:
    """Sätt ett single-select-fältvärde på ett item. Returnerar item-id."""
    data = graphql_fn(
        """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId, itemId: $itemId, fieldId: $fieldId,
            value: { singleSelectOptionId: $optionId }
          }) { projectV2Item { id } }
        }
        """,
        {"projectId": project_id, "itemId": item_id, "fieldId": field_id, "optionId": option_id},
    )
    return data["updateProjectV2ItemFieldValue"]["projectV2Item"]["id"]


def set_initiative(
    project_id: str, content_id: str, initiative_name: str,
    graphql_fn: GraphQLFn = _default_graphql,
) -> str:
    """Högnivå: säkerställ att issuen ligger i projektet och sätt dess Initiative-fält.

    Detta ÄR initiativ-projektionen: CNS-begreppet ``initiative`` → org-Project single-select.
    Idempotent. Returnerar item-id.
    """
    item_id = add_item(project_id, content_id, graphql_fn)
    field_id, option_id = resolve_single_select(project_id, "Initiative", initiative_name, graphql_fn)
    return set_single_select(project_id, item_id, field_id, option_id, graphql_fn)


# --- Backfill (Fas 1d): befintliga issues initiativ → org-Project --------------------
def plan_initiative_backfill(
    issues: list[dict], milestone_initiative: dict[int, str]
) -> list[dict]:
    """Ren planerare. ``issues``: [{number, node_id, milestone}] (milestone = ms-nummer eller None).

    En issues initiativ = dess milestones initiativ. Returnerar handlingsplanen
    [{number, node_id, initiative}] för de issues vars milestone HAR ett initiativ.
    Inga sidoeffekter — testbar; live-applicering sker i :func:`backfill_initiatives`.
    """
    plan = []
    for it in issues:
        ms = it.get("milestone")
        init = milestone_initiative.get(ms) if ms is not None else None
        if init and it.get("node_id"):
            plan.append({"number": it["number"], "node_id": it["node_id"], "initiative": init})
    return plan


def backfill_initiatives(
    project_id: str,
    issues: list[dict],
    milestone_initiative: dict[int, str],
    dry_run: bool = True,
    graphql_fn: GraphQLFn = _default_graphql,
) -> dict:
    """Sätt Initiative på alla issues utifrån deras milestone. ``dry_run`` skriver inget.

    Returnerar {dry_run, actions:[...]}. Vid live: varje action får ``item_id``.
    """
    plan = plan_initiative_backfill(issues, milestone_initiative)
    if dry_run:
        return {"dry_run": True, "actions": plan}
    done = []
    for a in plan:
        item = set_initiative(project_id, a["node_id"], a["initiative"], graphql_fn)
        done.append({**a, "item_id": item})
    return {"dry_run": False, "actions": done}


# --- Full backlog-synk (epic #13): öppna issues → org-Projektet "Backlog" -------------
# Återskapar `cns project sync` ovanpå denna delade projektion (ersätter #120:s
# fristående scripts/sync_gh_project.py, som duplicerade GraphQL-stacken innan denna
# modul fanns). Sätter tre single-select-fält: System (node:-label), Type (type:-label),
# Initiative (issuens milestone-initiativ). Epic = inbyggda Milestone-fältet (auto).

PROJECT_TITLE = "Backlog"
FIELD_SYSTEM = "System"
FIELD_TYPE = "Type"
FIELD_INITIATIVE = "Initiative"


def project_owner() -> str:
    """Org som äger projektet (``CNS_PROJECT_OWNER``), fallback till repo-ägaren.

    Skild från ``GITHUB_REPO``-ägaren: repot kan ligga kvar på ett user-konto medan
    Projektet är org-ägt.
    """
    owner = os.getenv("CNS_PROJECT_OWNER", "").strip()
    if owner:
        return owner
    repo = os.getenv("GITHUB_REPO", "")
    return repo.split("/")[0] if "/" in repo else repo


def _repo_parts() -> tuple[str, str]:
    repo = os.getenv("GITHUB_REPO", "")
    owner, _, name = repo.partition("/")
    return owner, name


def _cli_token() -> str:
    """Token för CLI-synk: ``CNS_GITHUB_TOKEN``, annars ``gh auth token`` (efter
    ``gh auth refresh -s project``). Skild från serverkärnans ``_token`` — den har
    medvetet ingen ``gh``-fallback (subprocess på Railway), CLI:t behöver den lokalt.
    """
    t = os.getenv("CNS_GITHUB_TOKEN", "")
    if t:
        return t
    try:
        out = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except Exception:
        return ""


def _cli_graphql(query: str, variables: dict | None = None) -> dict:
    """GraphQL-transport för CLI-synk — som ``gh_project_core._graphql`` men med
    ``_cli_token`` (gh-fallback). Injiceras i primitiverna via ``graphql_fn``."""
    import requests

    resp = requests.post(
        _GH_GRAPHQL,
        headers={"Authorization": f"Bearer {_cli_token()}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(str(data["errors"]))
    return data["data"]


def field_value_for(
    issue: dict, milestone_initiative: dict[int, Optional[str]]
) -> dict[str, Optional[str]]:
    """Önskade single-select-värden (fält-namn → option-namn) för ett issue. Ren."""
    quest = issue.get("quest")
    return {
        FIELD_SYSTEM: issue.get("node_slug"),
        FIELD_TYPE: issue.get("type") or "story",
        FIELD_INITIATIVE: milestone_initiative.get(quest) if quest else None,
    }


def resolve_project(graphql_fn: GraphQLFn = _cli_graphql) -> dict:
    """Hämta Projektet "Backlog" (id + single-select-fält med option-id:n) ur orgen.

    Returnerar ``{"id", "fields": {namn: {"id", "options": {optionnamn: id}}}}``.
    Kastar ``RuntimeError`` om Projektet saknas.
    """
    data = graphql_fn(
        """
        query($login: String!) {
          organization(login: $login) {
            projectsV2(first: 50) {
              nodes {
                id title
                fields(first: 50) {
                  nodes {
                    ... on ProjectV2SingleSelectField { id name options { id name } }
                    ... on ProjectV2FieldCommon { id name }
                  }
                }
              }
            }
          }
        }
        """,
        {"login": project_owner()},
    )
    org = (data or {}).get("organization") or {}
    projects = (org.get("projectsV2") or {}).get("nodes", [])
    proj = next((p for p in projects if p.get("title") == PROJECT_TITLE), None)
    if not proj:
        raise RuntimeError(
            f"Projektet '{PROJECT_TITLE}' saknas under org '{project_owner()}'. "
            f'Skapa det först: gh project create --owner {project_owner()} --title "{PROJECT_TITLE}"'
        )
    fields: dict[str, dict] = {}
    for f in (proj.get("fields") or {}).get("nodes", []):
        name = f.get("name")
        if not name:
            continue
        fields[name] = {
            "id": f.get("id"),
            "options": {o["name"]: o["id"] for o in f.get("options", [])} if f.get("options") else {},
        }
    return {"id": proj["id"], "fields": fields}


def open_issue_node_ids(graphql_fn: GraphQLFn = _cli_graphql) -> dict[int, str]:
    """``{issue_number: graphql_node_id}`` för öppna issues i repot (paginerat)."""
    owner, name = _repo_parts()
    out: dict[int, str] = {}
    cursor = None
    while True:
        data = graphql_fn(
            """
            query($owner: String!, $name: String!, $cursor: String) {
              repository(owner: $owner, name: $name) {
                issues(first: 100, states: OPEN, after: $cursor) {
                  pageInfo { hasNextPage endCursor }
                  nodes { number id }
                }
              }
            }
            """,
            {"owner": owner, "name": name, "cursor": cursor},
        )
        issues = ((data.get("repository") or {}).get("issues") or {})
        for n in issues.get("nodes", []):
            out[n["number"]] = n["id"]
        page = issues.get("pageInfo") or {}
        if page.get("hasNextPage"):
            cursor = page.get("endCursor")
        else:
            break
    return out


def existing_items(project_id: str, graphql_fn: GraphQLFn = _cli_graphql) -> dict[str, str]:
    """``{content_node_id: project_item_id}`` för items redan i Projektet (paginerat)."""
    out: dict[str, str] = {}
    cursor = None
    while True:
        data = graphql_fn(
            """
            query($id: ID!, $cursor: String) {
              node(id: $id) {
                ... on ProjectV2 {
                  items(first: 100, after: $cursor) {
                    pageInfo { hasNextPage endCursor }
                    nodes { id content { ... on Issue { id } ... on PullRequest { id } } }
                  }
                }
              }
            }
            """,
            {"id": project_id, "cursor": cursor},
        )
        items = ((data.get("node") or {}).get("items") or {})
        for it in items.get("nodes", []):
            content = it.get("content") or {}
            if content.get("id"):
                out[content["id"]] = it["id"]
        page = items.get("pageInfo") or {}
        if page.get("hasNextPage"):
            cursor = page.get("endCursor")
        else:
            break
    return out


def sync(dry_run: bool = False, graphql_fn: GraphQLFn = None) -> dict:
    """Synka alla öppna issues → Projektet "Backlog" och sätt System/Type/Initiative.

    Idempotent (dedupar mot befintliga items). ``dry_run`` skriver inget. Återanvänder
    ``add_item``/``set_single_select`` via den injicerade transporten (``graphql_fn``,
    default :func:`_cli_graphql` med gh-token-fallback).
    """
    graphql_fn = graphql_fn or _cli_graphql

    proj = resolve_project(graphql_fn)
    project_id = proj["id"]
    fields = proj["fields"]

    issues = list_issues(state="open")
    node_ids = open_issue_node_ids(graphql_fn)
    milestone_initiative = {
        m["number"]: m.get("initiative") for m in list_milestones(state="all")
    }
    present = {} if dry_run else existing_items(project_id, graphql_fn)

    added = 0
    set_fields = 0
    skipped_opts: set[str] = set()

    for issue in issues:
        number = issue.get("number")
        content_id = node_ids.get(number)
        if not content_id:
            continue

        if content_id in present:
            item_id = present[content_id]
        elif dry_run:
            item_id = None
            added += 1
        else:
            item_id = add_item(project_id, content_id, graphql_fn)
            present[content_id] = item_id
            added += 1

        wanted = field_value_for(issue, milestone_initiative)
        for fname, option_name in wanted.items():
            if not option_name or fname not in fields:
                continue
            option_id = fields[fname]["options"].get(option_name)
            if not option_id:
                skipped_opts.add(f"{fname}:{option_name}")
                continue
            if not dry_run and item_id:
                set_single_select(project_id, item_id, fields[fname]["id"], option_id, graphql_fn)
            set_fields += 1

    return {
        "issues": len(issues),
        "added": added,
        "field_values_set": set_fields,
        "missing_options": sorted(skipped_opts),
        "dry_run": dry_run,
    }
