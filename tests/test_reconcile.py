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


# -- blindhet är inte hälsa --------------------------------------------------

def test_a_blind_run_is_never_clean():
    """DEN VIKTIGASTE REGELN HÄR.

    Första CI-körningen var GRÖN och rapporterade "0 motsägelser" — enbart för att vaulten inte
    var klonad och tre av fyra vertikalrepon saknade access. Den mätte sin egen blindhet och
    kallade den hälsa. Att sakna bevis är inte samma sak som att sakna problem.
    """
    r = reconcile.Report(derived=2, annotated=0, merged=45,
                         blind_spots=["vaulten saknas"])
    assert r.is_blind
    assert not r.is_clean          # inga motsägelser funna, men vi såg heller ingenting


def test_blindness_is_shouted_not_whispered():
    text = reconcile.Report(blind_spots=["vaulten saknas — omdömet är osynligt"]).as_text()
    assert "BLIND KÖRNING" in text
    assert "INTE tillförlitligt" in text


def test_a_seeing_run_with_no_findings_is_clean():
    """Motsatsen måste också hålla: ser vi allt och hittar inget, DÅ är det rent."""
    assert reconcile.Report(derived=2, annotated=10, merged=45).is_clean
