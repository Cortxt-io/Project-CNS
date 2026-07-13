"""Skill-export — vaulten äger, `.claude/skills/` är en härledd artefakt.

**Varför:** samma mönster som `catalog.yaml`. En skill är *metod* (den överlever att en venture
dör), så källan bor i vaultens `Studio/Skills/`. Men Claude Code kan bara KÖRA en skill som ligger
i `.claude/skills/` — alltså måste källan exporteras dit.

**En riktning.** Vaultens `_templates/Skill.md` säger det själv: "Redigerar du exporten glider den
från källan, och då har du två sanningar som tyst säger olika saker." Därav `check_drift()`. Utan
den är "en riktning" en förhoppning, och tyst divergens mellan två beskrivningar av samma sak är
exakt felet som ruttnade agentur-lagret.

**Vad som exporteras:** bara det operativa. Routnings-motiveringen (varför detta är en skill och
inte kod) är Rikards beslutsunderlag, inte agentens arbetsinstruktion — den stannar i vaulten och
kostar inga tokens i varje skill-laddning.

Spec: `cns-internal/plans/skill-export-spec.md`.

Kör:
    python lab/cns_lab.py skill-export           # skriv exporten
    python lab/cns_lab.py skill-export --check   # falla om något drivit isär (CI)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scripts.vault_reader import parse_note, vault_root

SKILLS_SUBDIR = ("Ideaverse", "Cortxt-io", "Studio", "Skills")
DEFAULT_OUT = Path(__file__).resolve().parent.parent / ".claude" / "skills"

# Sektioner som ALDRIG följer med ut. Motiveringen är beslutsunderlag, inte instruktion.
DROP_SECTIONS = ("routningen",)

GENERATED_HEADER = (
    "<!-- GENERERAD ur vaulten — redigera INTE här.\n"
    "     Källa: Ideaverse/Cortxt-io/Studio/Skills/{source}\n"
    "     Skriv om källnoten och kör `cns skill-export`. En riktning. -->"
)


# --- parsning --------------------------------------------------------------------------------


def parse_skill(text: str) -> tuple[dict, dict[str, str]]:
    """Dela en skill-not i (frontmatter, {rubrik: brödtext}). Rubriker är `## `-nivå."""
    meta, body = parse_note(text)
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current, buf = line[3:].strip(), []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return meta, sections


def _section(sections: dict[str, str], prefix: str) -> str | None:
    """Hämta en sektion på prefix (rubriker bär em-dash och varierar i svans)."""
    for head, body in sections.items():
        if head.lower().startswith(prefix.lower()):
            return body
    return None


def _strip_markup(text: str) -> str:
    """Gör en sektion till en rad prosa: inga callouts, länkar, kursiv-parenteser eller radbrytningar."""
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith(">")]
    out = " ".join(lines)
    out = re.sub(r"_\(.*?\)_", "", out)          # mallens ifyll-hjälp
    out = re.sub(r"\[\[([^\]|]+)\|?[^\]]*\]\]", r"\1", out)  # [[länk|text]] → länk
    return re.sub(r"\s+", " ", out).strip()


def compose_description(sections: dict[str, str]) -> str:
    """description = VAD + NÄR.

    Mallen är explicit: "descriptionen ÄR triggern — bara namn och beskrivning förladdas, så en vag
    beskrivning betyder att skillen aldrig aktiveras." Därför krävs båda.
    """
    vad = _strip_markup(_section(sections, "Vad den gör") or "")
    nar = _strip_markup(_section(sections, "När den ska köras") or "")
    return " ".join(p for p in (vad, nar) if p).strip()


def validate_skill(meta: dict, sections: dict[str, str]) -> list[str]:
    """Hårda fel. En otriggbar eller namnlös skill ska falla, inte exporteras tyst."""
    errs: list[str] = []
    if not (meta.get("skill_name") or "").strip():
        errs.append("skill_name saknas — den blir slug och `name:` i exporten")
    if not _strip_markup(_section(sections, "Vad den gör") or ""):
        errs.append("'## Vad den gör' saknas eller är tom — halva descriptionen (triggern)")
    if not _strip_markup(_section(sections, "När den ska köras") or ""):
        errs.append("'## När den ska köras' saknas eller är tom — utan NÄR triggar skillen aldrig")
    return errs


# --- rendering -------------------------------------------------------------------------------


def _yaml_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_skill_md(meta: dict, sections: dict[str, str], source: str = "") -> str:
    """Rendera exportens SKILL.md. Frontmatter = bara det Claude Code kräver (name + description)."""
    errs = validate_skill(meta, sections)
    if errs:
        raise ValueError("; ".join(errs))

    name = str(meta["skill_name"]).strip()
    body_parts: list[str] = []
    for head, text in sections.items():
        if head.lower().startswith(DROP_SECTIONS):
            continue
        body_parts.append(f"## {head}\n\n{text}" if text else f"## {head}")

    return (
        "---\n"
        f"name: {name}\n"
        f"description: {_yaml_quote(compose_description(sections))}\n"
        "---\n\n"
        + GENERATED_HEADER.format(source=source or f"{name}.md")
        + f"\n\n# {name}\n\n"
        + "\n\n".join(body_parts)
        + "\n"
    )


# --- export + drift --------------------------------------------------------------------------


def skills_dir(root: Path) -> Path:
    return root.joinpath(*SKILLS_SUBDIR)


def _sources(root: Path) -> list[Path]:
    d = skills_dir(root)
    if not d.is_dir():
        return []
    # Mappnoten (Skills.md) är ett index, inte en skill.
    return sorted(p for p in d.glob("*.md") if p.stem.lower() != "skills")


def _render_one(path: Path) -> tuple[str, str] | None:
    """→ (slug, innehåll), eller None om noten inte ska exporteras."""
    meta, sections = parse_skill(path.read_text(encoding="utf-8"))
    if meta.get("type") != "skill" or meta.get("exported") is False:
        return None
    errs = validate_skill(meta, sections)
    if errs:
        raise ValueError(f"{path.name}: {'; '.join(errs)}")
    return str(meta["skill_name"]).strip(), render_skill_md(meta, sections, source=path.name)


def export_all(root: Path, out_dir: Path | None = None) -> list[Path]:
    """Skriv exporten. Returnerar de filer som skrevs."""
    out_dir = Path(out_dir or DEFAULT_OUT)
    written: list[Path] = []
    for src in _sources(root):
        rendered = _render_one(src)
        if rendered is None:
            continue
        slug, content = rendered
        target = out_dir / slug / "SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)
    return written


def check_drift(root: Path, out_dir: Path | None = None) -> list[str]:
    """Vad har drivit isär? Tomt = exporten är exakt vad källan säger.

    Tre sorters drift: handredigerad export, saknad export, och föräldralös export (källnoten
    borta). Alla tre betyder att `.claude/skills/` påstår något vaulten inte gör.
    """
    out_dir = Path(out_dir or DEFAULT_OUT)
    problems: list[str] = []
    expected: set[str] = set()

    for src in _sources(root):
        rendered = _render_one(src)
        if rendered is None:
            continue
        slug, content = rendered
        expected.add(slug)
        target = out_dir / slug / "SKILL.md"
        if not target.is_file():
            problems.append(f"{slug}: exporten saknas — kör `cns skill-export`")
        elif target.read_text(encoding="utf-8") != content:
            problems.append(f"{slug}: exporten är handredigerad — källan är {src.name}, skriv om DEN")

    if out_dir.is_dir():
        for d in sorted(out_dir.iterdir()):
            if d.is_dir() and (d / "SKILL.md").is_file() and d.name not in expected:
                problems.append(f"{d.name}: export utan källnot i Studio/Skills/ — föräldralös")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="falla om exporten drivit isär från vaulten")
    ap.add_argument("--vault", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    root = vault_root(args.vault)
    if root is None:
        print("Ingen vault hittad (sätt CORTXT_VAULT_PATH eller lägg den som ../vault).", file=sys.stderr)
        return 1

    if args.check:
        problems = check_drift(root, args.out)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print(f"{len(problems)} skill(s) har drivit isär." if problems
              else "Exporten är exakt vad vaulten säger.")
        return 1 if problems else 0

    written = export_all(root, args.out)
    for w in written:
        print(f"  {w.parent.name}/SKILL.md")
    print(f"Exporterade {len(written)} skill(s) ur Studio/Skills/.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
