"""Idea triage — group the open inbox so it can be acted on, not just listed.

The triage tool (#39) has three planned forms: (a) a ``/triage`` skill flow,
(b) an MCP batch tool, (c) a TUI view. This module is the **shared grouping
logic** all three reuse — transport-free and testable, mirroring the
``scripts/tools/<domain>_core`` split. Forms (b)/(c) import ``group_ideas``;
form (a) drives the ``cns triage`` CLI below.

A growing inbox is noise unless it is sorted into what to *act on* now:
  - clusters  — several open ideas sharing a node slug → decide them together.
  - mature    — has a slug and a concrete body → promotion candidates.
  - stale     — untriaged (no slug) and old → resolve/wontfix candidates.
  - untriaged — no slug yet → need a home before they can mature.

Rules are deliberately simple and deterministic (same philosophy as
``recommend.py``): the agent/skill does the judgement, this does the sorting.
"""

from __future__ import annotations

import re
from datetime import datetime

# An idea is "stale" once it has sat untriaged (no slug) this long.
STALE_DAYS = 14
# Bodies shorter than this read as one-liners — too thin to promote as-is.
MATURE_MIN_LEN = 40
# Phrase that marks a direction question (a decision, not a deliverable).
DIRECTION_MARKER = "riktningsfråga"

# Token-set (Jaccard) similarity at/above this flags two ideas as likely overlapping
# (#146 triage variant). Heuristic + conservative — surfaces merge CANDIDATES for the
# agent/skill to judge, never auto-merges. Calibrated against real body-length ideas:
# distinct ideas rarely share >0.30 of their topic tokens, so this catches genuine
# topic overlap (incl. across different slugs, which slug clustering misses) without
# drowning triage in weak pairs. Tunable per call via find_overlaps(threshold=…).
OVERLAP_THRESHOLD = 0.30
# Short/common tokens carry no topic signal; drop them before comparing.
_STOPWORDS = frozenset(
    "som ett att och det den för med inte att vad vid via per den ena via "
    "the and for that this with not via per each into over from idea idé "
    "ska kan vill bygg bygga göra gör finns redan över".split()
)
_TOKEN_RE = re.compile(r"[a-zA-Z0-9åäöÅÄÖ]{4,}")


def _age_days(created_at: str, now: datetime) -> float | None:
    """Age of an idea in days from its ISO ``created_at`` (None if unparseable)."""
    try:
        return (now - datetime.fromisoformat(created_at)).total_seconds() / 86400.0
    except (ValueError, TypeError):
        return None


def _is_mature(idea: dict) -> bool:
    """A promotion candidate: has a node home and a concrete (non-vague) body."""
    if not idea.get("slug"):
        return False
    text = (idea.get("text") or "").strip()
    if len(text) < MATURE_MIN_LEN:
        return False
    return DIRECTION_MARKER not in text.lower()


def _tokens(text: str) -> set[str]:
    """Topic tokens of an idea body: 4+ char words, lowercased, stopwords dropped."""
    return {t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOPWORDS}


def _similarity(a: set[str], b: set[str]) -> float:
    """Jaccard similarity of two token sets (0..1; 0 if either is empty)."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_overlaps(ideas: list[dict], threshold: float = OVERLAP_THRESHOLD) -> list[list[dict]]:
    """Group OPEN ideas that likely overlap by text similarity (#146 triage variant).

    Catches duplicates that share a topic but not a slug — what slug clustering in
    ``group_ideas`` misses. Pairwise Jaccard above ``threshold`` links two ideas;
    links are merged transitively (union-find) into candidate groups. Returns groups
    of 2+ ideas (newest-first within a group), heaviest-overlap groups first. These
    are merge CANDIDATES for the agent to judge — never an auto-merge.
    """
    open_ideas = [i for i in ideas if i.get("status", "open") == "open"]
    toks = [_tokens(i.get("text", "")) for i in open_ideas]

    parent = list(range(len(open_ideas)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(open_ideas)):
        for j in range(i + 1, len(open_ideas)):
            if _similarity(toks[i], toks[j]) >= threshold:
                parent[find(i)] = find(j)

    groups: dict[int, list[dict]] = {}
    for idx, idea in enumerate(open_ideas):
        groups.setdefault(find(idx), []).append(idea)
    result = [g for g in groups.values() if len(g) >= 2]
    for g in result:
        g.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    result.sort(key=len, reverse=True)
    return result


def group_ideas(
    ideas: list[dict],
    now: datetime | None = None,
    stale_days: int = STALE_DAYS,
) -> dict:
    """Sort open ideas into actionable buckets.

    Args:
        ideas: idea dicts as stored by ``idea_inbox`` (id/text/slug/created_at/status).
            Non-open ideas are ignored so callers can pass a raw list.
        now: reference time for staleness (injected for tests). Defaults to ``datetime.now()``.
        stale_days: untriaged-age threshold for the stale bucket.

    Returns a dict with ``clusters`` (slug → ideas, 2+ sharing a slug),
    ``mature``, ``stale``, ``untriaged`` lists, and a ``counts`` summary.
    Each list is newest-first; an idea may appear in several buckets
    (e.g. mature ideas also appear in their slug cluster).
    """
    now = now or datetime.now()
    open_ideas = [i for i in ideas if i.get("status", "open") == "open"]
    open_ideas.sort(key=lambda i: i.get("created_at", ""), reverse=True)

    untriaged = [i for i in open_ideas if not i.get("slug")]
    mature = [i for i in open_ideas if _is_mature(i)]
    stale = [
        i
        for i in untriaged
        if (age := _age_days(i.get("created_at", ""), now)) is not None
        and age >= stale_days
    ]

    by_slug: dict[str, list[dict]] = {}
    for idea in open_ideas:
        slug = idea.get("slug")
        if slug:
            by_slug.setdefault(slug, []).append(idea)
    clusters = [
        {"slug": slug, "ideas": members}
        for slug, members in sorted(by_slug.items())
        if len(members) >= 2
    ]

    overlaps = find_overlaps(open_ideas)

    return {
        "clusters": clusters,
        "mature": mature,
        "stale": stale,
        "untriaged": untriaged,
        "overlaps": overlaps,
        "counts": {
            "open": len(open_ideas),
            "clusters": len(clusters),
            "mature": len(mature),
            "stale": len(stale),
            "untriaged": len(untriaged),
            "overlaps": len(overlaps),
        },
    }


def _one_line(idea: dict, width: int = 72) -> str:
    """A single inbox line: id + collapsed, truncated text."""
    text = " ".join((idea.get("text") or "").split())
    if len(text) > width:
        text = text[: width - 1] + "…"
    return f"  {idea['id']}  {text}"


def render_triage(grouping: dict) -> str:
    """Markdown rendering of a grouping for the ``/triage`` skill / CLI."""
    c = grouping["counts"]
    lines = [
        f"# Triage — {c['open']} open ideas "
        f"({c['untriaged']} untriaged · {c['mature']} mature · "
        f"{c['stale']} stale · {c['clusters']} clusters · "
        f"{c.get('overlaps', 0)} overlap groups)",
        "",
    ]

    lines.append("## Likely overlaps (review for merge — #146)")
    if not grouping.get("overlaps"):
        lines.append("  (none)")
    for group in grouping.get("overlaps", []):
        lines.append(f"  ~ {len(group)} ideas:")
        lines += [_one_line(i, width=66).replace("  ", "    ", 1) for i in group]
    lines.append("")

    lines.append("## Mature (promotion candidates)")
    lines += [_one_line(i) for i in grouping["mature"]] or ["  (none)"]
    lines.append("")

    lines.append("## Stale (resolve/wontfix candidates)")
    lines += [_one_line(i) for i in grouping["stale"]] or ["  (none)"]
    lines.append("")

    lines.append("## Clusters (decide together, by node)")
    if not grouping["clusters"]:
        lines.append("  (none)")
    for cluster in grouping["clusters"]:
        lines.append(f"  [{cluster['slug']}]")
        lines += [_one_line(i, width=66).replace("  ", "    ", 1) for i in cluster["ideas"]]
    lines.append("")

    lines.append("## Untriaged (need a node)")
    lines += [_one_line(i) for i in grouping["untriaged"]] or ["  (none)"]
    return "\n".join(lines)
