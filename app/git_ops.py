"""Git operations for CNS Vault – pull, commit, push, configure."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent


def configure_git() -> None:
    """Set git user config and remote URL with token. Call at app startup."""
    _run("git", "config", "user.email", "cns-vault@railway.app")
    _run("git", "config", "user.name", "CNS Vault")

    token = os.getenv("GITHUB_TOKEN", "")
    repo = os.getenv("GITHUB_REPO", "")

    if token and repo:
        remote_url = f"https://{token}@github.com/{repo}.git"
        _run("git", "remote", "set-url", "origin", remote_url)
        logger.info("Git remote configured for %s", repo)
    else:
        logger.warning(
            "GITHUB_TOKEN or GITHUB_REPO not set – git push will not work. "
            "Running in local-only mode."
        )


def git_pull() -> tuple[bool, str]:
    """Pull latest from origin/main. Returns (success, output)."""
    try:
        result = _run("git", "pull", "origin", "main")
        return True, result.stdout
    except RuntimeError as exc:
        logger.warning("git pull failed: %s", exc)
        return False, str(exc)


def git_commit_and_push(message: str) -> tuple[bool, str]:
    """Stage projects/ and exports/, commit, and push. Returns (success, output)."""
    try:
        # Stage
        _run("git", "add", "projects/", "exports/")

        # Check if there is anything to commit
        check = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if check.returncode == 0:
            return True, "Nothing to commit"

        # Commit
        _run("git", "commit", "-m", message)

        # Push
        _run("git", "push", "origin", "main")
        return True, f"Committed and pushed: {message}"

    except RuntimeError as exc:
        logger.error("git commit/push failed: %s", exc)
        return False, str(exc)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a git subprocess, raise on failure."""
    result = subprocess.run(
        list(args),
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command '{' '.join(args)}' failed (exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result
