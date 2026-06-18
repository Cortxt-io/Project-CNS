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

from typing import Callable, Optional

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
