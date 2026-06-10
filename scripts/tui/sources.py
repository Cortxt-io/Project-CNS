"""Extra lässkällor för TUI:t — idéer, git-brancher och issues per nod.

Alla funktioner är **graceful-degrade**: de returnerar tom data eller en
statusmarkör i stället för att kasta, så UI:t aldrig kraschar när en källa
saknas (t.ex. issues-klienten finns bara på migreringsbranchen, och git/
token kan saknas). Håller isolationen — ingen import av heta filer på
toppnivå; issues_client importeras lazy.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# Repo-roten: scripts/tui/sources.py → parents[2].
REPO_ROOT = Path(__file__).resolve().parents[2]
# Workspace-roten (mappen ovanför repot, t.ex. "CNS projekt").
WORKSPACE_ROOT = REPO_ROOT.parent
# Claude Code-transkript: ~/.claude/projects/<kodad-workspace>/<sessionId>.jsonl
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


# -- miljö (.env) ------------------------------------------------------------

def load_env() -> None:
    """Läs .env till miljön (setdefault) så issues_client får GITHUB_REPO/token.

    Provar repo-roten först, sedan huvudarbetskopian Project-CNS (worktrees som
    cns-tui saknar egen .env — den är gitignored och delas inte av git).
    Degraderar tyst; samma radformat som scripts/recommend.py:_load_env.
    """
    import os

    for env_file in (REPO_ROOT / ".env", WORKSPACE_ROOT / "Project-CNS" / ".env"):
        try:
            if not env_file.exists():
                continue
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
            return
        except Exception:
            continue


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


def merged_branches() -> set[str]:
    """Lokala brancher som redan är merge:ade in i main (= klara spår).

    Pollbar 'done'-signal för loop-väntan: ett feature-spår räknas klart när
    det landat i main. Degraderar till tom mängd om git saknas/fel.
    """
    try:
        out = subprocess.run(
            ["git", "branch", "--merged", "main", "--format=%(refname:short)"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return set()
    if out.returncode != 0:
        return set()
    return {ln.strip() for ln in out.stdout.splitlines() if ln.strip()}


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


# -- Claude Code-sessioner (transkript, read-only, cross-boundary) ----------

@dataclass
class Transcript:
    session_id: str
    title: str
    git_branch: str
    timestamp: str
    path: str
    slugs: set[str] = field(default_factory=set)


def _encoded_workspace_dirname() -> str:
    """Claude Codes kataloghash för workspace-roten (ersätter :\\/ och blanksteg)."""
    s = str(WORKSPACE_ROOT)
    for ch in (":", "\\", "/", " "):
        s = s.replace(ch, "-")
    return s


def _scan_transcript(
    path: Path, slug_pattern: re.Pattern | None, max_lines: int = 4000
) -> Transcript | None:
    """Läs ett transkript (radbegränsat) → metadata, titel, nämnda nod-slugs."""
    session_id = path.stem
    title = ""
    git_branch = ""
    timestamp = ""
    found_slugs: set[str] = set()
    try:
        with path.open(encoding="utf-8") as fh:
            for n, line in enumerate(fh):
                if n >= max_lines:
                    break
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not git_branch and obj.get("gitBranch"):
                    git_branch = str(obj["gitBranch"])
                if not timestamp and obj.get("timestamp"):
                    timestamp = str(obj["timestamp"])
                if obj.get("sessionId"):
                    session_id = str(obj["sessionId"])
                if not title and obj.get("type") == "user":
                    title = _first_user_text(obj)
                # Slug-detektion med ordgräns (undviker träff inne i andra ord).
                if slug_pattern is not None:
                    found_slugs.update(m.lower() for m in slug_pattern.findall(line))
    except Exception:
        return None
    return Transcript(
        session_id=session_id,
        title=title or "(ingen titel)",
        git_branch=git_branch,
        timestamp=timestamp,
        path=str(path),
        slugs=found_slugs,
    )


def _first_user_text(obj: dict) -> str:
    msg = obj.get("message", {}) or {}
    content = msg.get("content")
    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text", "")
                break
    return " ".join(text.split())[:90]


def list_transcripts(known_slugs: set[str] | None = None, limit: int = 40) -> list[Transcript]:
    """Lista Claude Code-sessioner för detta workspace, nyast först.

    Läser ~/.claude/projects/<workspace>/<id>.jsonl. Read-only och
    cross-boundary (harness-katalog, inte GitHub-sanning). Degraderar till [].
    `known_slugs` används för att märka vilka noder varje session rört.
    """
    known = known_slugs or set()
    proj_dir = CLAUDE_PROJECTS_DIR / _encoded_workspace_dirname()
    if not proj_dir.exists():
        return []
    slug_pattern: re.Pattern | None = None
    if known:
        alts = "|".join(re.escape(s) for s in sorted(known, key=len, reverse=True))
        slug_pattern = re.compile(rf"(?<![\w-])({alts})(?![\w-])", re.IGNORECASE)
    transcripts: list[Transcript] = []
    for path in proj_dir.glob("*.jsonl"):
        t = _scan_transcript(path, slug_pattern)
        if t is not None:
            transcripts.append(t)
    transcripts.sort(key=lambda t: t.timestamp, reverse=True)
    return transcripts[:limit]


# -- kunskaps-ytor: skills + memory-cards ----------------------------------

def _light_meta(path: Path) -> dict[str, str]:
    """Minimal frontmatter-parser (topp-nivå key: value) — fallback när YAML är trasig."""
    meta: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return meta
    if not text.startswith("---"):
        return meta
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip("\"'")
    return meta


def load_skills() -> list[dict]:
    """Lista skills (skills/*/SKILL.md), frontmatter-parsade. Degraderar till []."""
    skills_dir = REPO_ROOT / "skills"
    if not skills_dir.exists():
        return []
    out: list[dict] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        name = skill_md.parent.name
        description = ""
        try:
            import frontmatter

            meta = frontmatter.load(str(skill_md)).metadata or {}
            name = str(meta.get("name", name))
            description = str(meta.get("description", ""))
        except Exception:
            meta = {}
        if not description:
            # Trasig/okänd YAML → lättviktig fallback.
            light = _light_meta(skill_md)
            name = light.get("name", name)
            description = light.get("description", description)
        out.append({"name": name, "description": description, "path": str(skill_md)})
    return out


def load_memory_cards() -> list[dict]:
    """Lista memory-cards (~/.claude/.../memory/*.md). Cross-boundary, read-only.

    Degraderar till [] om katalogen saknas. MEMORY.md-indexet hoppas över.
    """
    mem_dir = CLAUDE_PROJECTS_DIR / _encoded_workspace_dirname() / "memory"
    if not mem_dir.exists():
        return []
    out: list[dict] = []
    for md in sorted(mem_dir.glob("*.md")):
        if md.name == "MEMORY.md":
            continue
        name = md.stem
        description = ""
        mtype = ""
        try:
            import frontmatter

            meta = frontmatter.load(str(md)).metadata or {}
            name = str(meta.get("name", name))
            description = str(meta.get("description", ""))
            inner = meta.get("metadata")
            if isinstance(inner, dict) and inner.get("type"):
                mtype = str(inner.get("type"))
            elif meta.get("type"):
                mtype = str(meta.get("type"))
        except Exception:
            pass
        out.append(
            {"name": name, "description": description, "type": mtype, "path": str(md)}
        )
    return out
