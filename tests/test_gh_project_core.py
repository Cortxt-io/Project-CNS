"""Tester för org-fixen i scripts/tools/gh_project_core.py (port av #120).

Verifierar att ``gh_project(action="list")`` är robust mot ett user-konto: en
``organization(login:)``-fråga mot ett user-login reser ett GraphQL-fel, och
verktyget ska då falla igenom till user-frågan i stället för att krascha. Det är
buggen ``_graphql_safe`` löser — den gamla strikta ``_graphql`` gjorde den
efterföljande user-fallbacken till död kod.
"""
from __future__ import annotations

import pytest

from scripts.tools import gh_project_core as core


def test_project_owner_prefers_env(monkeypatch):
    monkeypatch.setenv("CNS_PROJECT_OWNER", "Cortxt-io")
    monkeypatch.setenv("GITHUB_REPO", "someuser/Project-CNS")
    assert core._project_owner() == "Cortxt-io"


def test_project_owner_falls_back_to_repo_owner(monkeypatch):
    monkeypatch.delenv("CNS_PROJECT_OWNER", raising=False)
    monkeypatch.setenv("GITHUB_REPO", "someuser/Project-CNS")
    assert core._project_owner() == "someuser"


def test_graphql_safe_swallows_value_error(monkeypatch):
    def boom(query, variables=None):
        raise ValueError("Could not resolve to an Organization with the login")

    monkeypatch.setattr(core, "_graphql", boom)
    assert core._graphql_safe("q") is None


def test_graphql_safe_propagates_network_error(monkeypatch):
    def boom(query, variables=None):
        raise ConnectionError("network down")

    monkeypatch.setattr(core, "_graphql", boom)
    with pytest.raises(ConnectionError):
        core._graphql_safe("q")


def test_list_falls_through_to_user_account(monkeypatch):
    """Org-frågan reser (login är ett user-konto) → faller igenom till user-frågan."""
    monkeypatch.setenv("CNS_PROJECT_OWNER", "someuser")

    def fake_graphql(query, variables=None):
        if "organization(login" in query:
            # GitHub reser ett GraphQL-fel mot ett user-konto.
            raise ValueError("Could not resolve to an Organization with the login of 'someuser'")
        if "user(login" in query:
            return {"user": {"projectsV2": {"nodes": [
                {"id": "PVT_1", "number": 1, "title": "Backlog", "url": "u", "closed": False},
                {"id": "PVT_2", "number": 2, "title": "Old", "url": "u", "closed": True},
            ]}}}
        raise AssertionError(f"oväntad query: {query[:40]}")

    monkeypatch.setattr(core, "_graphql", fake_graphql)
    projects = core.gh_project("list")
    assert [p["title"] for p in projects] == ["Backlog"]  # closed filtreras bort


def test_list_uses_org_when_present(monkeypatch):
    monkeypatch.setenv("CNS_PROJECT_OWNER", "Cortxt-io")

    def fake_graphql(query, variables=None):
        if "organization(login" in query:
            return {"organization": {"projectsV2": {"nodes": [
                {"id": "PVT_9", "number": 9, "title": "Backlog", "url": "u", "closed": False},
            ]}}}
        raise AssertionError("user-frågan skulle inte nås när orgen har projekt")

    monkeypatch.setattr(core, "_graphql", fake_graphql)
    projects = core.gh_project("list")
    assert [p["id"] for p in projects] == ["PVT_9"]
