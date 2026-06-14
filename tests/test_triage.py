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


def test_render_is_stable_markdown():
    ideas = [_idea("idea-1", "A concrete and clearly described deliverable here.", slug="cns-core")]
    out = render_triage(group_ideas(ideas, now=NOW))
    assert "# Triage —" in out
    assert "## Mature (promotion candidates)" in out
    assert "idea-1" in out
