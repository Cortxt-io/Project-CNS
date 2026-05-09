"""Compare two text snapshots and classify whether the change is meaningful.

Heuristics for noise reduction (MVP level):
1. Strip common timestamp/date patterns before comparing.
2. Ignore whitespace-only differences.
3. Require a minimum changed-character threshold.
4. Flag cookie-consent / tracking boilerplate phrases.

These are intentionally simple. Better NLP-based filtering is a later slice.
"""

import difflib
import re
from dataclasses import dataclass

# Patterns commonly found in dynamic page noise
TIMESTAMP_RE = re.compile(
    r"""
    \b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\b   # dates like 01/05/2026
    | \b\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}\b     # ISO-ish dates
    | \b\d{1,2}:\d{2}(:\d{2})?\b              # times like 14:30
    | \b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s*\d{2,4}\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

COOKIE_PHRASES = [
    "we use cookies",
    "cookie policy",
    "accept cookies",
    "cookie consent",
    "gdpr",
    "privacy preferences",
]


@dataclass
class DiffResult:
    url: str
    label: str
    has_change: bool
    is_meaningful: bool
    reason: str  # human-readable explanation
    added_lines: list[str]
    removed_lines: list[str]
    diff_text: str  # unified diff for display


def _strip_timestamps(text: str) -> str:
    return TIMESTAMP_RE.sub("__TS__", text)


def _is_cookie_noise(lines: list[str]) -> bool:
    joined = " ".join(lines).lower()
    return any(phrase in joined for phrase in COOKIE_PHRASES)


def compute_diff(
    url: str,
    label: str,
    old_text: str | None,
    new_text: str,
    filters: dict,
) -> DiffResult:
    """Compare old and new text, return a classified DiffResult."""

    if old_text is None:
        return DiffResult(
            url=url, label=label,
            has_change=False, is_meaningful=False,
            reason="First snapshot, nothing to compare.",
            added_lines=[], removed_lines=[], diff_text="",
        )

    old = old_text
    new = new_text

    # Optional: normalise timestamps before diffing
    if filters.get("ignore_timestamp_patterns", True):
        old = _strip_timestamps(old)
        new = _strip_timestamps(new)

    old_lines = old.splitlines()
    new_lines = new.splitlines()

    # Quick exit: nothing changed
    if old_lines == new_lines:
        return DiffResult(
            url=url, label=label,
            has_change=False, is_meaningful=False,
            reason="No change detected.",
            added_lines=[], removed_lines=[], diff_text="",
        )

    # Build unified diff
    diff = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile="previous", tofile="current", lineterm="",
    ))
    diff_text = "\n".join(diff)

    added = [l[1:] for l in diff if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:] for l in diff if l.startswith("-") and not l.startswith("---")]

    # --- Noise heuristics ---
    total_changed_chars = sum(len(l) for l in added + removed)

    # Whitespace-only?
    if filters.get("ignore_whitespace_only", True):
        stripped_added = [l.strip() for l in added if l.strip()]
        stripped_removed = [l.strip() for l in removed if l.strip()]
        if not stripped_added and not stripped_removed:
            return DiffResult(
                url=url, label=label,
                has_change=True, is_meaningful=False,
                reason="Whitespace-only change, likely noise.",
                added_lines=added, removed_lines=removed, diff_text=diff_text,
            )

    # Below minimum threshold?
    min_chars = filters.get("min_change_chars", 10)
    if total_changed_chars < min_chars:
        return DiffResult(
            url=url, label=label,
            has_change=True, is_meaningful=False,
            reason=f"Very small change ({total_changed_chars} chars), likely noise.",
            added_lines=added, removed_lines=removed, diff_text=diff_text,
        )

    # Cookie/tracking boilerplate?
    if _is_cookie_noise(added + removed):
        return DiffResult(
            url=url, label=label,
            has_change=True, is_meaningful=False,
            reason="Change appears to be cookie/tracking boilerplate.",
            added_lines=added, removed_lines=removed, diff_text=diff_text,
        )

    # Passed all filters -> meaningful
    return DiffResult(
        url=url, label=label,
        has_change=True, is_meaningful=True,
        reason=f"Content changed ({total_changed_chars} chars, {len(added)} added / {len(removed)} removed lines).",
        added_lines=added, removed_lines=removed, diff_text=diff_text,
    )
