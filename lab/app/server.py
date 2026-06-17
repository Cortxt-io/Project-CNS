"""CNS Vault – Flask web application for CNS portfolio management."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

# Ensure repo root is on sys.path so scripts.* imports work
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Set working directory to repo root so relative paths in scripts/ resolve
os.chdir(REPO_ROOT)

import markdown as md_lib  # noqa: E402
from flask import (  # noqa: E402
    Flask,
    after_this_request,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_httpauth import HTTPBasicAuth  # noqa: E402

from app.git_ops import (  # noqa: E402
    configure_git,
    delete_file_on_github,
    git_commit_and_push,
    git_pull,
    push_file_immediately,
    read_file_from_github,
)
from scripts.analyst import load_pending_suggestions, run_analyze, _call_claude, _read_node_context, _get_devwatch_context  # noqa: E402
from scripts.portfolio_brief import run_portfolio_brief  # noqa: E402
from scripts.json_exporter import export_json  # noqa: E402
from scripts.devwatch import run_devwatch, DevwatchError  # noqa: E402
from scripts.devlog import run_devlog  # noqa: E402
from scripts.md_parser import (  # noqa: E402
    SECTIONS,
    apply_changes,
    node_dir,
    node_path,
    read_all_nodes,
    read_node,
    write_node,
)
from scripts.issues_client import (  # noqa: E402
    list_issues as ic_list_issues,
    get_issue as ic_get_issue,
    create_issue as ic_create_issue,
    close_issue as ic_close_issue,
    list_milestones as ic_list_milestones,
    get_milestone as ic_get_milestone,
    create_milestone as ic_create_milestone,
    close_milestone as ic_close_milestone,
)

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


@auth.verify_password
def verify_password(username: str, password: str) -> bool:
    # Bearer token check (for React dashboard)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if API_TOKEN and token == API_TOKEN:
            g.role = "admin"
            return True

    # Existing Basic Auth logic (unchanged)
    if not PASSWORD:
        # Dev mode – no password set, allow all
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

STATUS_LABELS = {
    "idea": "Idé",
    "active": "Aktiv",
    "early_mvp": "Tidig MVP",
    "mvp": "MVP",
    "live": "Live",
    "shelved": "Vilande",
}

STAGE_LABELS = {
    "hypothesis": "Hypotes",
    "problem_interviews": "Problemintervjuer",
    "solution_test": "Lösningstest",
    "demand_test": "Efterfrågetest",
    "launch": "Lansering",
}

FAMILY_LABELS = {
    "developer-tools": "Developer Tools",
    "digest-pipeline": "Digest Pipeline",
    "internal-monitoring": "Internal Monitoring",
    "cns-core": "CNS Core",
    "ideas": "Ideas",
}

STATUS_BADGE_CLASSES = {
    "idea": "bg-slate-100 text-slate-600 border border-slate-200",
    "active": "bg-blue-50 text-blue-700 border border-blue-200",
    "early_mvp": "bg-amber-50 text-amber-700 border border-amber-200",
    "mvp": "bg-emerald-50 text-emerald-700 border border-emerald-200",
    "live": "bg-emerald-100 text-emerald-800 border border-emerald-300 font-bold",
    "shelved": "bg-rose-50 text-rose-700 border border-rose-200",
}


def _status_label(status: Any) -> str:
    if not status:
        return ""
    return STATUS_LABELS.get(str(status), str(status))


def _stage_label(stage: Any) -> str:
    if not stage:
        return ""
    return STAGE_LABELS.get(str(stage), str(stage))


def _family_label(family: Any) -> str:
    if not family:
        return ""
    return FAMILY_LABELS.get(str(family), str(family))


def _status_badge_class(status: Any) -> str:
    if not status:
        return "bg-gray-100 text-gray-600"
    return STATUS_BADGE_CLASSES.get(str(status), "bg-gray-100 text-gray-600")


def _roi_class(roi: Any) -> str:
    if not roi:
        return "text-gray-400 font-semibold"
    if roi >= 250:
        return "text-emerald-700 font-bold"
    if roi > 0:
        return "text-amber-700 font-bold"
    return "text-gray-400 font-semibold"


def _format_sek(value: Any) -> str:
    if not value and value != 0:
        return "–"
    try:
        return f"{int(value):,}".replace(",", " ")
    except (ValueError, TypeError):
        return str(value)


def _md_to_html(text: Any) -> str:
    if not text:
        return ""
    return md_lib.markdown(str(text), extensions=["extra", "nl2br"])


app.jinja_env.filters["status_label"] = _status_label
app.jinja_env.filters["stage_label"] = _stage_label
app.jinja_env.filters["family_label"] = _family_label
app.jinja_env.filters["status_badge_class"] = _status_badge_class
app.jinja_env.filters["roi_class"] = _roi_class
app.jinja_env.filters["format_sek"] = _format_sek
app.jinja_env.filters["md_to_html"] = _md_to_html

# ---------------------------------------------------------------------------
# Helper: read node subdirectory files
# ---------------------------------------------------------------------------


def _read_node_files(slug: str) -> dict[str, list[tuple[str, str]]]:
    """Read markdown files from planning/, notes/, research/ subdirs.

    Returns: {subdir_name: [(filename, content), ...]}
    Skips README.md and empty files.
    """
    pdir = node_dir(slug)
    result: dict[str, list[tuple[str, str]]] = {}
    for subdir in ("planning", "notes", "research"):
        files: list[tuple[str, str]] = []
        subpath = pdir / subdir
        if not subpath.exists():
            continue
        for md_file in sorted(subpath.glob("*.md")):
            if md_file.name.lower() == "readme.md":
                continue
            content = md_file.read_text(encoding="utf-8").strip()
            if not content:
                continue
            files.append((md_file.name, content))
        if files:
            result[subdir] = files
    return result


# ---------------------------------------------------------------------------
# Helpers: exports / devlog / devwatch
# ---------------------------------------------------------------------------


def _latest_export(pattern: str) -> Path | None:
    """Find the most recent file in REPO_ROOT/exports matching a glob pattern.

    Returns the Path with the highest alphabetical (i.e. latest date) name,
    or None if no files match.
    """
    exports_dir = REPO_ROOT / "exports"
    if not exports_dir.exists():
        return None
    matches = sorted(exports_dir.glob(pattern))
    return matches[-1] if matches else None


def _extract_devlog_body_from_string(html: str) -> str:
    """Extract inner HTML from <main> or <body> of a devlog HTML string.

    Returns empty string if unparsable.
    """
    # Try <main> first
    m = re.search(r"<main[^>]*>(.*?)</main>", html, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Fallback to <body>
    m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def _extract_devlog_body(html_path: Path | None) -> str:
    """Extract inner HTML from <main> or <body> of a devlog HTML file.

    Returns empty string if file is missing or unparsable.
    """
    if not html_path or not html_path.exists():
        return ""
    try:
        html = html_path.read_text(encoding="utf-8")
        return _extract_devlog_body_from_string(html)
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Routes – UI
# ---------------------------------------------------------------------------


@app.route("/")
@auth.login_required
def index():
    git_pull()

    all_nodes = read_all_nodes()
    nodes_data = []
    for meta, sections in all_nodes:
        nodes_data.append(meta)

    # Aggregate stats
    total = len(nodes_data)
    active = sum(
        1 for p in nodes_data if p.get("status") in ("active", "early_mvp", "mvp", "live")
    )
    total_cost = sum(p.get("cost_sek", 0) or 0 for p in nodes_data)
    total_value = sum(p.get("value_sek", 0) or 0 for p in nodes_data)
    with_roi = [p for p in nodes_data if (p.get("roi_percent") or 0) > 0]
    avg_roi = (
        round(sum(p.get("roi_percent", 0) or 0 for p in with_roi) / len(with_roi))
        if with_roi
        else 0
    )

    # Collect unique values for filters
    statuses = sorted(set(p.get("status", "") for p in nodes_data if p.get("status")))
    all_tags: list[str] = []
    for p in nodes_data:
        all_tags.extend(p.get("tags", []) or [])
    tags = sorted(set(all_tags))
    families = sorted(set(p.get("family", "") for p in nodes_data if p.get("family")))

    # Query params for filtering
    status_filter = request.args.get("status", "").split(",") if request.args.get("status") else []
    status_filter = [s for s in status_filter if s]
    tag_filter = request.args.get("tag", "").split(",") if request.args.get("tag") else []
    tag_filter = [t for t in tag_filter if t]
    family_filter = request.args.get("family", "")
    search_query = request.args.get("q", "").lower()
    sort_field = request.args.get("sort", "title")
    sort_dir = request.args.get("dir", "asc")
    view_mode = request.args.get("view", "table")

    # Apply filters
    filtered = nodes_data[:]
    if status_filter:
        filtered = [p for p in filtered if p.get("status") in status_filter]
    if tag_filter:
        filtered = [
            p
            for p in filtered
            if any(t in (p.get("tags", []) or []) for t in tag_filter)
        ]
    if family_filter:
        filtered = [p for p in filtered if p.get("family") == family_filter]
    if search_query:
        filtered = [
            p
            for p in filtered
            if search_query in (p.get("title", "") or "").lower()
            or search_query in (p.get("slug", "") or "").lower()
            or search_query in " ".join(p.get("tags", []) or []).lower()
        ]

    # Sort
    sort_key = sort_field
    if sort_key == "roi_percent":
        filtered.sort(key=lambda p: p.get("roi_percent", 0) or 0, reverse=(sort_dir != "asc"))
    elif sort_key == "cost_sek":
        filtered.sort(key=lambda p: p.get("cost_sek", 0) or 0, reverse=(sort_dir != "asc"))
    elif sort_key == "value_sek":
        filtered.sort(key=lambda p: p.get("value_sek", 0) or 0, reverse=(sort_dir != "asc"))
    else:
        filtered.sort(key=lambda p: (p.get("title", "") or "").lower(), reverse=(sort_dir != "asc"))

    return render_template(
        "index.html",
        nodes=filtered,
        stats={
            "total": total,
            "active": active,
            "total_cost": total_cost,
            "total_value": total_value,
            "avg_roi": avg_roi,
        },
        statuses=statuses,
        tags=tags,
        families=families,
        status_filter=status_filter,
        tag_filter=tag_filter,
        family_filter=family_filter,
        search_query=search_query,
        sort_field=sort_field,
        sort_dir=sort_dir,
        view_mode=view_mode,
        is_admin=is_admin(),
    )


@app.route("/node/<slug>")
@auth.login_required
def node_detail(slug):
    git_pull()

    try:
        meta, sections, raw = read_node(slug)
    except FileNotFoundError:
        return render_template(
            "node.html",
            error="not_found",
            slug=slug,
            meta=None,
            sections={},
            section_order=[],
            node_files={},
            has_pending=False,
            is_admin=is_admin(),
        ), 404

    node_files = _read_node_files(slug)

    # Check if there are pending suggestions for this node
    has_pending = any(
        p["slug"] == slug for p in load_pending_suggestions()
    )

    return render_template(
        "node.html",
        meta=meta,
        sections=sections,
        section_order=SECTIONS,
        node_files=node_files,
        has_pending=has_pending,
        slug=slug,
        error=None,
        is_admin=is_admin(),
    )


@app.route("/review")
@auth.login_required
def review():
    git_pull()

    slug_filter = request.args.get("slug", "")
    pending = load_pending_suggestions()

    if slug_filter:
        pending = [p for p in pending if p["slug"] == slug_filter]

    # Enrich with current node data for diff display
    enriched = []
    for item in pending:
        try:
            meta, sections, _ = read_node(item["slug"])
        except FileNotFoundError:
            meta = {}
            sections = {}
        enriched.append({**item, "current_meta": meta, "current_sections": sections})

    return render_template(
        "review.html",
        pending=enriched,
        slug_filter=slug_filter,
        is_admin=is_admin(),
    )


@app.route("/activity")
@auth.login_required
def activity():
    git_pull()

    devwatch_events: list[dict[str, Any]] = []
    devwatch_meta: dict[str, Any] = {}
    devwatch_date = ""
    no_activity = True

    # Read devwatch from GitHub
    devwatch_raw = read_file_from_github(
        "nodes/project-vault-dashboard/dashboard/data/devwatch_latest.json"
    )
    if devwatch_raw:
        try:
            data = json.loads(devwatch_raw)
            devwatch_events = data.get("events", [])
            devwatch_meta = data.get("meta", {})
            devwatch_date = data.get("exported_at", "")
            no_activity = not devwatch_events
        except Exception:
            pass

    # Read devlog from GitHub
    devlog_html = ""
    devlog_raw = read_file_from_github(
        "nodes/project-vault-dashboard/dashboard/data/devlog_latest.html"
    )
    if devlog_raw:
        devlog_html = _extract_devlog_body_from_string(devlog_raw)
        no_activity = no_activity and not devlog_html

    return render_template(
        "activity.html",
        devwatch_events=devwatch_events,
        devwatch_meta=devwatch_meta,
        devwatch_date=devwatch_date,
        devlog_html=devlog_html,
        no_activity=no_activity,
        is_admin=is_admin(),
    )


@app.route("/analyze")
@auth.login_required
def analyze():
    git_pull()

    all_nodes = read_all_nodes()
    nodes_data = []
    for meta, _sections in all_nodes:
        nodes_data.append(meta)

    # Load latest devwatch to find changed slugs
    devwatch_path = _latest_export("devwatch_*.json")
    changed_slugs: set[str] = set()
    if devwatch_path:
        try:
            data = json.loads(devwatch_path.read_text(encoding="utf-8"))
            for event in data.get("events", []):
                slug = event.get("meta", {}).get("slug")
                if slug:
                    changed_slugs.add(slug)
        except Exception:
            pass

    # Load pending suggestions grouped by slug
    pending_list = load_pending_suggestions()
    pending_by_slug: dict[str, dict[str, Any]] = {}
    for p in pending_list:
        pending_by_slug[p["slug"]] = p

    # Build node list with analysis state
    node_list = []
    for meta in nodes_data:
        slug = meta.get("slug", "")
        pending = pending_by_slug.get(slug)
        has_pending = pending is not None
        node_list.append({
            "meta": meta,
            "has_pending": has_pending,
            "pending_count": len(pending["suggestions"]) if has_pending else 0,
            "last_analyzed": pending.get("analyzed_at") if has_pending else None,
            "changed_in_devwatch": slug in changed_slugs,
        })

    # Sort: changed first, then pending, then alphabetically
    node_list.sort(
        key=lambda p: (
            not p["changed_in_devwatch"],
            not p["has_pending"],
            (p["meta"].get("title") or "").lower(),
        )
    )

    total_pending = sum(p["pending_count"] for p in node_list)

    return render_template(
        "analyze.html",
        node_list=node_list,
        total_pending=total_pending,
        is_admin=is_admin(),
    )


# ---------------------------------------------------------------------------
# Routes – API
# ---------------------------------------------------------------------------


@app.route("/api/analyze")
@auth.login_required
def api_analyze_list():
    if not is_admin():
        return jsonify({"status": "error", "message": "Admin required"}), 403

    all_nodes = read_all_nodes()
    pending_list = load_pending_suggestions()
    pending_by_slug = {p["slug"]: p for p in pending_list}

    node_list = []
    for meta, _ in all_nodes:
        slug = meta.get("slug", "")
        pending = pending_by_slug.get(slug)
        node_list.append({
            "slug": slug,
            "title": meta.get("title", slug),
            "status": meta.get("status", ""),
            "updated": meta.get("updated", ""),
            "has_pending": pending is not None,
            "pending_count": len(pending["suggestions"]) if pending else 0,
            "last_analyzed": pending.get("analyzed_at") if pending else None,
        })

    node_list.sort(key=lambda p: (
        not p["has_pending"],
        (p["title"] or "").lower()
    ))

    return jsonify({"nodes": node_list})


@app.route("/api/analyze/<slug>", methods=["POST"])
@auth.login_required
def api_analyze(slug):
    if not is_admin():
        return jsonify({"status": "error", "message": "Guests cannot perform this action"}), 403

    git_pull()

    try:
        output_path = (
            Path("exports")
            / f"analyze_{slug}_{date.today().isoformat()}.json"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = run_analyze(
            slug,
            confirm_fn=None,
            output_path=output_path,
        )

        if result and output_path.exists():
            # Count suggestions from the saved file
            data = json.loads(output_path.read_text(encoding="utf-8"))
            count = len(data.get("suggestions", {}))

            # Push the analyze JSON immediately — bypasses Railway ephemeral disk
            ok, msg = push_file_immediately(
                output_path,
                f"cns-vault: analyze {slug}",
            )
            if not ok:
                app.logger.warning("Failed to push analyze JSON for %s: %s", slug, msg)

            return jsonify({"status": "ok", "suggestions_count": count})
        else:
            return jsonify({"status": "ok", "suggestions_count": 0})

    except FileNotFoundError:
        return jsonify({"status": "error", "message": f"Node '{slug}' not found"}), 404
    except RuntimeError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/analyze/all", methods=["POST"])
@auth.login_required
def api_analyze_all():
    if not is_admin():
        return jsonify({"status": "error", "message": "Guests cannot perform this action"}), 403

    git_pull()

    devwatch_path = _latest_export("devwatch_*.json")
    changed_slugs: set[str] = set()
    if devwatch_path:
        try:
            data = json.loads(devwatch_path.read_text(encoding="utf-8"))
            for event in data.get("events", []):
                slug = event.get("meta", {}).get("slug")
                if slug:
                    changed_slugs.add(slug)
        except Exception:
            pass

    analyzed: list[str] = []
    errors: dict[str, str] = {}

    for slug in sorted(changed_slugs):
        try:
            output_path = (
                Path("exports")
                / f"analyze_{slug}_{date.today().isoformat()}.json"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)

            result = run_analyze(
                slug,
                confirm_fn=None,
                output_path=output_path,
            )

            if result and output_path.exists():
                analyzed.append(slug)
                push_ok, push_msg = push_file_immediately(
                    output_path,
                    f"cns-vault: analyze {slug}",
                )
                if not push_ok:
                    app.logger.warning("Failed to push analyze JSON for %s: %s", slug, push_msg)
            else:
                analyzed.append(slug)
        except FileNotFoundError:
            errors[slug] = f"Node '{slug}' not found"
        except Exception as exc:
            errors[slug] = str(exc)

    return jsonify({"status": "ok", "analyzed": analyzed, "errors": errors})


@app.route("/api/review/<slug>/approve", methods=["POST"])
@auth.login_required
def api_review_approve(slug):
    if not is_admin():
        return jsonify({"status": "error", "message": "Guests cannot perform this action"}), 403

    git_pull()

    # Find the pending JSON file for this slug
    pending_list = load_pending_suggestions()
    matching = [p for p in pending_list if p["slug"] == slug]

    if not matching:
        if _wants_json():
            return jsonify({"status": "error", "message": f"Inga väntande förslag för {slug}"}), 404
        flash(f"Inga väntande förslag för {slug}", "warning")
        return redirect(url_for("review", slug=slug))

    pending = matching[0]
    suggestions = pending["suggestions"]
    pending_path = pending["path"]

    try:
        meta, sections, _ = read_node(slug)

        new_meta, new_sections = apply_changes(
            meta.copy(), {k: v for k, v in sections.items()}, suggestions
        )

        # Handle current_slice manually (apply_changes does not cover it)
        if "current_slice" in suggestions and suggestions["current_slice"] is not None:
            new_meta["current_slice"] = suggestions["current_slice"]

        new_meta["updated"] = date.today().isoformat()

        write_node(slug, new_meta, new_sections)

        # Push node.md immediately — bypasses Railway ephemeral disk
        node_md_path = node_path(slug)
        ok, msg = push_file_immediately(
            node_md_path,
            f"cns-vault: apply analyze suggestions for {slug}",
        )
        if not ok:
            app.logger.warning("Failed to push node.md for %s: %s", slug, msg)

        # Delete the JSON file
        if pending_path.exists():
            pending_path.unlink()

        # Delete pending JSON from GitHub immediately
        delete_ok, delete_msg = delete_file_on_github(
            pending_path,
            f"cns-vault: remove pending suggestions for {slug}",
        )
        if not delete_ok:
            app.logger.warning("Failed to delete pending JSON on GitHub for %s: %s", slug, delete_msg)

        applied = list(suggestions.keys())
        if _wants_json():
            return jsonify({"status": "ok", "suggestions_count": len(applied)})
        flash(f"Tillämpade {len(applied)} fält för {slug}", "success")

        return redirect(url_for("review", slug=slug))

    except Exception as exc:
        if _wants_json():
            return jsonify({"status": "error", "message": str(exc)}), 500
        flash(f"Fel vid tillämpning: {exc}", "danger")
        return redirect(url_for("review", slug=slug))


@app.route("/api/review/<slug>/reject", methods=["POST"])
@auth.login_required
def api_review_reject(slug):
    if not is_admin():
        return jsonify({"status": "error", "message": "Guests cannot perform this action"}), 403

    # Find and delete the pending JSON file
    pending_list = load_pending_suggestions()
    matching = [p for p in pending_list if p["slug"] == slug]

    if matching:
        pending_path = matching[0]["path"]
        if pending_path.exists():
            pending_path.unlink()

        # Delete pending JSON from GitHub immediately
        delete_ok, delete_msg = delete_file_on_github(
            pending_path,
            f"cns-vault: reject analyze for {slug}",
        )
        if not delete_ok:
            app.logger.warning("Failed to delete pending JSON on GitHub for %s: %s", slug, delete_msg)

        if _wants_json():
            return jsonify({"status": "ok"})
        flash(f"Avvisade förslag för {slug}", "success")
    else:
        if _wants_json():
            return jsonify({"status": "error", "message": f"Inga väntande förslag för {slug}"}), 404
        flash(f"Inga väntande förslag för {slug}", "warning")

    return redirect(url_for("review", slug=slug))


@app.route("/api/nodes")
def api_nodes():
    git_pull()
    path = export_json()
    data = json.loads(path.read_text(encoding="utf-8"))
    return jsonify(data)


@app.route("/api/health")
def api_health():
    return jsonify({
        "status": "ok",
        "repo": os.getenv("GITHUB_REPO", "not configured"),
    })


@app.route("/api/eventstream/events")
def api_eventstream_events():
    """Return recent events from Redis live-buffer, filterable.

    Query params:
      slug:   filter by CNS node slug
      source: filter by source (github, railway, etc.)
      limit:  max events to return (default 100, max 500)

    Falls back to eventstream_latest.json if Redis is unavailable.
    """
    from scripts.eventstream import read_from_redis

    slug = request.args.get("slug")
    source = request.args.get("source")
    limit = min(int(request.args.get("limit", 100)), 500)

    events = read_from_redis(limit=limit, slug=slug, source=source)

    if events is None or len(events) == 0:
        # Fallback: read from eventstream_latest.json
        latest_path = Path(__file__).resolve().parent.parent / "exports" / "eventstream_latest.json"
        if latest_path.exists():
            try:
                all_events = json.loads(latest_path.read_text(encoding="utf-8"))
                if slug:
                    all_events = [e for e in all_events if e.get("slug") == slug]
                if source:
                    all_events = [e for e in all_events if e.get("source") == source]
                events = all_events[:limit]
            except Exception:
                events = []

    return jsonify({
        "events": events,
        "count": len(events),
        "source": "redis" if events else "fallback",
    })


@app.route("/brief")
@auth.login_required
def brief_page():
    return render_template("brief.html", is_admin=is_admin())


@app.route("/api/brief")
@auth.login_required
def api_brief():
    if not is_admin():
        return jsonify({"status": "error", "message": "Admin required"}), 403
    try:
        brief = run_portfolio_brief()
        return jsonify({"status": "ok", "brief": brief, "generated_at": date.today().isoformat()})
    except RuntimeError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/planning/quest", methods=["POST"])
@auth.login_required
def api_planning_quest():
    """Append a quest suggestion to nodes/<slug>/planning/quests.md"""
    if not is_admin():
        return jsonify({"status": "error", "message": "Admin required"}), 403

    data = request.get_json()
    slug = data.get("slug")
    quest = data.get("quest")  # { title, description, estimated_impact, source, created_at }

    if not slug or not quest:
        return jsonify({"status": "error", "message": "slug and quest required"}), 400

    # Read or create quests.md
    quests_path = node_path(slug).parent / "planning" / "quests.md"
    quests_path.parent.mkdir(parents=True, exist_ok=True)

    existing = quests_path.read_text(encoding="utf-8") if quests_path.exists() else f"# {slug} / quests\n\n"

    # Append new quest
    entry = (
        f"\n## {quest['created_at']} — {quest['title']}\n\n"
        f"**Beskrivning:** {quest['description']}\n\n"
        f"**Impact:** {quest['estimated_impact']}\n\n"
        f"**Status:** föreslagen\n\n"
        f"**Källa:** {quest.get('source', 'portfolio-brief')}\n\n"
        f"---\n"
    )
    quests_path.write_text(existing + entry, encoding="utf-8")

    # Push to GitHub immediately
    ok, msg = push_file_immediately(quests_path, f"cns-vault: add quest for {slug}")

    if not ok:
        return jsonify({"status": "error", "message": f"Saved locally but push failed: {msg}"}), 500

    return jsonify({"status": "ok", "path": str(quests_path.relative_to(REPO_ROOT))})


# ---------------------------------------------------------------------------
# Quest lifecycle API
# ---------------------------------------------------------------------------


def _require_bearer_admin():
    """Check Bearer token auth for quest mutation endpoints.

    Returns an error response tuple if unauthorized, or None if OK.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if API_TOKEN and token == API_TOKEN:
            g.role = "admin"
            return None
        else:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
    else:
        return jsonify({"status": "error", "message": "Bearer token required"}), 401


@app.route("/api/issues")
def api_issues_list():
    """List node issues, optionally filtered by ?node=<slug>&state=open|closed."""
    node_slug = request.args.get("node")
    state = request.args.get("state", "open")
    issues = ic_list_issues(node_slug=node_slug, state=state)
    return jsonify({"issues": issues})


@app.route("/api/issues/<int:number>")
def api_issues_get(number):
    """Get a single issue by number."""
    issue = ic_get_issue(number)
    if issue is None:
        return jsonify({"status": "error", "message": "Issue not found"}), 404
    return jsonify({"issue": issue})


@app.route("/api/issues", methods=["POST", "OPTIONS"])
def api_issues_create():
    """Create an issue tied to a node (adds the node:<slug> label)."""
    if request.method == "OPTIONS":
        return add_cors_headers(app.make_default_options_response())
    auth_err = _require_bearer_admin()
    if auth_err:
        return auth_err

    data = request.get_json() or {}
    node_slug = data.get("node_slug") or data.get("slug")
    title = data.get("title")
    body = data.get("body") or data.get("description", "")
    quest_number = data.get("quest_number")

    if not node_slug or not title:
        return jsonify({"status": "error", "message": "node_slug and title required"}), 400

    issue = ic_create_issue(node_slug=node_slug, title=title, body=body, milestone=quest_number)
    return jsonify({"issue": issue}), 201


@app.route("/api/issues/<int:number>/close", methods=["POST", "OPTIONS"])
def api_issues_close(number):
    """Close an issue, leaving an optional result_summary as a closing comment."""
    if request.method == "OPTIONS":
        return add_cors_headers(app.make_default_options_response())
    auth_err = _require_bearer_admin()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True) or {}
    issue = ic_close_issue(number, comment=data.get("result_summary"))
    return jsonify({"issue": issue})


@app.route("/api/issues/from-brief", methods=["POST", "OPTIONS"])
def api_issues_from_brief():
    """Create an issue from the brief's suggestion (deduped by open issue, same title+node)."""
    if request.method == "OPTIONS":
        return add_cors_headers(app.make_default_options_response())
    auth_err = _require_bearer_admin()
    if auth_err:
        return auth_err

    data = request.get_json() or {}
    node_slug = data.get("node_slug") or data.get("slug")
    title = data.get("title")
    body = data.get("body") or data.get("description", "")

    if not node_slug or not title:
        return jsonify({"status": "error", "message": "node_slug and title required"}), 400

    existing = [
        i for i in ic_list_issues(node_slug=node_slug, state="open")
        if i.get("title") == title
    ]
    if existing:
        return jsonify({"status": "ok", "issue": existing[0], "duplicate": True})

    issue = ic_create_issue(node_slug=node_slug, title=title, body=body)
    return jsonify({"issue": issue}), 201


# --- Quests == GitHub Milestones (grouping N issues, progress computed by GitHub) ---

@app.route("/api/quests")
def api_quests_list():
    """List quests (milestones) with progress, ?state=open|closed."""
    state = request.args.get("state", "open")
    return jsonify({"quests": ic_list_milestones(state=state)})


@app.route("/api/quests/<int:number>")
def api_quests_get(number):
    """Get a quest (milestone) with its issues."""
    quest = ic_get_milestone(number)
    if quest is None:
        return jsonify({"status": "error", "message": "Quest not found"}), 404
    quest["issues"] = ic_list_issues(milestone=number, state="all")
    return jsonify({"quest": quest})


@app.route("/api/quests", methods=["POST", "OPTIONS"])
def api_quests_create():
    """Create a quest (milestone)."""
    if request.method == "OPTIONS":
        return add_cors_headers(app.make_default_options_response())
    auth_err = _require_bearer_admin()
    if auth_err:
        return auth_err
    data = request.get_json() or {}
    title = data.get("title")
    if not title:
        return jsonify({"status": "error", "message": "title required"}), 400
    quest = ic_create_milestone(title=title, description=data.get("description", ""))
    return jsonify({"quest": quest}), 201


@app.route("/api/quests/<int:number>/close", methods=["POST", "OPTIONS"])
def api_quests_close(number):
    """Close a quest (milestone). Its issues keep their own open/closed state."""
    if request.method == "OPTIONS":
        return add_cors_headers(app.make_default_options_response())
    auth_err = _require_bearer_admin()
    if auth_err:
        return auth_err
    return jsonify({"quest": ic_close_milestone(number)})


@app.route("/api/activity")
def api_activity():
    devwatch_events: list[dict[str, Any]] = []
    devwatch_meta: dict[str, Any] = {}
    devwatch_date = ""
    devlog_html = ""
    devlog_date = ""

    # Read devwatch from GitHub
    devwatch_raw = read_file_from_github(
        "nodes/project-vault-dashboard/dashboard/data/devwatch_latest.json"
    )
    if devwatch_raw:
        try:
            data = json.loads(devwatch_raw)
            devwatch_events = data.get("events", [])
            devwatch_meta = data.get("meta", {})
            devwatch_date = data.get("exported_at", "")
        except Exception:
            pass

    # Read devlog from GitHub
    devlog_raw = read_file_from_github(
        "nodes/project-vault-dashboard/dashboard/data/devlog_latest.html"
    )
    if devlog_raw:
        devlog_html = _extract_devlog_body_from_string(devlog_raw)
        m = re.search(r"CNS DevLog — (\d{4}-\d{2}-\d{2})", devlog_raw)
        devlog_date = m.group(1) if m else ""

    return jsonify({
        "devwatch_events": devwatch_events,
        "devwatch_meta": devwatch_meta,
        "devwatch_date": devwatch_date,
        "devlog_html": devlog_html,
        "devlog_date": devlog_date,
        "has_activity": bool(devwatch_events or devlog_html),
    })


@app.route("/api/pending")
def api_pending():
    pending_list = load_pending_suggestions()
    # Strip non-serializable Path objects before returning JSON
    result = [
        {
            "slug": p["slug"],
            "analyzed_at": p["analyzed_at"],
            "suggestions": p["suggestions"],
            "reasoning": p.get("reasoning", {}),
            "overall": p.get("overall", ""),
        }
        for p in pending_list
    ]
    return jsonify({"pending": result})


@app.route("/api/node/<slug>/full")
def api_node_full(slug):
    """Return full node data including sections and subdir files."""
    git_pull()
    try:
        meta, sections, raw = read_node(slug)
    except FileNotFoundError:
        return jsonify({"status": "error",
                        "message": f"Node '{slug}' not found"}), 404

    # Read subdir files (planning/, notes/, research/)
    node_files: dict[str, list[dict]] = {}
    pdir = node_dir(slug)
    for subdir in ("planning", "notes", "research"):
        subpath = pdir / subdir
        if not subpath.exists():
            continue
        files = []
        for md_file in sorted(subpath.glob("*.md")):
            if md_file.name.lower() == "readme.md":
                continue
            content = md_file.read_text(encoding="utf-8").strip()
            if not content:
                continue
            files.append({"filename": md_file.name, "content": content})
        if files:
            node_files[subdir] = files

    # Check pending suggestions
    pending_list = load_pending_suggestions()
    pending = next((p for p in pending_list if p["slug"] == slug), None)
    pending_data = None
    if pending:
        pending_data = {
            "analyzed_at": pending["analyzed_at"],
            "suggestions": pending["suggestions"],
            "reasoning": pending.get("reasoning", {}),
            "overall": pending.get("overall", ""),
        }

    # Convert non-JSON-serializable meta values to strings
    meta_clean = {
        k: str(v) if not isinstance(v, (str, int, float, bool, list, type(None))) else v
        for k, v in meta.items()
    }

    return jsonify({
        "status": "ok",
        "slug": slug,
        "meta": meta_clean,
        "sections": sections,
        "node_files": node_files,
        "pending": pending_data,
    })


@app.route("/api/node/<slug>", methods=["PATCH"])
@auth.login_required
def api_node_update(slug):
    """Directly update specific fields in a node.md file."""
    if not is_admin():
        return jsonify({"status": "error", "message": "Admin required"}), 403

    data = request.get_json()
    fields = data.get("fields", {})

    if not fields:
        return jsonify({"status": "error", "message": "fields required"}), 400

    EDITABLE_FIELDS = {
        "status", "stage", "mvp_stage", "current_slice", "summary",
        "cost_sek", "value_sek", "roi_percent", "url_live", "url_repo", "tags"
    }

    invalid = set(fields.keys()) - EDITABLE_FIELDS
    if invalid:
        return jsonify({"status": "error", "message": f"Fields not editable: {invalid}"}), 400

    try:
        meta, sections, _ = read_node(slug)
        new_meta = meta.copy()

        for field, value in fields.items():
            new_meta[field] = value

        new_meta["updated"] = date.today().isoformat()
        write_node(slug, new_meta, sections)

        node_md_path = node_path(slug)
        ok, msg = push_file_immediately(
            node_md_path,
            f"cns-vault: update {', '.join(fields.keys())} for {slug}"
        )
        if not ok:
            app.logger.warning("Failed to push node.md for %s: %s", slug, msg)

        return jsonify({"status": "ok", "updated_fields": list(fields.keys())})

    except FileNotFoundError:
        return jsonify({"status": "error", "message": f"Node '{slug}' not found"}), 404
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/node/<slug>/suggest-quest", methods=["POST"])
@auth.login_required
def api_suggest_quest(slug):
    """Generate a quest suggestion for a specific node using Claude."""
    if not is_admin():
        return jsonify({"status": "error", "message": "Admin required"}), 403

    try:
        meta, sections, raw = read_node(slug)
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "Node not found"}), 404

    try:
        context = _read_node_context(slug)
        devwatch_context = _get_devwatch_context(slug)

        system_prompt = (
            "Du är en teknisk projektplanerare. "
            "Givet nodens kontext, föreslå ETT quest som bör göras härnäst. "
            "Returnera ENDAST giltig JSON: {\"title\": \"...\", \"description\": \"...\", \"estimated_impact\": \"...\"}"
        )

        user_prompt = f"Projektkontext:\n\n{context}"
        if devwatch_context:
            user_prompt += f"\n\nSenaste ändringar (devwatch):\n\n{devwatch_context}"

        ai_raw = _call_claude(system_prompt, user_prompt, max_tokens=1024)
        result = json.loads(ai_raw)

        # Validate required keys
        for key in ("title", "description", "estimated_impact"):
            if not result.get(key) or not isinstance(result[key], str) or not result[key].strip():
                return jsonify({"status": "error", "message": f"Missing or empty field: {key}"}), 500

        if len(result["title"]) > 120:
            result["title"] = result["title"][:120]

        return jsonify({
            "title": result["title"].strip(),
            "description": result["description"].strip(),
            "estimated_impact": result["estimated_impact"].strip(),
        })

    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


# ---------------------------------------------------------------------------
# Devwatch / Devlog / Update endpoints
# ---------------------------------------------------------------------------


def _check_git_available() -> bool:
    """Check if git subprocess is available (required for devwatch)."""
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True,
            timeout=5,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


@app.route("/api/devwatch/run", methods=["POST", "OPTIONS"])
def api_devwatch_run():
    if request.method == "OPTIONS":
        return add_cors_headers(app.make_default_options_response())
    # Manual Bearer token check (same logic as verify_password)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if API_TOKEN and token == API_TOKEN:
            g.role = "admin"
        else:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
    else:
        return jsonify({"status": "error", "message": "Bearer token required"}), 401
    if not is_admin():
        return jsonify({"status": "error", "message": "Admin required"}), 403

    try:
        output_path = Path("exports") / f"devwatch_{date.today().isoformat()}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result_path = run_devwatch(output=str(output_path))

        # Read result to get event count
        data = json.loads(result_path.read_text(encoding="utf-8"))
        event_count = len(data.get("events", []))

        # Push devwatch JSON to GitHub
        ok, msg = push_file_immediately(
            result_path,
            f"cns-vault: devwatch run {date.today().isoformat()}",
        )

        # Also update the latest symlink file
        latest_path = Path(
            "nodes/project-vault-dashboard/dashboard/data/devwatch_latest.json"
        )
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(result_path, latest_path)

        push_file_immediately(
            latest_path,
            f"cns-vault: update devwatch_latest {date.today().isoformat()}",
        )

        return jsonify({
            "status": "ok",
            "events": event_count,
            "output": str(result_path),
            "pushed": ok,
        })

    except DevwatchError as exc:
        return jsonify({"status": "skipped", "reason": str(exc)}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/devlog", methods=["GET", "OPTIONS"])
def api_devlog():
    """Return the latest devlog digest JSON."""
    if request.method == "OPTIONS":
        return add_cors_headers(app.make_default_options_response())

    latest = _latest_export("devlog_*.json")
    if not latest or not latest.exists():
        return jsonify({
            "text": "",
            "generated_at": "",
            "event_count": 0,
            "status": "not_found",
        }), 404

    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
        return jsonify({
            "text": data.get("text", ""),
            "generated_at": data.get("generated_at", ""),
            "event_count": data.get("event_count", 0),
            "status": "ok",
        })
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/devlog/run", methods=["POST", "OPTIONS"])
def api_devlog_run():
    if request.method == "OPTIONS":
        return add_cors_headers(app.make_default_options_response())
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if API_TOKEN and token == API_TOKEN:
            g.role = "admin"
        else:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
    else:
        return jsonify({"status": "error", "message": "Bearer token required"}), 401
    if not is_admin():
        return jsonify({"status": "error", "message": "Admin required"}), 403

    try:
        output_path = Path("exports") / f"devlog_{date.today().isoformat()}.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = run_devlog(output_path=output_path, html=True)

        # Push devlog JSON digest
        json_path = Path("exports") / f"devlog_{date.today().isoformat()}.json"
        if json_path.exists():
            push_file_immediately(
                json_path,
                f"cns-vault: devlog digest {date.today().isoformat()}",
            )
            latest_json = Path(
                "nodes/project-vault-dashboard/dashboard/data/devlog_latest.json"
            )
            latest_json.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(json_path, latest_json)
            push_file_immediately(
                latest_json,
                f"cns-vault: update devlog_latest json {date.today().isoformat()}",
            )

        # Push deprecated HTML (kept for backwards compatibility)
        html_pushed = False
        if result.get("html_path") and Path(result["html_path"]).exists():
            html_path = Path(result["html_path"])
            ok, msg = push_file_immediately(
                html_path,
                f"cns-vault: devlog run {date.today().isoformat()}",
            )
            html_pushed = ok

            latest_path = Path(
                "nodes/project-vault-dashboard/dashboard/data/devlog_latest.html"
            )
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(html_path, latest_path)
            push_file_immediately(
                latest_path,
                f"cns-vault: update devlog_latest {date.today().isoformat()}",
            )

        return jsonify({
            "status": "ok",
            "digest": result,
            "pushed": html_pushed,
        })

    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/update/run", methods=["POST", "OPTIONS"])
def api_update_run():
    if request.method == "OPTIONS":
        return add_cors_headers(app.make_default_options_response())
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if API_TOKEN and token == API_TOKEN:
            g.role = "admin"
        else:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
    else:
        return jsonify({"status": "error", "message": "Bearer token required"}), 401
    if not is_admin():
        return jsonify({"status": "error", "message": "Admin required"}), 403

    results: dict[str, Any] = {}

    # Step 1: devwatch
    try:
        dw_path = Path("exports") / f"devwatch_{date.today().isoformat()}.json"
        dw_path.parent.mkdir(parents=True, exist_ok=True)
        result_path = run_devwatch(output=str(dw_path))
        data = json.loads(result_path.read_text(encoding="utf-8"))
        results["devwatch"] = {
            "status": "ok",
            "events": len(data.get("events", [])),
        }

        push_file_immediately(
            result_path,
            f"cns-vault: devwatch {date.today().isoformat()}",
        )

        latest_dw = Path(
            "nodes/project-vault-dashboard/dashboard/data/devwatch_latest.json"
        )
        latest_dw.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(result_path, latest_dw)
        push_file_immediately(
            latest_dw, "cns-vault: update devwatch_latest"
        )

    except DevwatchError as exc:
        results["devwatch"] = {"status": "skipped", "reason": str(exc)}
    except Exception as exc:
        results["devwatch"] = {"status": "error", "message": str(exc)}

    # Step 2: devlog
    try:
        dl_path = Path("exports") / f"devlog_{date.today().isoformat()}.html"
        result = run_devlog(output_path=dl_path, html=True)
        results["devlog"] = {"status": "ok", "event_count": result.get("event_count", 0)}

        # Push JSON digest
        json_path = Path("exports") / f"devlog_{date.today().isoformat()}.json"
        if json_path.exists():
            push_file_immediately(
                json_path, f"cns-vault: devlog {date.today().isoformat()}"
            )
            latest_dl_json = Path(
                "nodes/project-vault-dashboard/dashboard/data/devlog_latest.json"
            )
            latest_dl_json.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(json_path, latest_dl_json)
            push_file_immediately(
                latest_dl_json, "cns-vault: update devlog_latest json"
            )

        # Push deprecated HTML
        if result.get("html_path") and Path(result["html_path"]).exists():
            html_path = Path(result["html_path"])
            push_file_immediately(
                html_path, f"cns-vault: devlog {date.today().isoformat()}"
            )
            latest_dl = Path(
                "nodes/project-vault-dashboard/dashboard/data/devlog_latest.html"
            )
            latest_dl.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(html_path, latest_dl)
            push_file_immediately(
                latest_dl, "cns-vault: update devlog_latest"
            )

    except Exception as exc:
        results["devlog"] = {"status": "error", "message": str(exc)}

    # Step 3: export nodes.json
    try:
        json_path = export_json()
        push_file_immediately(json_path, "cns-vault: export nodes.json")
        results["nodes_json"] = {"status": "ok"}
    except Exception as exc:
        results["nodes_json"] = {"status": "error", "message": str(exc)}

    non_devwatch = {k: v for k, v in results.items() if k != "devwatch"}
    overall = (
        "ok"
        if all(r.get("status") == "ok" for r in non_devwatch.values())
           and results.get("devwatch", {}).get("status") in ("ok", "skipped")
        else "partial"
    )
    return jsonify({"status": overall, "results": results})


# ---------------------------------------------------------------------------
# GitHub Webhook
# ---------------------------------------------------------------------------

GITHUB_WEBHOOK_SECRET = os.getenv("CNS_WEBHOOK_SECRET", "")


def _slugs_from_pushed_files(payload: dict) -> set[str]:
    """Return node slugs touched by a push event's commits."""
    changed_files: set[str] = set()
    for commit in payload.get("commits", []):
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))
        changed_files.update(commit.get("removed", []))

    slugs: set[str] = set()
    for f in changed_files:
        parts = Path(f).parts
        if len(parts) >= 2 and parts[0] == "nodes":
            slugs.add(parts[1])
    return slugs


def _slugs_from_text(*texts: str) -> set[str]:
    """Match known node slugs mentioned in free text (PR title/body/branch).

    Used for events that don't carry a file list (pull_request, workflow_run).
    A slug matches if it appears as a whole token in any of the given texts.
    """
    haystack = " ".join(t for t in texts if t).lower()
    if not haystack:
        return set()
    known = {meta.get("slug") for meta, _ in read_all_nodes() if meta.get("slug")}
    return {slug for slug in known if slug and slug.lower() in haystack}


_RETIRED = None  # quest auto-complete helpers removed — GitHub closes issues via "Closes #N"


@app.route("/api/webhook/github", methods=["POST", "OPTIONS"])
def api_webhook_github():
    """Receive GitHub webhooks — log activity to the eventstream.

    Handled events: push, pull_request, workflow_run, issues, issue_comment.
    Quest auto-completion was removed: work items are GitHub Issues now, and
    GitHub closes them natively from merged PRs ("Closes #N").
    """
    if request.method == "OPTIONS":
        return add_cors_headers(app.make_default_options_response())

    # Validate signature
    if GITHUB_WEBHOOK_SECRET:
        signature = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(
            GITHUB_WEBHOOK_SECRET.encode(),
            request.data,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return jsonify({"status": "error", "message": "Invalid signature"}), 401

    payload = request.get_json(silent=True) or {}
    event = request.headers.get("X-GitHub-Event", "")

    affected_slugs: set[str] = set()
    eventstream_count = 0  # events logged to Redis

    try:
        from scripts.eventstream import (
            normalize_push_event,
            normalize_pr_event,
            normalize_workflow_run_event,
            normalize_issue_event,
            normalize_milestone_event,
            push_to_redis,
        )

        if event == "push":
            affected_slugs = _slugs_from_pushed_files(payload)
            events = normalize_push_event(payload)
        elif event == "pull_request":
            events = normalize_pr_event(payload)
        elif event == "workflow_run":
            if payload.get("action") != "completed":
                return jsonify({
                    "status": "ok",
                    "message": f"Ignored workflow_run action: {payload.get('action')}",
                })
            events = normalize_workflow_run_event(payload)
        elif event in ("issues", "issue_comment"):
            events = normalize_issue_event(payload)
        elif event == "milestone":
            events = normalize_milestone_event(payload)
        else:
            return jsonify({"status": "ok", "message": f"Ignored event: {event}"})

        for evt in events:
            if not evt.get("slug") and affected_slugs:
                evt["slug"] = sorted(affected_slugs)[0]
            push_to_redis(evt)
            eventstream_count += 1
    except Exception as exc:
        app.logger.warning("Eventstream logging failed: %s", exc)

    return jsonify({
        "status": "ok",
        "event": event,
        "affected_slugs": list(affected_slugs),
        "eventstream_logged": eventstream_count,
    })


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

_configured = False


@app.before_request
def _setup() -> None:
    global _configured
    if not _configured:
        configure_git()
        _configured = True


if not PASSWORD:
    app.logger.warning(
        "CNS_ADMIN_PASSWORD not set – running in dev mode (no auth). "
        "Set CNS_PASSWORD for production."
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
