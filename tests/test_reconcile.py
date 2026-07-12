"""Tester för reconcile — rapporten får aldrig vara tyst.

Den farligaste buggen i ett reconcile-jobb är inte att det säger fel. Det är att det säger
INGENTING och därmed ser ut att ha godkänt allt. "Grönt" och "körde aldrig" ser identiska ut
om man inte tvingar rapporten att räkna.
"""
from __future__ import annotations

from lab.scripts import reconcile


def test_a_clean_report_is_clean():
    assert reconcile.Report(derived=3, annotated=2, merged=5).is_clean


def test_orphans_make_it_unclean():
    r = reconcile.Report(orphans=["local-ai — ingen backing"])
    assert not r.is_clean


def test_contradictions_make_it_unclean():
    r = reconcile.Report(contradictions=["orgkomp: kan aldrig dö"])
    assert not r.is_clean


def test_unbacked_alone_is_not_a_verdict():
    """Utan-backing är en KANDIDAT, inte en dom. Heuristiken flaggar; den dömer inte.

    Om en gissning fick fälla katalogen skulle vi trimma gissningen tills den slutade klaga —
    och då hade vi en heuristik som alltid säger ja.
    """
    r = reconcile.Report(unbacked=["orgkomp-graph — hittades inte (men har en not)"])
    assert r.is_clean


def test_the_report_shows_what_it_did_not_just_what_it_found():
    """En rapport som bara listar fel kan inte skiljas från en som aldrig kördes."""
    text = reconcile.Report(derived=2, annotated=10, merged=45).as_text()
    assert "härlett: 2" in text
    assert "annoterat (vault): 10" in text
    assert "sammanslaget: 45" in text


def test_every_section_prints_its_count_even_when_empty():
    text = reconcile.Report().as_text()
    for heading in ("Orphans: 0", "Motsägelser (härlett vs deklarerat): 0"):
        assert heading in text


def test_run_against_the_real_repo_produces_a_report():
    """Rökprov: den kör, och den ljuger inte om att ha gjort något."""
    report = reconcile.run(write=False)
    assert report.merged > 0
    assert isinstance(report.orphans, list)
