"""CNS backend — den läs-API app.cortxt.io konsumerar.

Fyra endpoints med en konsument, plus hälsa, CORS-preflight och GitHub-webhooken.
De 31 rutter som inte hade någon anropare revs 2026-07-13 (serverrenderade lab-sidor,
analyze/review/devwatch/devlog, issues/quests-speglingen, eventstream). Kontraktet mot frontenden
pinnas av `tests/test_api_contract.py` mot inspelningar i `tests/golden/`.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path so scripts.* imports work
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Set working directory to repo root so relative paths in scripts/ resolve
os.chdir(REPO_ROOT)

from flask import Flask, g, jsonify, request  # noqa: E402
from flask_httpauth import HTTPBasicAuth  # noqa: E402

from app.git_ops import git_pull  # noqa: E402
from scripts.json_exporter import export_json  # noqa: E402

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cns-vault-dev-key")

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

auth = HTTPBasicAuth()

USERNAME = os.getenv("CNS_USERNAME", "admin")
PASSWORD = os.getenv("CNS_ADMIN_PASSWORD", "")
GUEST_USERNAME = os.getenv("CNS_GUEST_USERNAME", "guest")
GUEST_PASSWORD = os.getenv("CNS_GUEST_PASSWORD", "")
API_TOKEN = os.getenv("CNS_API_TOKEN", "")


def _is_production() -> bool:
    """True when running on Railway (any RAILWAY_* deploy signal present)."""
    return bool(
        os.getenv("RAILWAY_GIT_COMMIT_SHA")
        or os.getenv("RAILWAY_ENVIRONMENT_NAME")
        or os.getenv("RAILWAY_PROJECT_ID")
    )


@auth.verify_password
def verify_password(username: str, password: str) -> bool:
    # Bearer token check (for React dashboard)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if API_TOKEN and token == API_TOKEN:
            g.role = "admin"
            return True

    # Existing Basic Auth logic
    if not PASSWORD:
        # No admin password configured. Fail OPEN locally (dev convenience),
        # but fail CLOSED in production so @auth.login_required endpoints are
        # never world-open. Set CNS_ADMIN_PASSWORD (or use CNS_API_TOKEN bearer)
        # on Railway to enable admin access there.
        if _is_production():
            return False
        g.role = "admin"
        return True
    if username == USERNAME and password == PASSWORD:
        g.role = "admin"
        return True
    if GUEST_PASSWORD and username == GUEST_USERNAME and password == GUEST_PASSWORD:
        g.role = "guest"
        return True
    return False


def is_admin() -> bool:
    return getattr(g, "role", "guest") == "admin"


def _wants_json() -> bool:
    """Return True when the caller prefers a JSON response (API clients)."""
    return request.headers.get("Accept", "").startswith("application/json")


ALLOWED_ORIGINS = [
    "https://rian010194.github.io",
    "https://app.cortxt.io",
    "https://dashboard-sable-psi-28.vercel.app",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


@app.route("/api/<path:path>", methods=["OPTIONS"])
def handle_options(path):
    response = app.make_default_options_response()
    return add_cors_headers(response)


# ---------------------------------------------------------------------------
# Jinja2 filters
# ---------------------------------------------------------------------------
# Routes — de fyra app.cortxt.io läser, plus hälsa och webhook
# ---------------------------------------------------------------------------


@app.route("/api/nodes")
def api_nodes():
    git_pull()
    path = export_json()
    data = json.loads(path.read_text(encoding="utf-8"))
    # Optional, additive filters (default = full portfolio, unchanged for v2 consumers):
    #   ?domain=juvahem  → only that domain
    #   ?products=1      → only product nodes (is_product, i.e. domain != cortxt)
    domain = request.args.get("domain")
    products = request.args.get("products", "").lower() in ("1", "true", "yes")
    if domain or products:
        nodes = data.get("nodes", [])
        if domain:
            nodes = [n for n in nodes if n.get("domain") == domain]
        if products:
            nodes = [n for n in nodes if n.get("is_product")]
        data["nodes"] = nodes
    return jsonify(data)


@app.route("/api/health")
def api_health():
    # running_sha lets you eyeball what commit Railway currently serves and
    # compare it against GitHub main HEAD — cheap freshness check, no network.
    # (Deeper running-vs-HEAD gap lives in /api/command-center → infra.)
    return jsonify({
        "status": "ok",
        "repo": os.getenv("GITHUB_REPO", "not configured"),
        "running_sha": (os.getenv("RAILWAY_GIT_COMMIT_SHA") or "")[:8] or None,
    })


@app.route("/api/command-center")
def api_command_center():
    """Return the composed Command Center state in one read.

    Wraps scripts.command_center.command_center_state() — the existing composer
    that weaves health + recommend + sessions + quests into one orientation view.
    Read-only and safe to expose publicly; no git_pull (the composer reads cached
    data). Optional ?now=<iso8601> freezes time for testing.

    Returns: {missions, sitrep, logistics, orders, command, freshness}.
    """
    try:
        from scripts.command_center import command_center_state

        now = None
        now_param = request.args.get("now")
        if now_param:
            try:
                from datetime import datetime as _dt
                now = _dt.fromisoformat(now_param)
            except (ValueError, TypeError):
                now = None  # fall back to datetime.now() inside the composer

        return jsonify(command_center_state(now=now))
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/vertical/<slug>")
def api_vertical(slug):
    """Per-vertikal detalj för per-projekt-vyn: roadmap (recept-faser + status/epics +
    öppna beslut) plus vertikal-posten ur command_center. Read-only; degraderar tyst.
    """
    try:
        from scripts.roadmap import roadmap_detail
        from scripts.command_center import _verticals

        vertical = next((v for v in _verticals() if v.get("slug") == slug), None)
        return jsonify({"slug": slug, "vertical": vertical, "roadmap": roadmap_detail(slug)})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/cookbook/<slug>")
def api_cookbook(slug):
    """Read a product's AI-maintained build cookbook (committed JSON), or null if none yet.
    Generation runs offline (`cns cookbook <slug>` / CI), not in this request.
    """
    try:
        from scripts.cookbook import load_cookbook
        return jsonify(load_cookbook(slug) or {"slug": slug, "steps": []})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


# GitHub-webhooken revs 2026-07-13. Den tog emot push/PR/workflow_run, normaliserade dem och
# skrev till en Redis-buffert — vars enda läsare (/api/eventstream/events) revs samma dag. Kedjan
# slutade i tomma intet. Dessutom letade dess slug-extraktion efter filer under `nodes/`, en katalog
# som revs redan i juni, så den kunde inte hitta en enda nod.
#
# Cockpit läser aktivitet via scripts.eventstream.fetch_github_commits, som frågar GitHubs API
# direkt. Den vägen är orörd.
#
# Webhooken måste även tas bort i GitHubs repo-inställningar, annars levererar den mot en 404:a.
