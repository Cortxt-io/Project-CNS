"""Skill-export: vaulten äger, .claude/skills/ är en härledd artefakt.

Spec: cns-internal/plans/skill-export-spec.md. Källan är Studio/Skills/<Namn>.md; exporten är
.claude/skills/<slug>/SKILL.md. EN riktning — därav drift-checken: handredigerar någon exporten
har vi två sanningar som tyst säger olika saker, vilket är exakt felet som ruttnade agentur-lagret.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import skill_export as se  # noqa: E402

NOTE = """---
type: skill
prose: description
status: active
skill_name: pr-protokoll
routing: skill
reads: GitHub PR-API
writes: PR-beskrivningar
decays_to: "kod, när checklistan slutat kräva omdöme"
exported: true
tags: [skill]
---

# PR-protokoll

## Routningen — varför är detta en skill och inte kod?

Checklistan kräver omdöme om vad som är riskabelt. Se [[Routningsprincipen]].

## Vad den gör
Ser till att en PR skapas, kopplas och skickas på review korrekt.

## När den ska köras
Använd vid "öppna PR", "begär review", innan en gren mergas.

## Läser · Skriver
| | |
|---|---|
| **Läser** | öppna issues |

## Spärrar
- Vägrar merga utan grön CI

## Steg
1. Kontrollera att grenen har en issue.
"""


def _note(**over) -> str:
    text = NOTE
    for k, v in over.items():
        text = text.replace(f"{k}: ", f"{k}: {v}  # ", 1) if False else text
    return text


# --- parsning + description ------------------------------------------------------------------

def test_description_composes_vad_and_nar() -> None:
    """description = Vad + När. Mallen: 'descriptionen ÄR triggern' — utan NÄR triggar den aldrig."""
    meta, sections = se.parse_skill(NOTE)
    desc = se.compose_description(sections)
    assert "Ser till att en PR skapas" in desc
    assert 'Använd vid "öppna PR"' in desc


def test_missing_nar_is_a_hard_error() -> None:
    """En skill utan NÄR är otriggbar. Det ska falla, inte exporteras tyst."""
    broken = NOTE.replace("## När den ska köras\nAnvänd vid \"öppna PR\", \"begär review\", innan en gren mergas.\n", "")
    meta, sections = se.parse_skill(broken)
    errs = se.validate_skill(meta, sections)
    assert any("När den ska köras" in e for e in errs)


def test_missing_skill_name_is_a_hard_error() -> None:
    meta, sections = se.parse_skill(NOTE.replace("skill_name: pr-protokoll", "skill_name:"))
    assert any("skill_name" in e for e in se.validate_skill(meta, sections))


# --- rendering -------------------------------------------------------------------------------

def test_render_carries_only_claude_code_frontmatter() -> None:
    """Exportens frontmatter = name + description. Vaultens fält (routing, decays_to…) hör inte hit."""
    out = se.render_skill_md(*se.parse_skill(NOTE))
    head = out.split("---")[1]
    assert "name: pr-protokoll" in head
    assert "description:" in head
    for vault_only in ("routing:", "decays_to:", "reads:", "exported:", "prose:"):
        assert vault_only not in head


def test_render_drops_the_routing_rationale() -> None:
    """Routnings-motiveringen är Rikards beslutsunderlag, inte agentens instruktion (och kostar tokens)."""
    out = se.render_skill_md(*se.parse_skill(NOTE))
    assert "Routningen" not in out
    assert "Routningsprincipen" not in out


def test_render_keeps_the_operative_sections() -> None:
    out = se.render_skill_md(*se.parse_skill(NOTE))
    for keep in ("## Spärrar", "Vägrar merga utan grön CI", "## Steg", "## Läser · Skriver"):
        assert keep in out


def test_render_marks_itself_generated() -> None:
    """Utan en genererad-header inbjuder filen till handredigering — och då har vi två sanningar."""
    out = se.render_skill_md(*se.parse_skill(NOTE))
    assert "GENERERAD" in out and "Studio/Skills" in out


# --- export + drift --------------------------------------------------------------------------

def _vault(tmp_path: Path, text: str = NOTE) -> Path:
    d = tmp_path / "Ideaverse" / "Cortxt-io" / "Studio" / "Skills"
    d.mkdir(parents=True)
    (d / "PR-protokoll.md").write_text(text, encoding="utf-8")
    return tmp_path


def test_export_writes_slug_dir_with_skill_md(tmp_path: Path) -> None:
    written = se.export_all(_vault(tmp_path), tmp_path / "out")
    assert written == [tmp_path / "out" / "pr-protokoll" / "SKILL.md"]
    assert "name: pr-protokoll" in written[0].read_text(encoding="utf-8")


def test_export_skips_exported_false(tmp_path: Path) -> None:
    assert se.export_all(_vault(tmp_path, NOTE.replace("exported: true", "exported: false")), tmp_path / "out") == []


def test_drift_check_is_green_right_after_export(tmp_path: Path) -> None:
    root, out = _vault(tmp_path), tmp_path / "out"
    se.export_all(root, out)
    assert se.check_drift(root, out) == []


def test_drift_check_catches_a_hand_edited_export(tmp_path: Path) -> None:
    """Detta är hela poängen med 'en riktning'. Utan denna check är den en förhoppning."""
    root, out = _vault(tmp_path), tmp_path / "out"
    se.export_all(root, out)
    target = out / "pr-protokoll" / "SKILL.md"
    target.write_text(target.read_text(encoding="utf-8") + "\nHandredigerad rad.\n", encoding="utf-8")
    drift = se.check_drift(root, out)
    assert len(drift) == 1 and "pr-protokoll" in drift[0]


def test_drift_check_catches_an_orphan_export(tmp_path: Path) -> None:
    """En GENERERAD export vars källnot raderats ska flaggas — annars lever en skill utan hemvist."""
    root, out = _vault(tmp_path), tmp_path / "out"
    se.export_all(root, out)
    (out / "spoke").mkdir()
    (out / "spoke" / "SKILL.md").write_text(
        "---\nname: spoke\n---\n\n<!-- GENERERAD ur vaulten — redigera INTE här. -->\n", encoding="utf-8"
    )
    assert any("spoke" in d for d in se.check_drift(root, out))


# --- target: vart skillen hör hemma ------------------------------------------------------------
# En skill hör antingen till vaulten (grindskillsen arbetar på vault-noter) eller till Project-CNS.
# EN källa, två destinationer.

VAULT_SKILL = NOTE.replace("skill_name: pr-protokoll", "skill_name: run-gate\ntarget: vault")


def test_target_defaults_to_cns(tmp_path: Path) -> None:
    meta, _ = se.parse_skill(NOTE)
    assert se.target_of(meta) == "cns"


def test_target_vault_is_read_from_frontmatter() -> None:
    meta, _ = se.parse_skill(VAULT_SKILL)
    assert se.target_of(meta) == "vault"


def test_unknown_target_is_a_hard_error() -> None:
    meta, sections = se.parse_skill(NOTE.replace("skill_name: pr-protokoll", "skill_name: x\ntarget: månen"))
    assert any("target" in e for e in se.validate_skill(meta, sections))


def test_export_routes_by_target(tmp_path: Path) -> None:
    """Vault-skills landar i vaultens .claude/skills, CNS-skills i repots."""
    d = tmp_path / "Ideaverse" / "Cortxt-io" / "Studio" / "Skills"
    d.mkdir(parents=True)
    (d / "PR-protokoll.md").write_text(NOTE, encoding="utf-8")
    (d / "Run-gate.md").write_text(VAULT_SKILL, encoding="utf-8")

    written = se.export_all(tmp_path, {"cns": tmp_path / "cns", "vault": tmp_path / "v"})
    assert (tmp_path / "cns" / "pr-protokoll" / "SKILL.md") in written
    assert (tmp_path / "v" / "run-gate" / "SKILL.md") in written


# --- buntade filer -----------------------------------------------------------------------------
# run-gate/references/STEPS.md, demand-scan/scripts/jobtech_scan.py. Exporten får inte tappa dem.


def _bundled(tmp_path: Path) -> Path:
    """Källan som mapp-not: Studio/Skills/<Namn>/<Namn>.md + buntade filer bredvid."""
    d = tmp_path / "Ideaverse" / "Cortxt-io" / "Studio" / "Skills" / "Run-gate"
    (d / "references").mkdir(parents=True)
    (d / "Run-gate.md").write_text(VAULT_SKILL, encoding="utf-8")
    (d / "references" / "STEPS.md").write_text("# Steg\n", encoding="utf-8")
    return tmp_path


def test_export_copies_bundled_files(tmp_path: Path) -> None:
    se.export_all(_bundled(tmp_path), {"vault": tmp_path / "v", "cns": tmp_path / "cns"})
    assert (tmp_path / "v" / "run-gate" / "SKILL.md").is_file()
    assert (tmp_path / "v" / "run-gate" / "references" / "STEPS.md").read_text(encoding="utf-8") == "# Steg\n"


def test_drift_check_covers_bundled_files(tmp_path: Path) -> None:
    """En handredigerad references/-fil är lika mycket drift som en handredigerad SKILL.md."""
    outs = {"vault": tmp_path / "v", "cns": tmp_path / "cns"}
    root = _bundled(tmp_path)
    se.export_all(root, outs)
    assert se.check_drift(root, outs) == []
    (tmp_path / "v" / "run-gate" / "references" / "STEPS.md").write_text("# Handredigerad\n", encoding="utf-8")
    assert any("STEPS.md" in d for d in se.check_drift(root, outs))


def test_hand_written_foreign_skill_is_not_an_orphan(tmp_path: Path) -> None:
    """Inlånade skills (obsidian-markdown, defuddle) gick aldrig genom pipelinen — de är inte våra.

    Drift gäller det vi själva har genererat. Att kräva en källnot för en främmande fil vore att
    göra checken till en gränspolis, och den skulle tvinga fram raderingar av fungerande verktyg.
    """
    root, out = _vault(tmp_path), tmp_path / "out"
    se.export_all(root, out)
    (out / "defuddle").mkdir()
    (out / "defuddle" / "SKILL.md").write_text("---\nname: defuddle\n---\n\nHandskriven.\n", encoding="utf-8")
    assert se.check_drift(root, out) == []
