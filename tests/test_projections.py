"""Tester för den deklarativa projektionstabellen (scripts/projections.py).

Verifierar att tabellen är kopplad till taxonomin, att no-op/single-writer-semantiken är
konsekvent, och — skelettets gröna lampa — att ett NYTT begrepp ("sprint") är ren data.
"""
from __future__ import annotations

from scripts import projections as pj
from scripts.work_taxonomy import layer_names


def test_every_canonical_is_known():
    known = pj.known_canonicals()
    for p in pj.PROJECTIONS:
        assert p.canonical in known, f"odeklarerat begrepp i projektion: {p.canonical}"


def test_every_layer_has_all_platforms():
    for layer in layer_names():
        for platform in pj.PLATFORMS:
            assert pj.projection(layer, platform) is not None, f"saknar {layer}@{platform}"


def test_github_has_a_home_for_every_layer():
    # GitHub = sanning idag → varje lager har ett native hem (inget no-op).
    for layer in layer_names():
        assert pj.projection(layer, "github").native is not None
        assert not pj.is_noop(layer, "github")


def test_vercel_worklayer_is_noop():
    # Vercel speglar nodlagret, inte arbetslagret → hela hierarkin är no-op.
    for layer in layer_names():
        assert pj.is_noop(layer, "vercel")


def test_linear_declared_but_not_wired():
    # Linear har native-hem men är EJ byggd (mechanism=None) — vakt mot oavsiktlig wiring.
    for layer in layer_names():
        p = pj.projection(layer, "linear")
        assert p.native is not None
        assert p.mechanism is None


def test_single_writer_direction_consistency():
    for p in pj.PROJECTIONS:
        if p.direction == "out":
            assert p.field_owner == "cns", f"{p.canonical}@{p.platform}: out ska ägas av cns"
        elif p.direction == "in":
            assert p.field_owner == p.platform, f"{p.canonical}@{p.platform}: in ska ägas av plattformen"
        else:  # None = no-op
            assert p.native is None


def test_pr_status_is_inbound_github_owned():
    p = pj.projection("pr_status", "github")
    assert p.direction == "in"
    assert p.field_owner == "github"


# --- Skelettets gröna lampa: lägga "sprint" är ren DATA, ingen kärnändring -------------
def test_adding_sprint_is_pure_data():
    """Bevis: ett nytt begrepp läggs som rader i tabellen; getter-logiken är oförändrad.

    GitHub → org-Project Iteration-fält, Linear → Cycle (deklarerad), Vercel utelämnas (no-op).
    """
    sprint_rows = (
        pj.Projection("sprint", "github", "Iteration", "iteration_field", "out", "cns"),
        pj.Projection("sprint", "linear", "Cycle", None, "in", "linear"),
        # Vercel utelämnas medvetet → projection() returnerar None = no-op.
    )
    table = pj.PROJECTIONS + sprint_rows

    assert pj.projection("sprint", "github", table).mechanism == "iteration_field"
    linear = pj.projection("sprint", "linear", table)
    assert linear.native == "Cycle"
    assert linear.mechanism is None  # deklarerad, ej byggd
    assert pj.projection("sprint", "vercel", table) is None
    assert pj.is_noop("sprint", "vercel", table)
