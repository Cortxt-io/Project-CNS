"""Skill-export — vaulten äger, `.claude/skills/` är en härledd artefakt.

**Varför:** samma mönster som `catalog.yaml`. En skill är *metod* (den överlever att en venture
dör), så källan bor i vaultens `Studio/Skills/`. Men Claude Code kan bara KÖRA en skill som ligger
i `.claude/skills/` — alltså måste källan exporteras dit.

**Tre mål, för laddningstidpunkten är en del av skillen.** Claude Code plockar upp en katalogs
skills först när en fil i den katalogen rörs. En vault-skill exporterad till `vault/.claude/skills/`
dyker därför upp först när vaulten redan är öppnad — efter det beslut skillen skulle ha påverkat.
`skill_usage.py` mätte kostnaden: 1 anrop på 923 transkript, trots att 13 av 16 hade vassa triggers.
Därav `workspace` (arbetsytans rot, laddad från sessionens FÖRSTA prompt) vid sidan av `cns` och
`vault`, som är rätt för skills som ändå bara betyder något i sitt eget repo. `target:` i
källnotens frontmatter väljer. Platsen styr **när skillen laddas**, aldrig vad den får redigera.

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
import os
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


# `cns` och `vault` laddas LAZILY — Claude Code plockar upp en katalogs skills först när en fil i
# den katalogen rörs. Det gör dem värdelösa som triggers: skillen dyker upp efter att beslutet den
# skulle ha påverkat redan är fattat. Mätaren (`skill_usage.py`) visade följden — 1 anrop på 923
# transkript, trots att 13 av 16 hade vassa triggers. `workspace` är arbetsytans rot och den enda
# destination som är laddad från sessionens FÖRSTA prompt.
VALID_TARGETS = ("cns", "vault", "workspace")


def validate_skill(meta: dict, sections: dict[str, str]) -> list[str]:
    """Hårda fel. En otriggbar eller namnlös skill ska falla, inte exporteras tyst."""
    errs: list[str] = []
    if not (meta.get("skill_name") or "").strip():
        errs.append("skill_name saknas — den blir slug och `name:` i exporten")
    if str(meta.get("target") or "cns").strip() not in VALID_TARGETS:
        errs.append(f"okänd target: {meta.get('target')!r} — välj {' eller '.join(VALID_TARGETS)}")
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
    """Källnoterna. Två former, båda giltiga:

    - **Platt:** `Studio/Skills/<Namn>.md` — en skill utan buntade filer.
    - **Mapp-not:** `Studio/Skills/<Namn>/<Namn>.md` — buntade filer (`references/`, `scripts/`)
      ligger bredvid noten och följer med ut. Det är Obsidians egen mappnot-form, så vaulten
      behöver inte lära sig något nytt.
    """
    d = skills_dir(root)
    if not d.is_dir():
        return []
    found = [p for p in d.glob("*.md") if p.stem.lower() != "skills"]
    for sub in d.iterdir():
        if sub.is_dir():
            note = sub / f"{sub.name}.md"
            if note.is_file():
                found.append(note)
    return sorted(found)


def _bundles(src: Path) -> list[Path]:
    """Buntade filer bredvid en mapp-not: allt utom själva noten."""
    if src.parent.name != src.stem:  # platt not → inga buntar
        return []
    return sorted(p for p in src.parent.rglob("*") if p.is_file() and p != src)


def target_of(meta: dict) -> str:
    """Vart skillen hör hemma. Default `cns` — de flesta skills är repo-skills."""
    return str(meta.get("target") or "cns").strip()


def _out_for(target: str, outs: dict[str, Path] | Path | None) -> Path | None:
    """Vart en skill med detta target ska. None = destinationen finns inte i den här miljön.

    Frånvaro är inte fel. CI checkar ut vaulten men har ingen arbetsyta att skriva till — då ska
    `workspace`-skillsen hoppas över, inte fälla bygget.
    """
    if isinstance(outs, dict):
        d = outs.get(target)
        return Path(d) if d else None
    return Path(outs or DEFAULT_OUT)


def workspace_root(vault: Path) -> Path | None:
    """Arbetsytan: $CORTXT_WORKSPACE_PATH, annars vaultens föräldramapp (`cortxt-io/`).

    En katalog är en arbetsyta först när den har en `.claude/` — vaultens förälder är annars vad
    som helst. I CI är den runnerns arbetskatalog, och utan det kravet skulle drift-checken
    rapportera tolv "saknade" exporter mot en yta som inte finns. Frånvaro är inte drift.
    """
    env = os.environ.get("CORTXT_WORKSPACE_PATH")
    cand = Path(env) if env else vault.parent
    return cand if (cand / ".claude").is_dir() else None


def _render_one(path: Path) -> tuple[str, str] | None:
    """→ (slug, innehåll), eller None om noten inte ska exporteras."""
    meta, sections = parse_skill(path.read_text(encoding="utf-8"))
    if meta.get("type") != "skill" or meta.get("exported") is False:
        return None
    errs = validate_skill(meta, sections)
    if errs:
        raise ValueError(f"{path.name}: {'; '.join(errs)}")
    return str(meta["skill_name"]).strip(), render_skill_md(meta, sections, source=path.name)


def _plan(root: Path, outs) -> list[tuple[Path, str, Path, str]]:
    """(källa, slug, exportkatalog, SKILL.md-innehåll) för varje not som ska exporteras."""
    out: list[tuple[Path, str, Path, str]] = []
    for src in _sources(root):
        meta, _ = parse_skill(src.read_text(encoding="utf-8"))
        rendered = _render_one(src)
        if rendered is None:
            continue
        dest_root = _out_for(target_of(meta), outs)
        if dest_root is None:  # destinationen finns inte här — hoppa, fäll inte
            continue
        slug, content = rendered
        out.append((src, slug, dest_root / slug, content))
    return out


def export_all(root: Path, outs: dict[str, Path] | Path | None = None) -> list[Path]:
    """Skriv exporten. `outs` är en katalog, eller {target: katalog}. Returnerar skrivna filer."""
    written: list[Path] = []
    for src, _slug, dest, content in _plan(root, outs):
        dest.mkdir(parents=True, exist_ok=True)
        skill_md = dest / "SKILL.md"
        skill_md.write_text(content, encoding="utf-8")
        written.append(skill_md)
        for b in _bundles(src):
            copy = dest / b.relative_to(src.parent)
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes(b.read_bytes())
            written.append(copy)
    return written


def check_drift(root: Path, outs: dict[str, Path] | Path | None = None) -> list[str]:
    """Vad har drivit isär? Tomt = exporten är exakt vad källan säger.

    Fyra sorters drift: handredigerad SKILL.md, handredigerad buntad fil, saknad export, och
    föräldralös export (källnoten borta). Alla fyra betyder att `.claude/skills/` påstår något
    vaulten inte gör — och en handredigerad `references/STEPS.md` ljuger lika mycket som en
    handredigerad SKILL.md.
    """
    problems: list[str] = []
    expected: dict[Path, set[str]] = {}

    for src, slug, dest, content in _plan(root, outs):
        expected.setdefault(dest.parent, set()).add(slug)

        skill_md = dest / "SKILL.md"
        if not skill_md.is_file():
            problems.append(f"{slug}: exporten saknas — kör `cns skill-export`")
            continue
        if skill_md.read_text(encoding="utf-8") != content:
            problems.append(f"{slug}: exporten är handredigerad — källan är {src.name}, skriv om DEN")

        for b in _bundles(src):
            rel = b.relative_to(src.parent)
            copy = dest / rel
            if not copy.is_file():
                problems.append(f"{slug}/{rel.as_posix()}: buntad fil saknas i exporten")
            elif copy.read_bytes() != b.read_bytes():
                problems.append(f"{slug}/{rel.as_posix()}: buntad fil är handredigerad — skriv om källan")

    # Föräldralösa: en GENERERAD export vars källnot är borta. Handskrivna skills som aldrig gått
    # genom pipelinen (inlånade verktyg som obsidian-markdown, defuddle) rörs inte — de saknar
    # genererad-headern och är därför inte våra. Drift gäller det vi själva har producerat; att
    # kräva att främmande filer har en källnot vore att göra checken till en gränspolis.
    for out_dir, slugs in expected.items():
        if not out_dir.is_dir():
            continue
        for d in sorted(out_dir.iterdir()):
            skill_md = d / "SKILL.md"
            if not (d.is_dir() and skill_md.is_file()) or d.name in slugs:
                continue
            if "GENERERAD ur vaulten" in skill_md.read_text(encoding="utf-8"):
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

    # Tre destinationer, en källa. `cns` och `vault` laddas lazily (per katalog) och är rätt för
    # skills som ändå bara betyder något i sitt repo. `workspace` laddas från första prompten och
    # är där allt som ska vara med FRÅN START bor.
    outs: dict[str, Path] | Path
    if args.out:
        outs = args.out
    else:
        outs = {"cns": DEFAULT_OUT, "vault": root / ".claude" / "skills"}
        ws = workspace_root(root)
        if ws:
            outs["workspace"] = ws / ".claude" / "skills"

    if args.check:
        problems = check_drift(root, outs)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print(f"{len(problems)} skill(s) har drivit isär." if problems
              else "Exporten är exakt vad vaulten säger.")
        return 1 if problems else 0

    written = export_all(root, outs)
    skills = sorted(p for p in written if p.name == "SKILL.md")
    bundles = len(written) - len(skills)
    where_of = {str(Path(d).resolve()): t for t, d in outs.items()} if isinstance(outs, dict) else {}
    for w in skills:
        where = where_of.get(str(w.parent.parent.resolve()), "?")
        print(f"  [{where}] {w.parent.name}")
    print(f"Exporterade {len(skills)} skill(s) + {bundles} buntad(e) fil(er) ur Studio/Skills/.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
