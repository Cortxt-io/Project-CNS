"""Minnen bor i vaulten och exporteras — samma riktning som skills.

Bakgrunden: 2026-07-13 styrdes en hel arbetsdag av ett minne Rikard aldrig sett. Det sa "dra honom
ur verktygsladan till produkt/värde", vilket var rimligt när det skrevs och fel den dagen — och det
gick inte att rätta, för det låg i ~/.claude/ och var osynligt.

Du kan inte rätta det du inte kan se. Därför äger vaulten minnet; ~/.claude/ är exporten.
"""
from pathlib import Path

import pytest

from lab.scripts.memory_export import (
    export_memories,
    parse_memory,
    render_memory,
    render_index,
    validate_memory,
)

SRC = """---
type: memory
memory_name: verifiera-mot-kalla
memory_type: feedback
status: active
---

# verifiera-mot-kalla

## Vad jag ska minnas

I sanningsdokument — verifiera mot källkod, gissa inte.

## Varför

Rikard fångade att jag gissat om Redis när källan låg en filöppning bort.

## Hur jag tillämpar det

Läs filen. Rätta felkällan, inte bara den härledda artefakten.
"""


def test_parse_reads_frontmatter_and_sections():
    meta, sections = parse_memory(SRC)
    assert meta["memory_name"] == "verifiera-mot-kalla"
    assert meta["memory_type"] == "feedback"
    assert "verifiera mot källkod" in sections["Vad jag ska minnas"]


def test_export_renders_the_shape_claude_actually_reads():
    """The harness reads name/description/metadata.type — get those wrong and the memory is inert."""
    meta, sections = parse_memory(SRC)
    out = render_memory(meta, sections, source="verifiera-mot-kalla.md")

    assert out.startswith("---\n")
    assert "name: verifiera-mot-kalla" in out
    assert "type: feedback" in out
    # The description is what the harness matches on when deciding a memory is relevant.
    assert "description:" in out
    assert "verifiera mot källkod" in out
    # A generated file must say so, or someone will edit it and lose the edit on the next export.
    assert "GENERERAD" in out


def test_a_memory_without_a_description_is_inert_and_must_fail_loudly():
    """A memory with no description never surfaces. Silence there is the failure we keep hitting."""
    broken = SRC.replace("## Vad jag ska minnas\n\nI sanningsdokument — verifiera mot källkod, gissa inte.\n", "")
    meta, sections = parse_memory(broken)
    errs = validate_memory(meta, sections)
    assert any("Vad jag ska minnas" in e for e in errs)


def test_unknown_memory_type_is_rejected():
    meta, sections = parse_memory(SRC.replace("memory_type: feedback", "memory_type: vibes"))
    errs = validate_memory(meta, sections)
    assert any("vibes" in e for e in errs)


def test_index_lists_every_memory_with_its_hook():
    lines = render_index([
        ("verifiera-mot-kalla", "feedback", "Verifiera mot källkod, gissa inte"),
        ("maskin-8gb-ram", "reference", "Datorn är minnesknapp"),
    ])
    assert "- [verifiera-mot-kalla](verifiera-mot-kalla.md) — Verifiera mot källkod" in lines
    assert "maskin-8gb-ram.md" in lines


def test_export_writes_files_and_index(tmp_path: Path):
    src = tmp_path / "Memory"
    src.mkdir()
    (src / "verifiera-mot-kalla.md").write_text(SRC, encoding="utf-8")
    dest = tmp_path / "out"

    written = export_memories(src, dest)

    assert (dest / "verifiera-mot-kalla.md").exists()
    assert (dest / "MEMORY.md").exists()
    assert written == 1
    assert "verifiera-mot-kalla" in (dest / "MEMORY.md").read_text(encoding="utf-8")


def test_export_removes_a_memory_deleted_from_the_vault(tmp_path: Path):
    """The vault is the source. Delete the note and the export must follow, or a corrected memory
    lives on in the export and keeps steering."""
    src = tmp_path / "Memory"
    src.mkdir()
    (src / "verifiera-mot-kalla.md").write_text(SRC, encoding="utf-8")
    dest = tmp_path / "out"
    dest.mkdir()
    stale = dest / "gammalt-minne.md"
    stale.write_text("---\nname: gammalt-minne\n---\nfel sedan länge\n", encoding="utf-8")

    export_memories(src, dest)

    assert not stale.exists()
    assert (dest / "verifiera-mot-kalla.md").exists()


def test_a_memory_note_that_is_not_type_memory_is_skipped(tmp_path: Path):
    src = tmp_path / "Memory"
    src.mkdir()
    (src / "Memory.md").write_text("---\ntype: index\n---\n# Memory\n", encoding="utf-8")
    dest = tmp_path / "out"
    assert export_memories(src, dest) == 0
