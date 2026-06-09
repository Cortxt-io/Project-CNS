"""Extra lässkällor för TUI:t — idéer, git-brancher och issues per nod.

Alla funktioner är **graceful-degrade**: de returnerar tom data eller en
statusmarkör i stället för att kasta, så UI:t aldrig kraschar när en källa
saknas (t.ex. issues-klienten finns bara på migreringsbranchen, och git/
token kan saknas). Håller isolationen — ingen import av heta filer på
toppnivå; issues_client importeras lazy.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

# Repo-roten: scripts/tui/sources.py → parents[2].
REPO_ROOT = Path(__file__).resolve().parents[2]


# -- idéer -----------------------------------------------------------------

def load_ideas(slug: str | None = None) -> list[dict]:
    """Öppna idéer (valfritt filtrerade på nod-slug), nyast först.

    Degraderar till [] om idé-inkorgen inte kan läsas.
    """
    try:
        from scripts.idea_inbox import list_ideas as _list_ideas

        return _list_ideas(status="open", slug=slug)
    except Exception:
        return []


# -- git-brancher ----------------------------------------------------------

@dataclass
class Branch:
    name: str
    current: bool
    remote: bool


def git_branches() -> list[Branch]:
    """Lista lokala + remote-brancher. Degraderar till [] om git saknas/fel.

    Aktiv branch markeras current=True. Kollisionssynlighet: ser man flera
    aktiva spår (t.ex. quest-to-issues, rename-project-to-node) syns de här.
    """
    try:
        out = subprocess.run(
            ["git", "branch", "-a", "--format=%(HEAD)%09%(refname)%09%(refname:short)"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return []
    if out.returncode != 0:
        return []

    branches: list[Branch] = []
    for line in out.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        head, refname, short = parts
        # Hoppa över remote HEAD-symrefen (refs/remotes/origin/HEAD).
        if refname.endswith("/HEAD"):
            continue
        remote = refname.startswith("refs/remotes/")
        branches.append(Branch(name=short, current=head.strip() == "*", remote=remote))
    return branches


# -- issues per nod (grindad) ----------------------------------------------

def open_issues_for_slug(slug: str) -> tuple[str | None, list[dict]]:
    """Öppna GitHub-issues för en nod via issues_client.

    Returnerar (status, issues). status är None vid lyckad hämtning, annars en
    människoläsbar markör (klienten saknas på denna branch, eller token/repo
    ej konfigurerat). Lazy import så TUI:t fungerar på en branch utan
    migreringskoden.
    """
    try:
        from scripts.issues_client import list_issues
    except Exception:
        return ("issues-klient saknas på denna branch (migrering ej landad)", [])
    try:
        issues = list_issues(node_slug=slug, state="open")
        return (None, issues or [])
    except Exception as exc:
        return (f"issues ej konfigurerade ({type(exc).__name__})", [])
