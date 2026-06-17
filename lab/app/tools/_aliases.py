"""Bakåtkompat-shim: de 43 gamla granulära ``cortxt_*``-verktygen som tunna alias.

Varför: konsolideringen till feta verktyg (``cortxt_issue`` m.fl.) är ett **breaking
rename** mot claude.ai-connectorn. Under övergången (Fas α) registreras både feta verktyg
OCH alla gamla namn med **bevarad signatur**, så en connector som ännu inte re-authats
fortsätter fungera oförändrad. Aliasen bär ingen egen logik — de delegerar till samma
domänkärna (``scripts/tools/*_core.py``) via ``_fat.call``, så det finns inget att driva isär.

Deprecation: docstring märker varje alias med sitt feta motsvarighet. När användningen av
ett namn tystnat (Fas γ) tas ``register_aliases``-raden bort i ``app/mcp_server.py``.
Se ``decisions/mcp-router.md`` och ``plans/agentur-verktygsatkomst-spec.md``.
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.tools._fat import call, owner, push_idea, push_session


def register_aliases(mcp: FastMCP) -> None:
    # --- issue (10) → cortxt_issue ----------------------------------------------
    @mcp.tool()
    def cortxt_list_open_issues(node_slug: str | None = None) -> list[dict]:
        """[DEPRECATED → cortxt_issue(action='list')] List open work-item issues."""
        return call("issue", "list", node_slug=node_slug)

    @mcp.tool()
    def cortxt_get_issue(number: int) -> dict:
        """[DEPRECATED → cortxt_issue(action='get')] Get a work-item issue with node context."""
        return call("issue", "get", number=number)

    @mcp.tool()
    def cortxt_create_issue(
        node_slug: str, title: str, body: str = "", quest_number: int | None = None,
        issue_type: str = "story", depends_on: list[int] | None = None,
    ) -> dict:
        """[DEPRECATED → cortxt_issue(action='create')] Create a work-item issue."""
        return call("issue", "create", node_slug=node_slug, title=title, body=body,
                    quest_number=quest_number, issue_type=issue_type, depends_on=depends_on)

    @mcp.tool()
    def cortxt_close_issue(number: int, result_summary: str) -> dict:
        """[DEPRECATED → cortxt_issue(action='close')] Close an issue with a closing comment."""
        return call("issue", "close", number=number, result_summary=result_summary)

    @mcp.tool()
    def cortxt_move_issue_to_quest(number: int, quest_number: int | None = None) -> dict:
        """[DEPRECATED → cortxt_issue(action='move_to_quest')] Move an issue into/out of a quest."""
        return call("issue", "move_to_quest", number=number, quest_number=quest_number)

    @mcp.tool()
    def cortxt_add_todo(number: int, text: str) -> dict:
        """[DEPRECATED → cortxt_issue(action='add_todo')] Add a sub-task (todo) to an issue."""
        return call("issue", "add_todo", number=number, text=text)

    @mcp.tool()
    def cortxt_check_todo(number: int, index: int, done: bool = True) -> dict:
        """[DEPRECATED → cortxt_issue(action='check_todo')] Tick a todo on/off by index."""
        return call("issue", "check_todo", number=number, index=index, done=done)

    @mcp.tool()
    def cortxt_set_issue_type(number: int, issue_type: str) -> dict:
        """[DEPRECATED → cortxt_issue(action='set_type')] Set an issue's type."""
        return call("issue", "set_type", number=number, issue_type=issue_type)

    @mcp.tool()
    def cortxt_set_depends_on(number: int, depends_on: list[int]) -> dict:
        """[DEPRECATED → cortxt_issue(action='set_depends_on')] Set the issues this depends on."""
        return call("issue", "set_depends_on", number=number, depends_on=depends_on)

    @mcp.tool()
    def cortxt_add_acceptance(number: int, given: str, when: str, then: str) -> dict:
        """[DEPRECATED → cortxt_issue(action='add_acceptance')] Add a Given/When/Then criterion."""
        return call("issue", "add_acceptance", number=number, given=given, when=when, then=then)

    # --- quest (4) → cortxt_quest -----------------------------------------------
    @mcp.tool()
    def cortxt_list_quests() -> list[dict]:
        """[DEPRECATED → cortxt_quest(action='list')] List open quests with progress."""
        return call("quest", "list")

    @mcp.tool()
    def cortxt_get_quest(number: int) -> dict:
        """[DEPRECATED → cortxt_quest(action='get')] Get a quest with its issues."""
        return call("quest", "get", number=number)

    @mcp.tool()
    def cortxt_create_quest(title: str, description: str = "", initiative: str | None = None) -> dict:
        """[DEPRECATED → cortxt_quest(action='create')] Create a quest (milestone)."""
        return call("quest", "create", title=title, description=description, initiative=initiative)

    @mcp.tool()
    def cortxt_close_quest(number: int) -> dict:
        """[DEPRECATED → cortxt_quest(action='close')] Close a quest."""
        return call("quest", "close", number=number)

    # --- idea (4) → cortxt_idea (push i shimmen, som tidigare) ------------------
    @mcp.tool()
    def cortxt_capture_idea(
        text: str, source: str = "chat", slug: str | None = None, session_id: str | None = None,
    ) -> dict:
        """[DEPRECATED → cortxt_idea(action='capture')] Capture a raw idea into the inbox."""
        idea = call("idea", "capture", text=text, source=source, slug=slug, session_id=session_id)
        push_idea(idea["id"], f"cns-vault: capture idea {idea['id']}")
        return idea

    @mcp.tool()
    def cortxt_list_ideas(
        status: str = "open", slug: str | None = None, session_id: str | None = None,
    ) -> list[dict]:
        """[DEPRECATED → cortxt_idea(action='list')] List captured ideas."""
        return call("idea", "list", status=status, slug=slug, session_id=session_id)

    @mcp.tool()
    def cortxt_promote_idea_to_issue(
        idea_id: str, title: str, slug: str | None = None,
        body: str | None = None, quest_number: int | None = None,
    ) -> dict:
        """[DEPRECATED → cortxt_idea(action='promote')] Promote an inbox idea into an issue."""
        result = call("idea", "promote", idea_id=idea_id, title=title, slug=slug,
                      body=body, quest_number=quest_number)
        iid = result["idea"]["id"]
        push_idea(iid, f"cns-vault: promote idea {iid} to issue #{result['issue']['number']}")
        return result

    @mcp.tool()
    def cortxt_resolve_idea(idea_id: str, resolution: str, reason: str) -> dict:
        """[DEPRECATED → cortxt_idea(action='resolve')] Close an idea without creating an issue."""
        idea = call("idea", "resolve", idea_id=idea_id, resolution=resolution, reason=reason)
        push_idea(idea["id"], f"cns-vault: resolve idea {idea['id']} ({resolution})")
        return idea

    # --- session (6) → cortxt_session (push i shimmen) --------------------------
    @mcp.tool()
    def cortxt_start_session(
        link_kind: str | None = None, link_ref: str | None = None, summary: str = "",
        source: str = "chat", transcript_id: str | None = None,
    ) -> dict:
        """[DEPRECATED → cortxt_session(action='start')] Register a running AI work-pass."""
        s = call("session", "start", link_kind=link_kind, link_ref=link_ref,
                 summary=summary, source=source, transcript_id=transcript_id)
        push_session(s, "start session")
        return s

    @mcp.tool()
    def cortxt_mark_session_done(session_id: str, summary: str | None = None) -> dict:
        """[DEPRECATED → cortxt_session(action='done')] Flip a running session to done."""
        s = call("session", "done", session_id=session_id, summary=summary)
        push_session(s, "mark session done")
        return s

    @mcp.tool()
    def cortxt_save_session(
        summary: str, link_kind: str | None = None, link_ref: str | None = None,
        status: str = "done", source: str = "chat", transcript_id: str | None = None,
    ) -> dict:
        """[DEPRECATED → cortxt_session(action='save')] Save an AI work-pass in one shot."""
        s = call("session", "save", summary=summary, link_kind=link_kind, link_ref=link_ref,
                 status=status, source=source, transcript_id=transcript_id)
        push_session(s, "save session")
        return s

    @mcp.tool()
    def cortxt_list_sessions(status: str | None = None, link_ref: str | None = None) -> list[dict]:
        """[DEPRECATED → cortxt_session(action='list')] List sessions, newest first."""
        return call("session", "list", status=status, link_ref=link_ref)

    @mcp.tool()
    def cortxt_fork_session(
        parent_id: str, summary: str = "", fork_name: str | None = None,
        link_kind: str | None = None, link_ref: str | None = None,
        source: str = "chat", transcript_id: str | None = None,
    ) -> dict:
        """[DEPRECATED → cortxt_session(action='fork')] Fork a child work-pass."""
        s = call("session", "fork", parent_id=parent_id, summary=summary, fork_name=fork_name,
                 link_kind=link_kind, link_ref=link_ref, source=source, transcript_id=transcript_id)
        push_session(s, "fork session")
        return s

    @mcp.tool()
    def cortxt_get_session_tree(root_id: str | None = None) -> list[dict] | dict | None:
        """[DEPRECATED → cortxt_session(action='tree')] Return the session tree nested."""
        return call("session", "tree", root_id=root_id)

    # --- pr (4) → cortxt_pr -----------------------------------------------------
    @mcp.tool()
    def cortxt_list_prs(state: str = "open") -> list[dict]:
        """[DEPRECATED → cortxt_pr(action='list')] List pull requests."""
        return call("pr", "list", state=state)

    @mcp.tool()
    def cortxt_get_pr(number: int) -> dict:
        """[DEPRECATED → cortxt_pr(action='get')] Get PR details with review status."""
        return call("pr", "get", number=number)

    @mcp.tool()
    def cortxt_create_pr(
        title: str, head: str, base: str = "main", body: str = "", draft: bool = False,
    ) -> dict:
        """[DEPRECATED → cortxt_pr(action='create')] Create a pull request."""
        return call("pr", "create", title=title, head=head, base=base, body=body, draft=draft)

    @mcp.tool()
    def cortxt_set_pr_reviewers(number: int, reviewers: list[str]) -> dict:
        """[DEPRECATED → cortxt_pr(action='set_reviewers')] Request reviews on a PR."""
        return call("pr", "set_reviewers", number=number, reviewers=reviewers)

    # --- project (2) → cortxt_project -------------------------------------------
    @mcp.tool()
    def cortxt_list_projects() -> list[dict]:
        """[DEPRECATED → cortxt_project(action='list')] List all catalog entries."""
        return call("project", "list")

    @mcp.tool()
    def cortxt_get_project(slug: str) -> dict:
        """[DEPRECATED → cortxt_project(action='get')] Get one catalog entry by slug."""
        return call("project", "get", slug=slug)

    # --- gh_project (3) → cortxt_gh_project -------------------------------------
    @mcp.tool()
    def cortxt_list_gh_projects() -> list[dict]:
        """[DEPRECATED → cortxt_gh_project(action='list')] List GitHub Projects v2."""
        return call("gh_project", "list")

    @mcp.tool()
    def cortxt_list_gh_project_items(project_id: str, first: int = 30) -> list[dict]:
        """[DEPRECATED → cortxt_gh_project(action='list_items')] List items in a board."""
        return call("gh_project", "list_items", project_id=project_id, first=first)

    @mcp.tool()
    def cortxt_move_gh_project_item(project_id: str, item_id: str, field_id: str, option_id: str) -> dict:
        """[DEPRECATED → cortxt_gh_project(action='move_item')] Move a project item."""
        return call("gh_project", "move_item", project_id=project_id, item_id=item_id,
                    field_id=field_id, option_id=option_id)

    # --- action (3) → cortxt_action ---------------------------------------------
    @mcp.tool()
    def cortxt_list_workflow_runs(workflow_id: str | None = None, limit: int = 10) -> list[dict]:
        """[DEPRECATED → cortxt_action(action='list_runs')] List recent workflow runs."""
        return call("action", "list_runs", workflow_id=workflow_id, limit=limit)

    @mcp.tool()
    def cortxt_trigger_workflow(workflow_id: str, ref: str = "main", inputs: dict | None = None) -> dict:
        """[DEPRECATED → cortxt_action(action='trigger')] Trigger a workflow_dispatch."""
        return call("action", "trigger", workflow_id=workflow_id, ref=ref, inputs=inputs)

    @mcp.tool()
    def cortxt_get_workflow_run(run_id: int) -> dict:
        """[DEPRECATED → cortxt_action(action='get_run')] Get a workflow run's status."""
        return call("action", "get_run", run_id=run_id)

    # --- wiki (3) → cortxt_wiki -------------------------------------------------
    @mcp.tool()
    def cortxt_list_wiki_pages() -> list[dict]:
        """[DEPRECATED → cortxt_wiki(action='list')] List all wiki pages."""
        return call("wiki", "list")

    @mcp.tool()
    def cortxt_read_wiki_page(page: str) -> dict:
        """[DEPRECATED → cortxt_wiki(action='read')] Read a wiki page by name."""
        return call("wiki", "read", page=page)

    @mcp.tool()
    def cortxt_write_wiki_page(page: str, content: str, message: str = "") -> dict:
        """[DEPRECATED → cortxt_wiki(action='write')] Create or update a wiki page."""
        return call("wiki", "write", page=page, content=content, message=message)

    # --- lease (4) → cortxt_lease (owner injiceras, som tidigare) ---------------
    @mcp.tool()
    def cortxt_claim_issue(number: int) -> dict:
        """[DEPRECATED → cortxt_lease(action='claim')] Atomically claim an issue."""
        return call("lease", "claim", number=number, owner=owner())

    @mcp.tool()
    def cortxt_release_issue(number: int) -> dict:
        """[DEPRECATED → cortxt_lease(action='release')] Release your claim on an issue."""
        return call("lease", "release", number=number, owner=owner())

    @mcp.tool()
    def cortxt_heartbeat_issue(number: int) -> dict:
        """[DEPRECATED → cortxt_lease(action='heartbeat')] Renew your claim's TTL."""
        return call("lease", "heartbeat", number=number, owner=owner())

    @mcp.tool()
    def cortxt_list_leases() -> list[dict]:
        """[DEPRECATED → cortxt_lease(action='list')] List all currently held claims."""
        return call("lease", "list")
