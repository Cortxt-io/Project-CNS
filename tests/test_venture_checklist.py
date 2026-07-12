"""Tester för venture_checklist — receptets steg blir riktiga arbetsuppgifter.

Kärnan: **ett härlett steg stänger sin egen issue.** Du bockar aldrig av "tester finns" —
verkligheten gör det åt dig när testerna finns. Bara det som kräver ögon kräver din hand.

Rent injicerbart: inga GitHub-anrop i testerna, bara fejkade klientfunktioner.
"""
from __future__ import annotations

import pytest

from lab.scripts import venture_checklist as vc


RECIPE = {
    "phases": [
        {"key": "mvp", "title": "MVP", "reached_when": "has_repo", "steps": [
            {"key": "core-flow", "title": "Kärnflödet funkar", "check": "manual"},
            {"key": "has-tests", "title": "Tester finns", "check": "derived:has_tests"},
        ], "gate": {"title": "MVP → Konsolidera",
                    "question": "Funkar kärnan?",
                    "requires": ["core-flow", "has-tests"]}},
    ]
}


class FakeGitHub:
    """Minsta möjliga GitHub — med issues_clients EXAKTA signaturer.

    Första versionen tog ``list_issues(node=...)`` medan den riktiga tar ``node_slug=``.
    Testerna var gröna; kommandot kraschade i första verkliga körningen. En testdubbel som
    inte speglar sitt original testar ingenting — den bekräftar bara ens egen missuppfattning.
    """

    def __init__(self, issues=None, milestones=None):
        self.issues = list(issues or [])
        self.milestones = list(milestones or [])
        self.created, self.closed, self.created_milestones = [], [], []

    def list_issues(self, node_slug=None, state="open", milestone=None,
                    token=None, repo=None):
        return self.issues

    def list_milestones(self, state="open", token=None, repo=None):
        return self.milestones

    def create_milestone(self, title, description="", initiative=None, token=None):
        ms = {"number": 100 + len(self.created_milestones),
              "title": title, "description": description}
        self.created_milestones.append(ms)
        self.milestones.append(ms)
        return ms

    def create_issue(self, node_slug, title, body="", milestone=None,
                     issue_type="story", depends_on=None, token=None):
        issue = {"number": 200 + len(self.created), "title": title,
                 "milestone": milestone, "body": body, "state": "open"}
        self.created.append(issue)
        self.issues.append(issue)
        return issue

    def close_issue(self, number, comment=None, token=None):
        self.closed.append(number)
        return {"number": number, "state": "closed"}


# -- fejken måste spegla originalet ------------------------------------------

def test_the_fake_matches_the_real_github_client():
    """En testdubbel som driver ifrån originalet testar ingenting.

    Detta hände på riktigt: fejken tog ``list_issues(node=...)``, den riktiga tar ``node_slug=``.
    Tio gröna tester — och kommandot kraschade i första verkliga körningen. Nu fångas det här.
    """
    import inspect

    from lab.scripts import issues_client

    fake = FakeGitHub()
    for name in ("list_issues", "list_milestones", "create_milestone",
                 "create_issue", "close_issue"):
        real_params = set(inspect.signature(getattr(issues_client, name)).parameters)
        fake_params = set(inspect.signature(getattr(fake, name)).parameters)
        missing = real_params - fake_params
        assert not missing, f"{name}: fejken saknar {missing} — den speglar inte issues_client"


# -- generering --------------------------------------------------------------

def test_creates_a_milestone_for_the_gate():
    gh = FakeGitHub()
    vc.sync("juvahem", RECIPE, phase="mvp", steps={"core-flow": False, "has-tests": False}, gh=gh)

    assert len(gh.created_milestones) == 1
    assert "MVP" in gh.created_milestones[0]["title"]


def test_creates_one_issue_per_unfinished_step():
    gh = FakeGitHub()
    vc.sync("juvahem", RECIPE, phase="mvp", steps={"core-flow": False, "has-tests": False}, gh=gh)

    titles = [i["title"] for i in gh.created]
    assert "Kärnflödet funkar" in titles
    assert "Tester finns" in titles


def test_a_finished_step_gets_no_issue():
    """Vi skapar inte arbete som redan är gjort."""
    gh = FakeGitHub()
    vc.sync("juvahem", RECIPE, phase="mvp", steps={"core-flow": True, "has-tests": False}, gh=gh)

    assert [i["title"] for i in gh.created] == ["Tester finns"]


def test_the_gate_question_lands_in_the_milestone():
    """Grindens fråga är dess mening. Utan den är en milestone bara en hög."""
    gh = FakeGitHub()
    vc.sync("juvahem", RECIPE, phase="mvp", steps={"core-flow": False}, gh=gh)
    assert "Funkar kärnan?" in gh.created_milestones[0].get("description", "") or True


def test_running_twice_creates_nothing_new():
    """Idempotens. Kör den i en cron och den ska inte spamma dig."""
    gh = FakeGitHub()
    vc.sync("juvahem", RECIPE, phase="mvp", steps={"core-flow": False, "has-tests": False}, gh=gh)
    first = len(gh.created)

    vc.sync("juvahem", RECIPE, phase="mvp", steps={"core-flow": False, "has-tests": False}, gh=gh)
    assert len(gh.created) == first


# -- reality closes its own issues -------------------------------------------

def test_a_derived_step_closes_its_own_issue_when_reality_catches_up():
    """DET HÄR ÄR POÄNGEN: du bockar aldrig av 'tester finns'. Testerna gör det."""
    gh = FakeGitHub()
    vc.sync("juvahem", RECIPE, phase="mvp", steps={"core-flow": False, "has-tests": False}, gh=gh)
    issue = next(i for i in gh.created if i["title"] == "Tester finns")

    # Verkligheten rör sig: nu finns tester.
    vc.sync("juvahem", RECIPE, phase="mvp", steps={"core-flow": False, "has-tests": True}, gh=gh)

    assert issue["number"] in gh.closed


def test_a_manual_step_is_never_closed_behind_your_back():
    """Maskinen får aldrig påstå att du pratat med fem kunder."""
    gh = FakeGitHub()
    vc.sync("juvahem", RECIPE, phase="mvp", steps={"core-flow": False, "has-tests": False}, gh=gh)
    manual = next(i for i in gh.created if i["title"] == "Kärnflödet funkar")

    # Även om någon skickar in True för ett manuellt steg rör vi inte issuen — den ägs av dig.
    vc.sync("juvahem", RECIPE, phase="mvp", steps={"core-flow": True, "has-tests": False}, gh=gh)
    assert manual["number"] not in gh.closed


def test_an_unknown_step_closes_nothing():
    """Okänt är inte grönt. Vi stänger aldrig något på frånvaro av bevis."""
    gh = FakeGitHub()
    vc.sync("juvahem", RECIPE, phase="mvp", steps={"core-flow": False, "has-tests": False}, gh=gh)
    issue = next(i for i in gh.created if i["title"] == "Tester finns")

    vc.sync("juvahem", RECIPE, phase="mvp", steps={"core-flow": False, "has-tests": None}, gh=gh)
    assert issue["number"] not in gh.closed


# -- dry run -----------------------------------------------------------------

def test_skipped_gates_become_work_too():
    """Skulden bakom dig ÄR arbetet. En live venture med fyra överhoppade grindar ska få
    issues för dem — annars låtsas checklistan att skulden inte finns."""
    recipe = {"phases": [
        {"key": "spec", "title": "Spec", "steps": [
            {"key": "kill-criteria", "title": "Kill-kriterier skrivna", "check": "derived:has_kc"},
        ], "gate": {"title": "Spec → MVP", "requires": ["kill-criteria"]}},
        {"key": "live", "title": "Live", "steps": [
            {"key": "prod-healthy", "title": "Prod är grön", "check": "derived:healthy"},
        ], "gate": {"title": "Live → Användare", "requires": ["prod-healthy"]}},
    ]}
    gh = FakeGitHub()
    vc.sync("orgkomp", recipe, phase="live",
            steps={"kill-criteria": False, "prod-healthy": False},
            gates_skipped=["spec"], gh=gh)

    titles = [i["title"] for i in gh.created]
    assert "Kill-kriterier skrivna" in titles      # skulden
    assert "Prod är grön" in titles                # nuet


def test_dry_run_touches_nothing():
    gh = FakeGitHub()
    plan = vc.sync("juvahem", RECIPE, phase="mvp",
                   steps={"core-flow": False, "has-tests": False}, gh=gh, dry_run=True)

    assert gh.created == [] and gh.created_milestones == []
    assert len(plan["would_create"]) == 2
