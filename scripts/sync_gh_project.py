"""Synka öppna issues till org-projektet "Backlog" (GitHub Projects v2).

Board & Projects-visualisering (epic #13). Lägger alla öppna issues i projektet och
sätter single-select-fälten **System** (ur `node:<slug>`-label), **Type** (ur
`type:<value>`-label) och **Initiative** (ur issuens milestone-description
`Initiative: <namn>`). Epic = inbyggda Milestone-fältet (auto). Idempotent.

Sanningskälla för ägaren: env **`CNS_PROJECT_OWNER`** (org, t.ex. `Cortxt-io`),
skild från `GITHUB_REPO`-ägaren (repot kan ligga kvar på ett user-konto).

Token: `CNS_GITHUB_TOKEN` (kräver `project`-scope) eller `gh auth token` (efter
`gh auth refresh -s project`). Återanvänder `issues_client` för issues/milestones.

Körs: `cns project sync` eller `python -m scripts.sync_gh_project [--dry-run]`.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from typing import Optional

import requests

from scripts.issues_client import list_issues, list_milestones

_GH_GRAPHQL = "https://api.github.com/graphql"
_TIMEOUT = 30
PROJECT_TITLE = "Backlog"

# Single-select-fält scriptet sätter (built-in Milestone/Status rörs ej här).
FIELD_SYSTEM = "System"
FIELD_TYPE = "Type"
FIELD_INITIATIVE = "Initiative"


# ---------------------------------------------------------------------------
# Konfiguration / GraphQL
# ---------------------------------------------------------------------------

def _token() -> str:
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


def project_owner() -> str:
    """Org som äger projektet (CNS_PROJECT_OWNER), fallback till repo-ägaren."""
    owner = os.getenv("CNS_PROJECT_OWNER", "").strip()
    if owner:
        return owner
    repo = os.getenv("GITHUB_REPO", "")
    return repo.split("/")[0] if "/" in repo else repo


def _repo_parts() -> tuple[str, str]:
    repo = os.getenv("GITHUB_REPO", "")
    owner, _, name = repo.partition("/")
    return owner, name


def _graphql(query: str, variables: dict | None = None) -> dict:
    resp = requests.post(
        _GH_GRAPHQL,
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(str(data["errors"]))
    return data["data"]


# ---------------------------------------------------------------------------
# Rena hjälpare (enhetstestbara utan nätverk)
# ---------------------------------------------------------------------------

def parse_initiative(description: Optional[str]) -> Optional[str]:
    """Plocka ``Initiative: <namn>`` ur en milestone-description (annars None)."""
    for line in (description or "").splitlines():
        line = line.strip()
        if line.lower().startswith("initiative:"):
            return line.split(":", 1)[1].strip() or None
    return None


def field_value_for(issue: dict, milestone_initiative: dict[int, Optional[str]]) -> dict[str, Optional[str]]:
    """Returnera önskade single-select-värden (fält-namn → option-namn) för ett issue."""
    quest = issue.get("quest")
    return {
        FIELD_SYSTEM: issue.get("node_slug"),
        FIELD_TYPE: issue.get("type") or "story",
        FIELD_INITIATIVE: milestone_initiative.get(quest) if quest else None,
    }


# ---------------------------------------------------------------------------
# GraphQL-frågor
# ---------------------------------------------------------------------------

def resolve_project() -> dict:
    """Hämta projektet (id + single-select-fält med option-id:n) ur orgen.

    Returnerar {"id", "fields": {fältnamn: {"id", "options": {optionnamn: id}}}}.
    Raises RuntimeError om projektet inte hittas.
    """
    data = _graphql(
        """
        query($login: String!) {
          organization(login: $login) {
            projectsV2(first: 50) {
              nodes {
                id title
                fields(first: 50) {
                  nodes {
                    __typename
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
    org = data.get("organization") or {}
    projects = (org.get("projectsV2") or {}).get("nodes", [])
    proj = next((p for p in projects if p.get("title") == PROJECT_TITLE), None)
    if not proj:
        raise RuntimeError(
            f"Project '{PROJECT_TITLE}' saknas under org '{project_owner()}'. "
            f"Skapa det först: gh project create --owner {project_owner()} --title \"{PROJECT_TITLE}\""
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


def existing_items(project_id: str) -> dict[str, str]:
    """Returnera {content_node_id: project_item_id} för items redan i projektet."""
    out: dict[str, str] = {}
    cursor = None
    while True:
        data = _graphql(
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


def open_issue_node_ids() -> dict[int, str]:
    """Returnera {issue_number: graphql_node_id} för öppna issues i repot."""
    owner, name = _repo_parts()
    out: dict[int, str] = {}
    cursor = None
    while True:
        data = _graphql(
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


def add_item(project_id: str, content_id: str) -> str:
    data = _graphql(
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


def set_single_select(project_id: str, item_id: str, field_id: str, option_id: str) -> None:
    _graphql(
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


# ---------------------------------------------------------------------------
# Orkestrering
# ---------------------------------------------------------------------------

def sync(dry_run: bool = False) -> dict:
    proj = resolve_project()
    project_id = proj["id"]
    fields = proj["fields"]

    issues = list_issues(state="open")
    node_ids = open_issue_node_ids()
    milestone_initiative = {
        m["number"]: parse_initiative(m.get("description"))
        for m in list_milestones(state="all")
    }
    present = {} if dry_run else existing_items(project_id)

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
            item_id = add_item(project_id, content_id)
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
                set_single_select(project_id, item_id, fields[fname]["id"], option_id)
            set_fields += 1

    summary = {
        "issues": len(issues),
        "added": added,
        "field_values_set": set_fields,
        "missing_options": sorted(skipped_opts),
        "dry_run": dry_run,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Visa vad som skulle göras")
    args = parser.parse_args()

    if not _token():
        raise SystemExit(
            "Ingen token. Sätt CNS_GITHUB_TOKEN (project-scope) eller kör "
            "`gh auth refresh -s project` så scriptet kan använda `gh auth token`."
        )
    res = sync(dry_run=args.dry_run)
    print(f"Issues: {res['issues']} | tillagda: {res['added']} | fält satta: {res['field_values_set']}")
    if res["missing_options"]:
        print("Saknade single-select-options (lägg dem på fältet, eller bredda enum):")
        for o in res["missing_options"]:
            print(f"  - {o}")


if __name__ == "__main__":
    main()
