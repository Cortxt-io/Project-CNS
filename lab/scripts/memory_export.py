"""Exportera minnen ur vaulten till ~/.claude/…/memory/.

Samma riktning som skills: **vaulten äger, exporten är genererad.** Redigerar du exporten glider den
från källan, och då finns två sanningar som tyst säger olika saker.

Varför minnena flyttade in i vaulten 2026-07-13:

En hel arbetsdag styrdes av ett minne Rikard aldrig sett. Det sa *"dra honom ur verktygsladan till
produkt/värde"* — rimligt när det skrevs, fel den dagen, och det gjorde att pluginet kallades en
distraktion sex gånger trots att det är leveransfordonet för en betalande kund.

Minnet gick inte att rätta, för det låg i `~/.claude/` och var osynligt. **Du kan inte rätta det du
inte kan se.** Femtio sådana filer styrde arbetet.

Nu bor de i `Studio/Memory/`, syns i Obsidian, och kan läsas och rättas av den de handlar om.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# Vad harness:en faktiskt matchar på. En okänd art blir tyst ignorerad — så vi vägrar den i stället.
VALID_TYPES = ("user", "feedback", "project", "reference")

FM = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", re.S)

BANNER = (
    "<!-- GENERERAD ur vaulten — redigera INTE här.\n"
    "     Källa: Ideaverse/Cortxt-io/Studio/Memory/{source}\n"
    "     Skriv om källnoten och kör `cns memory-export`. En riktning. -->"
)


def parse_memory(text: str) -> tuple[dict, dict[str, str]]:
    """Dela en minnesnot i (frontmatter, {rubrik: brödtext}). Rubriker är `## `-nivå."""
    m = FM.match(text)
    if not m:
        return {}, {}
    meta = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)

    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current:
                sections[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        elif current:
            buf.append(line)
    if current:
        sections[current] = "\n".join(buf).strip()
    return meta, sections


def _strip_markup(text: str) -> str:
    text = re.sub(r"\[\[([^\]|]+)(\|[^\]]+)?\]\]", r"\1", text)
    text = re.sub(r"[*_`>#]", "", text)
    return " ".join(text.split())


def compose_description(sections: dict[str, str]) -> str:
    """Descriptionen är det harness:en matchar på när den avgör att ett minne är relevant.

    Utan den syns minnet aldrig — samma tysta fel som en skill utan `När den ska köras`.
    """
    return _strip_markup(sections.get("Vad jag ska minnas", ""))[:400]


def validate_memory(meta: dict, sections: dict[str, str]) -> list[str]:
    """Hårda fel. Ett minne som aldrig kan träffa ska falla, inte exporteras tyst."""
    errs: list[str] = []
    if not str(meta.get("memory_name") or "").strip():
        errs.append("memory_name saknas — det blir filnamn och `name:` i exporten")
    mt = str(meta.get("memory_type") or "").strip()
    if mt not in VALID_TYPES:
        errs.append(f"okänd memory_type: {mt!r} — välj {' | '.join(VALID_TYPES)}")
    if not compose_description(sections):
        errs.append("'## Vad jag ska minnas' saknas eller är tom — det ÄR descriptionen, och utan den syns minnet aldrig")
    return errs


def _yaml_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_memory(meta: dict, sections: dict[str, str], source: str = "") -> str:
    name = str(meta["memory_name"]).strip()
    body = "\n\n".join(
        f"## {h}\n\n{t}" for h, t in sections.items() if h != "Vad jag ska minnas"
    )
    head = sections.get("Vad jag ska minnas", "").strip()

    return (
        "---\n"
        f"name: {name}\n"
        f"description: {_yaml_quote(compose_description(sections))}\n"
        "metadata:\n"
        f"  type: {meta['memory_type']}\n"
        "---\n\n"
        + BANNER.format(source=source or f"{name}.md")
        + f"\n\n{head}\n\n{body}\n".rstrip()
        + "\n"
    )


def render_index(rows: list[tuple[str, str, str]]) -> str:
    """MEMORY.md — den enda filen harness:en läser vid varje sessionsstart."""
    lines = [
        "# Minnesindex",
        "",
        "<!-- GENERERAD ur Studio/Memory/. Redigera inte här. -->",
        "",
    ]
    for kind in VALID_TYPES:
        group = [r for r in rows if r[1] == kind]
        if not group:
            continue
        lines += [f"## {kind}", ""]
        lines += [f"- [{name}]({name}.md) — {hook}" for name, _, hook in sorted(group)]
        lines += [""]
    return "\n".join(lines)


def export_memories(src: Path, dest: Path) -> int:
    """Skriv exporten. Returnerar antalet minnen.

    Raderar exporter vars källnot är borta — annars lever ett rättat (eller ogiltigförklarat) minne
    kvar i exporten och fortsätter styra. Det är hela poängen med en riktning.
    """
    dest.mkdir(parents=True, exist_ok=True)

    rows: list[tuple[str, str, str]] = []
    written: set[str] = set()

    for p in sorted(src.glob("*.md")):
        meta, sections = parse_memory(p.read_text(encoding="utf-8"))
        if meta.get("type") != "memory" or meta.get("exported") is False:
            continue
        errs = validate_memory(meta, sections)
        if errs:
            raise ValueError(f"{p.name}: {'; '.join(errs)}")
        name = str(meta["memory_name"]).strip()
        (dest / f"{name}.md").write_text(render_memory(meta, sections, source=p.name), encoding="utf-8")
        written.add(f"{name}.md")
        rows.append((name, str(meta["memory_type"]), compose_description(sections)[:160]))

    (dest / "MEMORY.md").write_text(render_index(rows), encoding="utf-8")

    for old in dest.glob("*.md"):
        if old.name != "MEMORY.md" and old.name not in written:
            old.unlink()

    return len(rows)


def _default_src() -> Path | None:
    """Studio/Memory/ i vaulten. Samma vault-upplösning som skill_export — en mekanism, inte två."""
    from scripts.skill_export import vault_root  # samma söklogik, ingen andra kopia

    root = vault_root(None)
    return None if root is None else root / "Ideaverse" / "Cortxt-io" / "Studio" / "Memory"


def _default_dest() -> Path:
    """Katalogen harness:en faktiskt läser vid varje sessionsstart."""
    return Path.home() / ".claude" / "projects" / "C--Users-rikar-Cortxt-io" / "memory"


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Exportera minnen ur vaulten till ~/.claude/…/memory/")
    ap.add_argument("--src", type=Path, default=None, help="Studio/Memory/ (default: ur vaulten)")
    ap.add_argument("--dest", type=Path, default=None, help="~/.claude/projects/<slug>/memory/")
    ap.add_argument("--check", action="store_true", help="Fall om exporten inte matchar vaulten")
    a = ap.parse_args(argv)

    if a.src is None:
        a.src = _default_src()
        if a.src is None:
            print("Ingen vault hittad (sätt CORTXT_VAULT_PATH eller lägg den som ../vault).", file=sys.stderr)
            return 1
    if a.dest is None:
        a.dest = _default_dest()

    if a.check:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            export_memories(a.src, Path(tmp))
            drift = [
                p.name
                for p in sorted(Path(tmp).glob("*.md"))
                if not (a.dest / p.name).exists()
                or (a.dest / p.name).read_text(encoding="utf-8") != p.read_text(encoding="utf-8")
            ]
        if drift:
            print("Exporten säger inte vad vaulten säger:", ", ".join(drift), file=sys.stderr)
            return 1
        print("Exporten är exakt vad vaulten säger.")
        return 0

    n = export_memories(a.src, a.dest)
    print(f"Exporterade {n} minne(n) ur Studio/Memory/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
