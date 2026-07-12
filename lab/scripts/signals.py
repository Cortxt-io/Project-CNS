"""Signaler ur verkligheten — det ``phase_derive`` mäter fasen med.

**Principen:** en signal antingen MÄTS eller saknas. Den gissas aldrig. En signal som inte kan
avgöras utelämnas ur dicten — då blir dess steg ``None`` ("vi vet inte") i stället för ``False``
("det är inte gjort"). Skillnaden avgör om man litar på härledaren.

**Källorna, i fallande ordning av tillförlitlighet:**
  1. Repot på disk — vertikalerna ligger som syskonmappar (``../<slug>``). Ingen API-nyckel,
     inget nät, och det är den mest direkta sanningen som finns: koden själv.
  2. ``catalog.yaml`` — ``url_repo``, ``url_live``, ``integrations.deploy``.
  3. Vault-annoteringen — ``kill_criteria``, ``north_star`` (omdöme Rikard skrivit).
  4. Drift-API:er (Vercel/Railway) — senare; ``deploy_healthy`` saknas tills dess, och då är
     dess steg ärligt ``None`` i stället för falskt grönt.

Ren och injicerbar: ``collect`` tar en rot-sökväg så testerna kan peka på en tmp-mapp.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE = REPO_ROOT.parent          # Cortxt-io/ — vertikalerna ligger som syskon

# Filnamn som förråder att det finns tester, oavsett stack.
TEST_MARKERS = ("tests", "test", "__tests__", "spec")
TEST_GLOBS = ("**/*.test.*", "**/*.spec.*", "**/test_*.py")

# Designsystemet, per stack. Att UI:t sitter på en delad primär (i stället för hårdkodade
# färger per app) är precis vad konsolideringsfasen kräver.
DESIGN_SYSTEM_MARKERS = ("@cortxt/ui", "shadcn", "components/ui", "bits-ui")

# En typad API-söm = UI anropar aldrig fetch direkt, utan går genom en klientfil.
API_SEAM_MARKERS = ("lib/cns.js", "lib/api.ts", "lib/api.js", "src/lib/api", "lib/client.ts")


def repo_path(slug: str, workspace: Path | None = None) -> Path | None:
    """Vertikalens repo på disk, om det finns som syskonmapp."""
    root = (workspace or WORKSPACE) / slug
    return root if (root / ".git").is_dir() else None


def _has_tests(repo: Path) -> bool:
    if any((repo / m).is_dir() for m in TEST_MARKERS):
        return True
    return any(next(repo.glob(g), None) is not None for g in TEST_GLOBS)


def _text_of(repo: Path, *names: str) -> str:
    """Slå ihop innehållet i några nyckelfiler — billigt sätt att leta markörer."""
    out = []
    for name in names:
        path = repo / name
        if path.is_file():
            try:
                out.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                pass
    return "\n".join(out)


def _uses_design_system(repo: Path) -> bool:
    manifest = _text_of(repo, "package.json", "components.json")
    if any(m in manifest for m in DESIGN_SYSTEM_MARKERS):
        return True
    return any((repo / p).exists() for p in ("components/ui", "src/components/ui",
                                             "app/components/ui", "src/lib/components/ui"))


def _has_api_seam(repo: Path) -> bool:
    return any((repo / p).exists() or (repo / "src" / p).exists() for p in API_SEAM_MARKERS)


def collect(
    slug: str,
    *,
    catalog_entry: dict | None = None,
    annotation: dict | None = None,
    workspace: Path | None = None,
) -> dict:
    """Samla allt vi VET om en venture. Det vi inte vet utelämnas — det gissas aldrig.

    Nycklarna matchar ``check: derived:<signal>`` i ``roadmaps/_recipe.yaml``.
    """
    entry = catalog_entry or {}
    note = annotation or {}
    signals: dict[str, bool] = {}

    # -- ur omdömet (vaulten): finns det alls, inte om det är bra --------------
    if note:
        signals["has_kill_criteria"] = bool(note.get("kill_criteria"))
        signals["has_north_star"] = bool(str(note.get("north_star") or "").strip())

    # -- ur katalogen ----------------------------------------------------------
    if entry:
        signals["has_live_url"] = bool(str(entry.get("url_live") or "").strip())
        deploy = (entry.get("integrations") or {}).get("deploy")
        signals["has_deploy"] = bool(deploy) or signals.get("has_live_url", False)

    decisions = REPO_ROOT / "decisions" / f"{slug}.md"
    signals["has_decision_record"] = decisions.is_file()

    # -- ur repot på disk (starkast signalen: koden själv) ---------------------
    repo = repo_path(slug, workspace)
    signals["has_repo"] = repo is not None
    if repo is not None:
        signals["has_tests"] = _has_tests(repo)
        signals["uses_design_system"] = _uses_design_system(repo)
        signals["has_api_seam"] = _has_api_seam(repo)

    # deploy_healthy mäts INTE ännu (kräver Vercel/Railway-API). Den utelämnas medvetet
    # → dess steg blir `None` ("vet inte"), aldrig falskt grönt. Ärlighet före täckning.

    return signals


def checked_steps(annotation: dict | None) -> set[str]:
    """Manuellt kryssade steg ur vaultens venture-not (``steps_done: [core-flow, ...]``)."""
    done = (annotation or {}).get("steps_done") or []
    return {str(s).strip() for s in done if str(s).strip()}
