"""Vercel-driftsadapter (#78) — plain REST mot Vercel REST API.

Samma mönster som ``scripts/prs_client.py``: modulfunktioner (ingen klass), ``requests``,
token ur arg eller env (``VERCEL_TOKEN``), plain-dict-retur, **fail-open** utan token
(degraderar, kraschar aldrig ett pass). Skiljer READ-ONLY (connect/find_project/status) från
MUTATING (deploy) — ``deploy`` gatas av anroparen (skriv-läge + godkännande), aldrig i read-läge.

Endpoints (Vercel REST API):
- connect:      GET  /v2/user
- find_project: GET  /v10/projects?repoUrl=<url>
- status:       GET  /v6/deployments?projectId=<id>&limit=1
- deploy:       POST /v13/deployments   (gitSource — git-kopplad app)

Auth: ``Authorization: Bearer <token>``. Valfri team-scope via ``VERCEL_TEAM_ID``.
Statusenum (Vercel): READY | ERROR | BUILDING | QUEUED | INITIALIZING | CANCELED | BLOCKED.
"""
from __future__ import annotations

import os
from typing import Optional

import requests

VERCEL_API = "https://api.vercel.com"
_TIMEOUT = 20


def _resolve_token(token: Optional[str]) -> str:
    return token or os.getenv("VERCEL_TOKEN", "")


def _headers(token: Optional[str] = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {_resolve_token(token)}", "Accept": "application/json"}


def _team_params(token: Optional[str] = None) -> dict[str, str]:
    """Team-scope om ``VERCEL_TEAM_ID`` är satt (personliga konton lämnar tomt)."""
    team = os.getenv("VERCEL_TEAM_ID", "")
    return {"teamId": team} if team else {}


def configured(token: Optional[str] = None) -> bool:
    """Är adaptern konfigurerad (token satt)? Anroparen kan fail-open utan att slå nät."""
    return bool(_resolve_token(token))


def connect(token: Optional[str] = None) -> dict:
    """Verifiera token mot ``GET /v2/user``. Read-only.

    Returnerar ``{"ok": True, "user": <login>}`` vid framgång, annars
    ``{"ok": False, "error": ...}`` — fail-open (kastar aldrig på saknad token / nätfel).
    """
    if not configured(token):
        return {"ok": False, "error": "VERCEL_TOKEN ej satt"}
    try:
        resp = requests.get(
            f"{VERCEL_API}/v2/user",
            headers=_headers(token),
            params=_team_params(token),
            timeout=_TIMEOUT,
        )
        if resp.status_code == 401:
            return {"ok": False, "error": "ogiltig token (401)"}
        resp.raise_for_status()
        user = (resp.json() or {}).get("user", {})
        return {"ok": True, "user": user.get("username") or user.get("email") or user.get("uid", "")}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def find_project(repo_url: str, token: Optional[str] = None) -> Optional[dict]:
    """Slå upp ett Vercel-projekt via dess git-repo (``GET /v10/projects?repoUrl=``).

    Returnerar ``{"id", "name"}`` för första träffen, eller ``None`` (ej hittat / ej konfig).
    """
    if not configured(token):
        return None
    try:
        params = {"repoUrl": repo_url, "limit": 1, **_team_params(token)}
        resp = requests.get(
            f"{VERCEL_API}/v10/projects",
            headers=_headers(token),
            params=params,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        projects = (resp.json() or {}).get("projects") or []
        if not projects:
            return None
        p = projects[0]
        return {"id": p.get("id", ""), "name": p.get("name", "")}
    except requests.RequestException:
        return None


def status(project: str, token: Optional[str] = None) -> dict:
    """Senaste deployment-status för ett projekt (``GET /v6/deployments``). Read-only.

    ``project`` = Vercel-projekt-id eller -namn. Returnerar
    ``{"ok": True, "state": "READY", "url": ..., "created": ...}`` eller
    ``{"ok": False, "error": ...}`` — fail-open.
    """
    if not configured(token):
        return {"ok": False, "error": "VERCEL_TOKEN ej satt"}
    try:
        params = {"projectId": project, "limit": 1, **_team_params(token)}
        resp = requests.get(
            f"{VERCEL_API}/v6/deployments",
            headers=_headers(token),
            params=params,
            timeout=_TIMEOUT,
        )
        if resp.status_code == 404:
            return {"ok": False, "error": f"projekt '{project}' hittades inte"}
        resp.raise_for_status()
        deployments = (resp.json() or {}).get("deployments") or []
        if not deployments:
            return {"ok": True, "state": "NONE", "url": "", "created": 0}
        d = deployments[0]
        return {
            "ok": True,
            "state": d.get("state") or d.get("readyState") or "UNKNOWN",
            "url": d.get("url", ""),
            "created": d.get("created", 0),
        }
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def deploy(
    project: str,
    *,
    ref: str = "main",
    repo_id: Optional[str] = None,
    git_type: str = "github",
    token: Optional[str] = None,
) -> dict:
    """Trigga en ny deployment (``POST /v13/deployments``, gitSource). **MUTATING.**

    Anropas ALDRIG i read-läge — anroparen (CLI/dispatch) gatar bakom skriv-läge +
    explicit godkännande (samma anda som github-skriv #128). Fail-open vid nätfel.
    """
    if not configured(token):
        return {"ok": False, "error": "VERCEL_TOKEN ej satt"}
    git_source: dict = {"type": git_type, "ref": ref}
    if repo_id:
        git_source["repoId"] = repo_id
    body = {"name": project, "gitSource": git_source}
    try:
        resp = requests.post(
            f"{VERCEL_API}/v13/deployments",
            headers={**_headers(token), "Content-Type": "application/json"},
            params=_team_params(token),
            json=body,
            timeout=_TIMEOUT,
        )
        if resp.status_code == 401:
            return {"ok": False, "error": "ogiltig token (401)"}
        resp.raise_for_status()
        d = resp.json() or {}
        return {"ok": True, "uid": d.get("uid", ""), "state": d.get("state", "QUEUED"), "url": d.get("url", "")}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}
