"""CNS Vault – Flask web application for CNS portfolio management."""

from __future__ import annotations

import json
import os
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
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_httpauth import HTTPBasicAuth  # noqa: E402

from app.git_ops import configure_git, git_commit_and_push, git_pull  # noqa: E402
from scripts.analyst import load_pending_suggestions, run_analyze  # noqa: E402
from scripts.json_exporter import export_json  # noqa: E402
from scripts.md_parser import (  # noqa: E402
    SECTIONS,
    apply_changes,
    project_dir,
    read_all_projects,
    read_project,
    write_project,
)
from scripts.validator import (  # noqa: E402
    VALID_FAMILIES,
    VALID_MVP_STAGES,
    VALID_STATUSES,
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
PASSWORD = os.getenv("CNS_PASSWORD", "")


@auth.verify_password
def verify_password(username: str, password: str) -> bool:
    if not PASSWORD:
        # Dev mode – no password set, allow all
        return True
    return username == USERNAME and password == PASSWORD


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
# Helper: read project subdirectory files
# ---------------------------------------------------------------------------


def _read_project_files(slug: str) -> dict[str, list[tuple[str, str]]]:
    """Read markdown files from planning/, notes/, research/ subdirs.

    Returns: {subdir_name: [(filename, content), ...]}
    Skips README.md and empty files.
    """
    pdir = project_dir(slug)
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
# Routes – UI
# ---------------------------------------------------------------------------


@app.route("/")
@auth.login_required
def index():
    git_pull()

    all_projects = read_all_projects()
    projects_data = []
    for meta, sections in all_projects:
        projects_data.append(meta)

    # Aggregate stats
    total = len(projects_data)
    active = sum(
        1 for p in projects_data if p.get("status") in ("active", "early_mvp", "mvp", "live")
    )
    total_cost = sum(p.get("cost_sek", 0) or 0 for p in projects_data)
    total_value = sum(p.get("value_sek", 0) or 0 for p in projects_data)
    with_roi = [p for p in projects_data if (p.get("roi_percent") or 0) > 0]
    avg_roi = (
        round(sum(p.get("roi_percent", 0) or 0 for p in with_roi) / len(with_roi))
        if with_roi
        else 0
    )

    # Collect unique values for filters
    statuses = sorted(set(p.get("status", "") for p in projects_data if p.get("status")))
    all_tags: list[str] = []
    for p in projects_data:
        all_tags.extend(p.get("tags", []) or [])
    tags = sorted(set(all_tags))
    families = sorted(set(p.get("family", "") for p in projects_data if p.get("family")))

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
    filtered = projects_data[:]
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
        projects=filtered,
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
    )


@app.route("/project/<slug>")
@auth.login_required
def project_detail(slug):
    git_pull()

    try:
        meta, sections, raw = read_project(slug)
    except FileNotFoundError:
        return render_template(
            "project.html",
            error="not_found",
            slug=slug,
            meta=None,
            sections={},
            section_order=[],
            project_files={},
            has_pending=False,
        ), 404

    project_files = _read_project_files(slug)

    # Check if there are pending suggestions for this project
    has_pending = any(
        p["slug"] == slug for p in load_pending_suggestions()
    )

    return render_template(
        "project.html",
        meta=meta,
        sections=sections,
        section_order=SECTIONS,
        project_files=project_files,
        has_pending=has_pending,
        slug=slug,
        error=None,
    )


@app.route("/review")
@auth.login_required
def review():
    git_pull()

    slug_filter = request.args.get("slug", "")
    pending = load_pending_suggestions()

    if slug_filter:
        pending = [p for p in pending if p["slug"] == slug_filter]

    # Enrich with current project data for diff display
    enriched = []
    for item in pending:
        try:
            meta, sections, _ = read_project(item["slug"])
        except FileNotFoundError:
            meta = {}
            sections = {}
        enriched.append({**item, "current_meta": meta, "current_sections": sections})

    return render_template(
        "review.html",
        pending=enriched,
        slug_filter=slug_filter,
    )


# ---------------------------------------------------------------------------
# Routes – API
# ---------------------------------------------------------------------------


@app.route("/api/analyze/<slug>", methods=["POST"])
@auth.login_required
def api_analyze(slug):
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

            # Commit the analyze JSON to git so it survives redeploy
            ok, msg = git_commit_and_push(f"cns-vault: analyze {slug}")
            if not ok:
                app.logger.warning("Failed to commit analyze JSON: %s", msg)

            return jsonify({"status": "ok", "suggestions_count": count})
        else:
            return jsonify({"status": "ok", "suggestions_count": 0})

    except FileNotFoundError:
        return jsonify({"status": "error", "message": f"Project '{slug}' not found"}), 404
    except RuntimeError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/review/<slug>/approve", methods=["POST"])
@auth.login_required
def api_review_approve(slug):
    git_pull()

    # Find the pending JSON file for this slug
    pending_list = load_pending_suggestions()
    matching = [p for p in pending_list if p["slug"] == slug]

    if not matching:
        flash(f"Inga väntande förslag för {slug}", "warning")
        return redirect(url_for("review", slug=slug))

    pending = matching[0]
    suggestions = pending["suggestions"]
    pending_path = pending["path"]

    try:
        meta, sections, _ = read_project(slug)

        new_meta, new_sections = apply_changes(
            meta.copy(), {k: v for k, v in sections.items()}, suggestions
        )

        # Handle current_slice manually (apply_changes does not cover it)
        if "current_slice" in suggestions and suggestions["current_slice"] is not None:
            new_meta["current_slice"] = suggestions["current_slice"]

        new_meta["updated"] = date.today().isoformat()

        write_project(slug, new_meta, new_sections)

        # Delete the JSON file
        if pending_path.exists():
            pending_path.unlink()

        # Commit and push
        ok, msg = git_commit_and_push(
            f"cns-vault: apply analyze suggestions for {slug}"
        )
        if not ok:
            flash(f"Ändringar sparade lokalt men kunde inte pushas: {msg}", "danger")
        else:
            applied = list(suggestions.keys())
            flash(f"Tillämpade {len(applied)} fält för {slug}", "success")

        return redirect(url_for("review", slug=slug))

    except Exception as exc:
        flash(f"Fel vid tillämpning: {exc}", "danger")
        return redirect(url_for("review", slug=slug))


@app.route("/api/review/<slug>/reject", methods=["POST"])
@auth.login_required
def api_review_reject(slug):
    # Find and delete the pending JSON file
    pending_list = load_pending_suggestions()
    matching = [p for p in pending_list if p["slug"] == slug]

    if matching:
        pending_path = matching[0]["path"]
        if pending_path.exists():
            pending_path.unlink()

        # Commit the deletion to git
        ok, msg = git_commit_and_push(f"cns-vault: reject analyze for {slug}")
        if not ok:
            flash(f"Förslag raderat lokalt men kunde inte pushas: {msg}", "danger")
        else:
            flash(f"Avvisade förslag för {slug}", "success")
    else:
        flash(f"Inga väntande förslag för {slug}", "warning")

    return redirect(url_for("review", slug=slug))


@app.route("/api/projects")
@auth.login_required
def api_projects():
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


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

configure_git()

if not PASSWORD:
    app.logger.warning(
        "CNS_PASSWORD not set – running in dev mode (no auth). "
        "Set CNS_PASSWORD for production."
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
