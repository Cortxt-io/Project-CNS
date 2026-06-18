"""Tester för Vercel-driftsadaptern (#78) — injicerad transport, inget nät.

Mönster som test_dispatch: ingen mock-lib, en liten fejk-respons + monkeypatch av
``requests``. Verifierar fail-open utan token, status-parsing, och deploy-body-formen.
"""
from __future__ import annotations

import pytest

from scripts.adapters import vercel


class _FakeResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise vercel.requests.HTTPError(f"status {self.status_code}")


@pytest.fixture(autouse=True)
def _no_token(monkeypatch):
    """Default: ingen token i env (tester sätter själva när de vill ha en)."""
    monkeypatch.delenv("VERCEL_TOKEN", raising=False)
    monkeypatch.delenv("VERCEL_TEAM_ID", raising=False)


# --- fail-open utan token -------------------------------------------------

def test_connect_without_token_is_fail_open():
    out = vercel.connect()
    assert out == {"ok": False, "error": "VERCEL_TOKEN ej satt"}


def test_status_without_token_is_fail_open():
    out = vercel.status("cortxt-dashboard")
    assert out["ok"] is False


def test_find_project_without_token_returns_none():
    assert vercel.find_project("https://github.com/x/y") is None


def test_configured_reflects_token(monkeypatch):
    assert vercel.configured() is False
    monkeypatch.setenv("VERCEL_TOKEN", "tok")
    assert vercel.configured() is True


# --- connect --------------------------------------------------------------

def test_connect_ok(monkeypatch):
    monkeypatch.setenv("VERCEL_TOKEN", "tok")
    monkeypatch.setattr(vercel.requests, "get",
                        lambda *a, **k: _FakeResp(200, {"user": {"username": "rian"}}))
    assert vercel.connect() == {"ok": True, "user": "rian"}


def test_connect_401(monkeypatch):
    monkeypatch.setenv("VERCEL_TOKEN", "bad")
    monkeypatch.setattr(vercel.requests, "get", lambda *a, **k: _FakeResp(401))
    out = vercel.connect()
    assert out["ok"] is False and "401" in out["error"]


# --- status ---------------------------------------------------------------

def test_status_parses_latest_deployment(monkeypatch):
    monkeypatch.setenv("VERCEL_TOKEN", "tok")
    payload = {"deployments": [{"state": "READY", "url": "x.vercel.app", "created": 123}]}
    monkeypatch.setattr(vercel.requests, "get", lambda *a, **k: _FakeResp(200, payload))
    out = vercel.status("cortxt-dashboard")
    assert out == {"ok": True, "state": "READY", "url": "x.vercel.app", "created": 123}


def test_status_no_deployments(monkeypatch):
    monkeypatch.setenv("VERCEL_TOKEN", "tok")
    monkeypatch.setattr(vercel.requests, "get", lambda *a, **k: _FakeResp(200, {"deployments": []}))
    out = vercel.status("p")
    assert out["ok"] is True and out["state"] == "NONE"


def test_status_404(monkeypatch):
    monkeypatch.setenv("VERCEL_TOKEN", "tok")
    monkeypatch.setattr(vercel.requests, "get", lambda *a, **k: _FakeResp(404))
    out = vercel.status("missing")
    assert out["ok"] is False and "hittades inte" in out["error"]


# --- find_project ---------------------------------------------------------

def test_find_project_first_hit(monkeypatch):
    monkeypatch.setenv("VERCEL_TOKEN", "tok")
    payload = {"projects": [{"id": "prj_1", "name": "cortxt-dashboard"}]}
    monkeypatch.setattr(vercel.requests, "get", lambda *a, **k: _FakeResp(200, payload))
    assert vercel.find_project("https://github.com/Cortxt-io/cortxt") == {
        "id": "prj_1", "name": "cortxt-dashboard"}


# --- deploy (mutating) ----------------------------------------------------

def test_deploy_builds_gitsource_body(monkeypatch):
    monkeypatch.setenv("VERCEL_TOKEN", "tok")
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return _FakeResp(200, {"uid": "dpl_1", "state": "QUEUED", "url": "x.vercel.app"})

    monkeypatch.setattr(vercel.requests, "post", fake_post)
    out = vercel.deploy("cortxt-dashboard", ref="main", repo_id="42")
    assert out == {"ok": True, "uid": "dpl_1", "state": "QUEUED", "url": "x.vercel.app"}
    assert captured["url"].endswith("/v13/deployments")
    assert captured["json"]["name"] == "cortxt-dashboard"
    assert captured["json"]["gitSource"] == {"type": "github", "ref": "main", "repoId": "42"}
