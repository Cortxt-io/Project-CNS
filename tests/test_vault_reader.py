"""Tester för vault_reader — handlagret (Obsidian) som annoteringskälla.

Kontraktet: läs venture-frontmatter ur vaulten, validera den mot annotation.schema.json,
och håll referensintegriteten som JSON Schema INTE kan hålla (node: → catalog-slug).

Rena funktioner tar in data; IO-skalet testas mot en tmp-vault. Ingen riktig vault, inget nät.
"""
from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

import pytest

from lab.scripts import vault_reader as vr


# -- fixtures ----------------------------------------------------------------

def _note(body: str) -> str:
    return textwrap.dedent(body).lstrip()


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """En minimal men verklighetstrogen vault: två ventures + en pre-gate-idé."""
    verticals = tmp_path / "Ideaverse" / "Cortxt" / "Verticals"

    (verticals / "juvahem").mkdir(parents=True)
    (verticals / "juvahem" / "juvahem.md").write_text(_note("""
        ---
        node: juvahem
        type: venture
        owner: rikard
        gate_decision: go
        gate_date: 2026-06-01
        steps_done:
          - core-flow
        north_star: 10 par som flyttat
        kill_criteria:
          - Ingen betalande användare efter 3 månader
        next_action: Koppla Kolada-ETL steg 2
        last_reviewed: 2026-07-01
        ---

        # juvahem

        ## Pitch

        Rankar 290 kommuner mot ett pars gemensamma profil.

        Andra stycket ska INTE hamna i pitchen.

        ## Annat
        """), encoding="utf-8")

    (verticals / "orgkomp").mkdir(parents=True)
    (verticals / "orgkomp" / "orgkomp.md").write_text(_note("""
        ---
        node: orgkomp
        type: venture
        owner: rikard
        last_reviewed: 2026-07-11
        ---

        # orgkomp
        """), encoding="utf-8")

    pipeline = verticals / "_pipeline"
    pipeline.mkdir(parents=True)
    (pipeline / "RankSweden.md").write_text(_note("""
        ---
        node: none
        type: idea
        owner: rikard
        last_reviewed: 2026-07-10
        ---

        # RankSweden
        """), encoding="utf-8")

    return tmp_path


# -- läsning -----------------------------------------------------------------

def test_load_annotations_keys_by_node_slug(vault: Path):
    ann = vr.load_annotations(vault)
    assert set(ann) == {"juvahem", "orgkomp", "RankSweden"}
    assert ann["juvahem"]["gate_decision"] == "go"
    assert ann["juvahem"]["owner"] == "rikard"


def test_ideas_key_by_filename_since_node_is_none(vault: Path):
    """Pre-gate-idéer har node: none — de kan inte kollidera på slugen 'none'."""
    ann = vr.load_annotations(vault)
    assert ann["RankSweden"]["node"] == "none"
    assert ann["RankSweden"]["type"] == "idea"


def test_missing_vault_degrades_to_empty(tmp_path: Path):
    """Saknad vault → tomt, aldrig krasch (samma mönster som roadmap.py)."""
    assert vr.load_annotations(tmp_path / "finns-inte") == {}


def test_pitch_is_first_paragraph_under_heading(vault: Path):
    ann = vr.load_annotations(vault)
    assert ann["juvahem"]["pitch"] == "Rankar 290 kommuner mot ett pars gemensamma profil."
    assert "Andra stycket" not in ann["juvahem"]["pitch"]


def test_pitch_absent_when_no_heading(vault: Path):
    ann = vr.load_annotations(vault)
    assert ann["orgkomp"].get("pitch", "") == ""


# -- schemavalidering --------------------------------------------------------

def test_valid_annotation_has_no_errors():
    assert vr.validate_annotation({
        "node": "juvahem", "type": "venture", "owner": "rikard",
        "last_reviewed": "2026-07-01",
    }) == []


def test_unknown_gate_decision_is_rejected():
    """Go/Kill/Hold/Recycle — lånat från Stage-Gate, inte påhittat."""
    errors = vr.validate_annotation({
        "node": "juvahem", "type": "venture", "owner": "rikard",
        "gate_decision": "kanske", "last_reviewed": "2026-07-01",
    })
    assert any("gate_decision" in e for e in errors)


def test_the_phase_is_not_a_hand_field():
    """Fasen HÄRLEDS. Skriver du den för hand är det inte längre en mätning."""
    ann = vr.validate_annotation({
        "node": "juvahem", "type": "venture", "owner": "rikard",
        "last_reviewed": "2026-07-01", "steps_done": ["core-flow"],
    })
    assert ann == []


def test_missing_required_field_is_rejected():
    errors = vr.validate_annotation({"node": "juvahem", "type": "venture"})
    assert errors


def test_a_venture_must_be_backed_by_a_catalog_node():
    """type: venture utan CNS-nod = något som påstår sig vara byggt men inte finns."""
    errors = vr.validate_annotation({
        "node": "none", "type": "venture", "owner": "rikard",
        "last_reviewed": "2026-07-01",
    })
    assert errors


def test_a_kill_must_be_dated():
    """En odaterad kill kan aldrig bli gammal — och det är precis så ett dött projekt
    fortsätter kosta i tysthet."""
    errors = vr.validate_annotation({
        "node": "juvahem", "type": "venture", "owner": "rikard",
        "gate_decision": "kill", "last_reviewed": "2026-07-01",
    })
    assert errors


# -- referensintegritet (det JSON Schema INTE kan) ---------------------------

def test_node_pointing_at_unknown_catalog_slug_is_a_finding(vault: Path):
    findings = vr.check(vault, catalog_slugs={"orgkomp"})   # juvahem saknas i katalogen
    assert any(f.slug == "juvahem" and "katalog" in f.message.lower() for f in findings)


def test_idea_with_node_none_is_not_a_reference_finding(vault: Path):
    findings = vr.check(vault, catalog_slugs={"juvahem", "orgkomp"})
    assert not any(f.slug == "RankSweden" for f in findings)


def test_duplicate_node_slug_across_notes_is_a_finding(vault: Path):
    dup = vault / "Ideaverse" / "Cortxt" / "Verticals" / "dubblett"
    dup.mkdir()
    (dup / "dubblett.md").write_text(_note("""
        ---
        node: juvahem
        type: venture
        owner: rikard
        last_reviewed: 2026-07-01
        ---
        """), encoding="utf-8")

    findings = vr.check(vault, catalog_slugs={"juvahem", "orgkomp"})
    assert any("dubblett" in f.message.lower() or "duplicate" in f.message.lower()
               for f in findings)


# -- staleness (den lucka prior art inte löser) ------------------------------

def test_annotation_age_counts_days_since_review():
    assert vr.annotation_age_days("2026-07-01", today=date(2026, 7, 12)) == 11


def test_missing_last_reviewed_gives_unknown_age():
    assert vr.annotation_age_days(None, today=date(2026, 7, 12)) is None


def test_a_live_venture_goes_stale_faster_than_an_idea():
    """SLA:t nycklas på den HÄRLEDDA fasen: det som möter användare är färskvara."""
    assert vr.is_stale(phase="live", age_days=45) is True
    assert vr.is_stale(phase="discovery", age_days=45) is False


def test_a_killed_venture_never_nags():
    """Grinden sa kill. Då är det dött, och dött tjatar inte."""
    assert vr.is_stale(phase="live", age_days=900, gate_decision="kill") is False


# -- verklighetens vault (regressioner från första körningen mot riktiga noter) ----

def test_empty_frontmatter_key_is_dropped_not_passed_as_none(vault: Path):
    """`url_live:` utan värde blir None i YAML — inte en tom sträng.

    Skickas det vidare failar schemat på 'None is not of type string' för ett fält användaren
    aldrig fyllt i. Frånvaro ska betyda frånvaro.
    """
    note = vault / "Ideaverse" / "Cortxt" / "Verticals" / "orgkomp" / "orgkomp.md"
    note.write_text(_note("""
        ---
        node: orgkomp
        type: venture
        owner: rikard
        last_reviewed: 2026-07-11
        url_live:
        next_action:
        ---

        # orgkomp
        """), encoding="utf-8")

    ann = vr.load_annotations(vault)
    assert "url_live" not in ann["orgkomp"]
    assert vr.check(vault, catalog_slugs={"juvahem", "orgkomp"}) == []


def test_reference_notes_are_not_scanned_as_ventures(vault: Path):
    """_pipeline/README.md är en förklaringsnot, inte en idé. Den ska inte valideras som venture."""
    readme = vault / "Ideaverse" / "Cortxt" / "Verticals" / "_pipeline" / "README.md"
    readme.write_text(_note("""
        ---
        type: reference
        ---

        # Så funkar pipelinen
        """), encoding="utf-8")

    ann = vr.load_annotations(vault)
    assert "README" not in ann
    assert not any(f.slug == "README" for f in vr.check(vault, catalog_slugs={"juvahem", "orgkomp"}))
