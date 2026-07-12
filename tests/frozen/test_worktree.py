"""Smoke-test för git-worktree-lagret (scripts/worktree.py, #59 skriv-läge).

Mot ett RIKTIGT temporärt git-repo (ingen remote → push testas ej): prepare skapar
worktree+branch, commit_all stagar+committar bara när något ändrats, cleanup tar bort
worktree:t men behåller branchen (committat arbete överlever). Körs fristående/pytest.
Hoppas tyst om git saknas.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import worktree  # noqa: E402


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


def _make_repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    _git("init", "-b", "main", cwd=repo)
    _git("config", "user.email", "t@t.se", cwd=repo)
    _git("config", "user.name", "t", cwd=repo)
    (repo / "f.txt").write_text("hej\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-m", "init", cwd=repo)
    return repo


def run() -> None:
    if not shutil.which("git"):
        print("SKIP: git saknas")
        return
    tmp = Path(tempfile.mkdtemp(prefix="wt-test-"))
    orig_root, orig_wtdir = worktree.REPO_ROOT, worktree.WT_DIR
    try:
        repo = _make_repo(tmp)
        worktree.REPO_ROOT = repo
        worktree.WT_DIR = tmp / "wts"

        wt = worktree.prepare(42)
        assert Path(wt["path"]).exists(), "worktree skapades inte"
        assert wt["branch"] == "dispatch/issue-42"

        # Rent worktree → commit_all returnerar False.
        assert worktree.commit_all(wt["path"], "tomt") is False

        # Ändra en fil → commit_all returnerar True.
        (Path(wt["path"]) / "ny.txt").write_text("data\n", encoding="utf-8")
        assert worktree.commit_all(wt["path"], "lägg till ny.txt") is True

        # Cleanup tar bort worktree men behåller branchen (committat arbete kvar).
        worktree.cleanup(wt["path"])
        assert not Path(wt["path"]).exists(), "worktree städades inte"
        branches = subprocess.run(
            ["git", "branch", "--list", "dispatch/issue-42"],
            cwd=str(repo), capture_output=True, text=True,
        ).stdout
        assert "dispatch/issue-42" in branches, "branchen ska överleva cleanup"
        print("PASS test_worktree_lifecycle")
    finally:
        worktree.REPO_ROOT, worktree.WT_DIR = orig_root, orig_wtdir
        shutil.rmtree(tmp, ignore_errors=True)


def test_worktree_lifecycle():
    run()


if __name__ == "__main__":
    run()
