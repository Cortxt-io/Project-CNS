"""Git operations for CNS Vault – GitHub REST API based.

Railway deploys without a .git/ directory, so all git subprocess calls crash.
This module uses the GitHub Contents API instead, requiring only
CNS_GITHUB_TOKEN and GITHUB_REPO environment variables.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
GITHUB_API = "https://api.github.com"
BRANCH = "main"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _get_config() -> tuple[str, str]:
    """Read CNS_GITHUB_TOKEN and GITHUB_REPO from environment."""
    token = os.getenv("CNS_GITHUB_TOKEN", "")
    repo = os.getenv("GITHUB_REPO", "")
    return token, repo


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


# ---------------------------------------------------------------------------
# Public API (kept to maintain existing call signatures)
# ---------------------------------------------------------------------------


def configure_git() -> None:
    """Verify that GitHub credentials are available."""
    token, repo = _get_config()
    if token and repo:
        logger.info("GitHub API configured for %s", repo)
    else:
        logger.warning(
            "CNS_GITHUB_TOKEN or GITHUB_REPO not set – GitHub API will not work. "
            "Running in local-only mode."
        )


def git_pull() -> tuple[bool, str]:
    """No-op on Railway – Railway always deploys latest code from GitHub."""
    return True, "ok"


def git_commit_and_push(message: str) -> tuple[bool, str]:
    """Sync recently changed files under projects/ and exports/ to GitHub.

    Only files modified in the last 60 seconds are pushed, to avoid
    sending hundreds of API requests on every call.
    """
    token, repo = _get_config()
    if not token or not repo:
        return False, "CNS_GITHUB_TOKEN or GITHUB_REPO not configured"

    headers = _headers(token)
    pushed: list[str] = []
    errors: list[str] = []

    cutoff = time.time() - 60  # files changed in the last 60 seconds

    dirs_to_sync = [
        REPO_ROOT / "projects",
        REPO_ROOT / "exports",
    ]

    for sync_dir in dirs_to_sync:
        if not sync_dir.exists():
            continue
        for file_path in sync_dir.rglob("*.md"):
            if file_path.stat().st_mtime > cutoff:
                _push_file(file_path, repo, headers, message, pushed, errors)
        for file_path in sync_dir.rglob("*.json"):
            if file_path.stat().st_mtime > cutoff:
                _push_file(file_path, repo, headers, message, pushed, errors)
        for file_path in sync_dir.rglob("*.html"):
            if file_path.stat().st_mtime > cutoff:
                _push_file(file_path, repo, headers, message, pushed, errors)

    if errors:
        return False, f"Errors: {'; '.join(errors[:3])}"
    if not pushed:
        return True, "Nothing to push"
    return True, f"Pushed {len(pushed)} files"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _push_file(
    file_path: Path,
    repo: str,
    headers: dict[str, str],
    message: str,
    pushed: list[str],
    errors: list[str],
) -> None:
    try:
        rel_path = file_path.relative_to(REPO_ROOT).as_posix()
        content = file_path.read_bytes()
        encoded = base64.b64encode(content).decode("utf-8")

        # Get current SHA (required for updates)
        get_url = f"{GITHUB_API}/repos/{repo}/contents/{rel_path}"
        get_resp = requests.get(get_url, headers=headers, timeout=10)

        sha: str | None = None
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")
        elif get_resp.status_code == 404:
            sha = None  # New file
        else:
            errors.append(f"{rel_path}: GET failed {get_resp.status_code}")
            return

        # Push file
        put_payload: dict[str, str | None] = {
            "message": message,
            "content": encoded,
            "branch": BRANCH,
        }
        if sha:
            put_payload["sha"] = sha

        put_resp = requests.put(
            get_url,
            headers=headers,
            json=put_payload,
            timeout=30,
        )

        if put_resp.status_code in (200, 201):
            pushed.append(rel_path)
        else:
            errors.append(
                f"{rel_path}: PUT failed {put_resp.status_code} "
                f"{put_resp.text[:100]}"
            )
    except Exception as exc:
        errors.append(f"{file_path.name}: {exc}")
