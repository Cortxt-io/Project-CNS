"""Tests for scripts.triage — the shared idea-grouping logic (#39)."""

from datetime import datetime

from scripts.triage import group_ideas, render_triage

NOW = datetime(2026, 6, 14, 12, 0, 0)


def _idea(idea_id, text="", slug=None, days_old=0, status="open"):
    created = datetime(2026, 6, 14, 12, 0, 0)
    created = created.replace(day=14 - days_old) if days_old <= 13 else datetime(2026, 5, 31)
    return {
        "id": idea_id,
        "text": text,
        "slug": slug,
        "created_at": created.isoformat(timespec="seconds"),
        "status": status,
    }


def test_untriaged_are_ideas_without_slug():
    ideas = [_idea("idea-1", "x" * 50, slug="cns-core"), _idea("idea-2", "loose thought")]
    g = group_ideas(ideas, now=NOW)
    assert [i["id"] for i in g["untriaged"]] == ["idea-2"]
    assert g["counts"]["untriaged"] == 1


def test_mature_requires_slug_and_concrete_body():
    long_text = "Build a concrete deliverable that is clearly described here."
    ideas = [
        _idea("idea-mature", long_text, slug="cns-core"),
        _idea("idea-short", "too short", slug="cns-core"),
        _idea("idea-noslug", long_text),
        _idea("idea-vague", "open riktningsfråga about direction " + "x" * 40, slug="cns-core"),
    ]
    g = group_ideas(ideas, now=NOW)
    assert [i["id"] for i in g["mature"]] == ["idea-mature"]


def test_stale_is_old_and_untriaged():
    ideas = [
        _idea("idea-old", "ancient loose thought", days_old=20),
        _idea("idea-fresh", "fresh loose thought", days_old=1),
        _idea("idea-old-homed", "x" * 50, slug="cns-core", days_old=20),  # homed → not stale
    ]
    g = group_ideas(ideas, now=NOW)
    assert [i["id"] for i in g["stale"]] == ["idea-old"]


def test_clusters_need_two_sharing_a_slug():
    ideas = [
        _idea("idea-a", "x" * 50, slug="cns-core"),
        _idea("idea-b", "x" * 50, slug="cns-core"),
        _idea("idea-c", "x" * 50, slug="interface"),  # lone slug → no cluster
    ]
    g = group_ideas(ideas, now=NOW)
    assert len(g["clusters"]) == 1
    assert g["clusters"][0]["slug"] == "cns-core"
    assert {i["id"] for i in g["clusters"][0]["ideas"]} == {"idea-a", "idea-b"}


def test_non_open_ideas_are_ignored():
    ideas = [
        _idea("idea-open", "loose", status="open"),
        _idea("idea-promoted", "loose", status="promoted"),
        _idea("idea-resolved", "loose", status="resolved"),
    ]
    g = group_ideas(ideas, now=NOW)
    assert g["counts"]["open"] == 1
    assert [i["id"] for i in g["untriaged"]] == ["idea-open"]


def test_unparseable_created_at_does_not_crash_staleness():
    ideas = [{"id": "idea-x", "text": "loose", "slug": None, "created_at": "not-a-date", "status": "open"}]
    g = group_ideas(ideas, now=NOW)
    assert g["stale"] == []
    assert [i["id"] for i in g["untriaged"]] == ["idea-x"]


def test_find_overlaps_flags_similar_text_across_slugs():
    ideas = [
        _idea("idea-a", "Build a triage tool that groups ideas into clusters and stale buckets", slug="cns-core"),
        _idea("idea-b", "Triage tool grouping ideas: clusters, stale buckets, mature promotion", slug="interface"),
        _idea("idea-c", "Completely unrelated thought about Vercel deploy adapters and storefront", slug="cortxt"),
    ]
    groups = __import__("scripts.triage", fromlist=["find_overlaps"]).find_overlaps(ideas)
    assert len(groups) == 1
    assert {i["id"] for i in groups[0]} == {"idea-a", "idea-b"}  # c not pulled in


def test_find_overlaps_respects_threshold():
    from scripts.triage import find_overlaps
    ideas = [
        _idea("idea-a", "alpha beta gamma delta epsilon zeta theta"),
        _idea("idea-b", "alpha beta gamma kappa lambda omikron sigma"),
    ]
    assert find_overlaps(ideas, threshold=0.99) == []          # too strict → no pair
    assert len(find_overlaps(ideas, threshold=0.2)) == 1       # loose → paired


def test_find_overlaps_ignores_non_open():
    from scripts.triage import find_overlaps
    ideas = [
        _idea("idea-a", "shared topic words here clearly", status="open"),
        _idea("idea-b", "shared topic words here clearly", status="resolved"),
    ]
    assert find_overlaps(ideas) == []  # only one open → no group


def test_grouping_exposes_overlaps_and_count():
    ideas = [
        _idea("idea-a", "shared overlapping topic words alpha beta", slug="cns-core"),
        _idea("idea-b", "shared overlapping topic words alpha gamma", slug="interface"),
    ]
    g = group_ideas(ideas, now=NOW)
    assert g["counts"]["overlaps"] == 1
    assert len(g["overlaps"]) == 1


def test_render_is_stable_markdown():
    ideas = [_idea("idea-1", "A concrete and clearly described deliverable here.", slug="cns-core")]
    out = render_triage(group_ideas(ideas, now=NOW))
    assert "# Triage —" in out
    assert "## Mature (promotion candidates)" in out
    assert "idea-1" in out
