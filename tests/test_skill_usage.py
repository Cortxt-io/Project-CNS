"""Skill-mätaren: vilka skills avfyras faktiskt?

Bakgrunden (2026-07-13): Rikard misstänkte att han byggde skills men inte använde dem. Ingen kunde
svara, för ingen mätte. Transkripten svarade: **40 skill-anrop i 28 sessioner, varav exakt ETT** var
en egen skill (`run-gate`). Åtta av tolv egna skills saknade trigger helt och kunde aldrig aktiveras.

Den skillnad som gör mätaren värd något: skill-LISTAN injiceras i varje prompt (varje skillnamn
förekommer hundratals gånger i transkripten). Ett skill-ANROP är ett `tool_use` med `name: "Skill"`.
Räknar man omnämnanden får man en mätare som säger att allt används — vilket är exakt den lögn vi
byggde den för att avslöja.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab.scripts import skill_usage as su  # noqa: E402


def _line(**content) -> str:
    return json.dumps(content, ensure_ascii=False)


def _transcript(tmp_path: Path, *lines: str) -> Path:
    d = tmp_path / "proj"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "session.jsonl"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


def _call(skill: str, ts: str = "2026-07-13T10:00:00Z") -> str:
    return _line(timestamp=ts, message={"content": [
        {"type": "tool_use", "name": "Skill", "input": {"skill": skill}}
    ]})


def test_counts_actual_invocations(tmp_path: Path) -> None:
    root = _transcript(tmp_path, _call("run-gate"), _call("run-gate"), _call("triage"))
    counts = {u.skill: u.count for u in su.collect(root)}
    assert counts == {"run-gate": 2, "triage": 1}


def test_a_mention_is_not_an_invocation(tmp_path: Path) -> None:
    """Skill-listan injiceras i VARJE prompt. Räknar vi omnämnanden ser allt använt ut."""
    root = _transcript(
        tmp_path,
        _line(message={"content": [{"type": "text", "text": "tillgängliga skills: run-gate, triage, capture"}]}),
        _line(message={"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "triage.md"}}]}),
        _call("run-gate"),
    )
    counts = {u.skill: u.count for u in su.collect(root)}
    assert counts == {"run-gate": 1}, "bara riktiga Skill-anrop får räknas"


def test_last_used_is_the_latest_timestamp(tmp_path: Path) -> None:
    root = _transcript(
        tmp_path,
        _call("run-gate", "2026-07-01T09:00:00Z"),
        _call("run-gate", "2026-07-13T18:30:00Z"),
    )
    assert su.collect(root)[0].last_used.startswith("2026-07-13")


def test_never_fired_skills_are_the_point(tmp_path: Path) -> None:
    """En skill som aldrig avfyrats är inte en skill. Den är en fil. Rapporten måste säga det."""
    root = _transcript(tmp_path, _call("run-gate"))
    report = su.report(root, known={"run-gate", "triage", "capture", "pr-protokoll"})
    assert [u.skill for u in report.used] == ["run-gate"]
    assert set(report.never_used) == {"capture", "pr-protokoll", "triage"}


def test_own_skills_are_separated_from_vendor_skills(tmp_path: Path) -> None:
    """superpowers:* och deep-research är Anthropics. Blandas de in ser lådan full ut."""
    root = _transcript(tmp_path, _call("superpowers:brainstorming"), _call("run-gate"))
    report = su.report(root, known={"run-gate"})
    assert [u.skill for u in report.used] == ["run-gate"]
    assert [u.skill for u in report.foreign] == ["superpowers:brainstorming"]


def test_missing_transcript_dir_degrades_to_empty(tmp_path: Path) -> None:
    assert su.collect(tmp_path / "finns-inte") == []
