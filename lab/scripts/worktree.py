"""Git-worktree-isolering för skrivande dispatch-pass (#59, Fas 3).

När crawlen släpper på skrivtröskeln (agenten får mutera filer) ska passet INTE
röra ``main`` direkt: det jobbar i en isolerad git-worktree på en egen branch, så
ett misslyckat/halvfärdigt pass aldrig smutsar ner arbetskopian. Worktree + branch
skapas före passet, committas + pushas om något ändrades, och städas alltid bort
efteråt (orphan-cleanup, samma princip som lease-TTL:n).

Tunna subprocess-wrappers runt ``git worktree`` — degraderar tydligt (kastar
``WorktreeError``) om repo:t saknar git/remote. Injiceras i ``dispatch.crawl_once``
som ``worktree_fn``/``finalize_fn`` så själva crawl-logiken förblir testbar utan git.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# Worktrees bor som syskon till repo-roten (ej nästlat i trädet → ingen self-tracking).
WT_DIR = REPO_ROOT.parent / ".cns-dispatch-worktrees"
BRANCH_PREFIX = "dispatch"


class WorktreeError(RuntimeError):
    """Git saknas, är inte ett repo, eller ett worktree-kommando misslyckades."""


def _git(*args: str, cwd: Path | None = None) -> str:
    """Kör ett git-kommando och returnera stdout (strip). Kastar WorktreeError vid fel."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd or REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise WorktreeError(f"git ej körbart: {exc}") from exc
    if proc.returncode != 0:
        raise WorktreeError(f"git {' '.join(args)} → {proc.returncode}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def branch_name(number: int) -> str:
    """Branchnamn för en dispatchad issue: ``dispatch/issue-<n>``."""
    return f"{BRANCH_PREFIX}/issue-{int(number)}"


def prepare(number: int, *, base: str = "main") -> dict:
    """Skapa en isolerad worktree på en ny branch ``dispatch/issue-<n>`` från *base*.

    Returnerar ``{"path", "branch"}``. Kastar WorktreeError om branchen/worktree:t redan
    finns (en pågående claim ska aldrig dubbeldispatchas) eller om git saknas.
    """
    branch = branch_name(number)
    path = WT_DIR / f"issue-{int(number)}"
    WT_DIR.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise WorktreeError(f"worktree finns redan: {path}")
    # -b skapar branchen; faller branchen redan finns kastar git → vi vill veta.
    _git("worktree", "add", "-b", branch, str(path), base)
    return {"path": str(path), "branch": branch}


def commit_all(path: str, message: str) -> bool:
    """Stagea + committa allt i worktree:t. True om något committades, False om rent."""
    wt = Path(path)
    _git("add", "-A", cwd=wt)
    status = _git("status", "--porcelain", cwd=wt)
    if not status.strip():
        return False
    _git("commit", "-m", message, cwd=wt)
    return True


def push(path: str, branch: str) -> None:
    """Pusha branchen till origin (skapar remote-branch för PR:n)."""
    _git("push", "-u", "origin", branch, cwd=Path(path))


def changed_paths(path: str, *, base: str = "main") -> list[str]:
    """Filer som skrivpassets branch ändrat mot *base* (för risk-klassning, Fas 5).

    ``git diff --name-only <base>...HEAD`` i worktree:t → lista relativa sökvägar. Tom
    lista om inget ändrats. Degraderar till [] vid git-fel (klassas då som "inga ändringar").
    """
    try:
        out = _git("diff", "--name-only", f"{base}...HEAD", cwd=Path(path))
    except WorktreeError:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def cleanup(path: str, *, branch: str | None = None, delete_branch: bool = False) -> None:
    """Ta bort worktree:t (force) och valfritt den lokala branchen. Degraderar tyst."""
    try:
        _git("worktree", "remove", "--force", path)
    except WorktreeError:
        pass
    if delete_branch and branch:
        try:
            _git("branch", "-D", branch)
        except WorktreeError:
            pass
