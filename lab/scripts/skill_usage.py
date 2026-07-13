"""Skill-mätaren — avfyras skillsen faktiskt?

**Varför:** Rikard misstänkte 2026-07-13 att han byggde skills men inte använde dem. Ingen kunde
svara, för ingen mätte — och i frånvaron av data fyllde oron tomrummet. Transkripten svarade:
**40 skill-anrop i 28 sessioner, varav exakt ETT** var en egen skill (`run-gate`). Åtta av tolv egna
skills saknade trigger helt (`description` sa *vad*, aldrig *när*) och kunde därför aldrig aktiveras.
Verktygslådan såg full ut och fungerade som tom.

**Den skillnad som gör mätaren värd något:** skill-LISTAN injiceras i varje prompt, så varje
skillnamn förekommer hundratals gånger i transkripten. Ett skill-ANROP är ett `tool_use` med
`name: "Skill"`. Räknar man omnämnanden får man en mätare som säger att allt används — vilket är
precis den lögn den byggdes för att avslöja.

Deterministiskt, verifierbart, upprepat → **kod, inte skill** (Routningsprincipen).

Kör:
    python lab/cns_lab.py skill-usage
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

# Anthropics egna skills. De blandas inte in: gör man det ser lådan full ut, och det var just den
# synvillan som gjorde att ingen upptäckte att de EGNA skillsen aldrig avfyrades.
FOREIGN_PREFIXES = ("superpowers:", "plugin-", "vercel:", "nimble:", "shopify-", "exa:",
                    "code-modernization:", "frontend-design:", "skill-creator:", "pr-review-toolkit:",
                    "commit-commands:", "feature-dev:", "plugin-dev:", "supabase:", "railway:",
                    "mcp-server-dev:", "dak:", "datarobot-agent-skills:", "session-report:")
FOREIGN_EXACT = {"deep-research", "artifact-design", "dataviz", "verify", "code-review", "simplify",
                 "loop", "schedule", "run", "init", "review", "security-review", "remember:remember",
                 "update-config", "keybindings-help", "claude-api", "fewer-permission-prompts"}

# Allt med ett kolon är namespacat av ett plugin/marketplace — våra egna skills är bara sluggar
# (`run-gate`, `pr-protokoll`). Att missa den regeln fick `exa:search` att räknas som vår och lådan
# att se använd ut: 70 anrop av något vi inte skrivit.
def _is_namespaced(skill: str) -> bool:
    return ":" in skill


def default_transcript_root() -> Path:
    return Path(os.path.expanduser("~")) / ".claude" / "projects"


@dataclass
class Usage:
    skill: str
    count: int = 0
    last_used: str = ""


@dataclass
class Report:
    used: list[Usage] = field(default_factory=list)       # egna, avfyrade
    never_used: list[str] = field(default_factory=list)   # egna, aldrig avfyrade
    foreign: list[Usage] = field(default_factory=list)    # Anthropics


def is_foreign(skill: str) -> bool:
    return (_is_namespaced(skill) or skill in FOREIGN_EXACT
            or any(skill.startswith(p) for p in FOREIGN_PREFIXES))


def _invocations(path: Path):
    """Varje faktiskt Skill-anrop i ett transkript → (skill, timestamp)."""
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or '"Skill"' not in line:   # billig förfilter; 143 MB transkript
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if (isinstance(block, dict) and block.get("type") == "tool_use"
                        and block.get("name") == "Skill"):
                    skill = (block.get("input") or {}).get("skill")
                    if skill:
                        yield str(skill), str(rec.get("timestamp") or "")


def collect(root: Path | str | None = None) -> list[Usage]:
    """Alla skill-anrop, sorterade på antal. Saknad katalog → [] (frånvaro, inte fel)."""
    root = Path(root or default_transcript_root())
    if not root.is_dir():
        return []

    seen: dict[str, Usage] = {}
    for f in sorted(root.rglob("*.jsonl")):
        for skill, ts in _invocations(f):
            u = seen.setdefault(skill, Usage(skill))
            u.count += 1
            if ts > u.last_used:
                u.last_used = ts
    return sorted(seen.values(), key=lambda u: (-u.count, u.skill))


def report(root: Path | str | None = None, *, known: set[str] | None = None) -> Report:
    """Egna avfyrade · egna ALDRIG avfyrade · Anthropics.

    `never_used` är hela poängen. En skill som aldrig avfyrats är inte en skill — den är en fil.
    """
    all_usage = collect(root)
    known = known or set()

    rep = Report()
    for u in all_usage:
        (rep.foreign if is_foreign(u.skill) else rep.used).append(u)

    fired = {u.skill for u in rep.used}
    rep.never_used = sorted(known - fired)
    return rep


def known_skills(skills_dir: Path | None = None) -> set[str]:
    """Våra skills — BÅDA destinationerna.

    Exporten skriver till två ställen: repo-skills till `lab/.claude/skills/` och vault-skills
    (grindarna, som arbetar på vault-noter) till vaultens egen `.claude/skills/`. Räknar man bara
    den ena döljer mätaren halva sanningen — och en mätare som visar halva sanningen är sämre än
    ingen, för den blir trodd.
    """
    if skills_dir is not None:
        dirs = [Path(skills_dir)]
    else:
        from scripts.vault_reader import vault_root

        dirs = [Path(__file__).resolve().parent.parent / ".claude" / "skills"]
        vault = vault_root()
        if vault:
            dirs.append(vault / ".claude" / "skills")

    return {
        p.name
        for d in dirs if d.is_dir()
        for p in d.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--transcripts", type=Path, default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    rep = report(args.transcripts, known=known_skills())

    if args.json:
        print(json.dumps({
            "used": [vars(u) for u in rep.used],
            "never_used": rep.never_used,
            "foreign": [vars(u) for u in rep.foreign],
        }, ensure_ascii=False, indent=2))
        return 0

    print("\nVÅRA SKILLS — avfyrade")
    if rep.used:
        for u in rep.used:
            print(f"  {u.count:4d}x  {u.skill:24s} senast {u.last_used[:10] or '?'}")
    else:
        print("  (ingen. Verktygslådan ser full ut och fungerar som tom.)")

    print("\nVÅRA SKILLS — ALDRIG avfyrade")
    if rep.never_used:
        for s in rep.never_used:
            print(f"        {s}")
        print("\n  En skill som aldrig avfyrats är inte en skill — den är en fil.")
        print("  Vanligaste orsaken: descriptionen säger VAD den gör, aldrig NÄR. Descriptionen ÄR triggern.")
    else:
        print("  (inga — allt vi byggt används)")

    if rep.foreign:
        top = ", ".join(f"{u.skill.split(':')[-1]} ({u.count})" for u in rep.foreign[:4])
        print(f"\nAnthropics skills, till jämförelse: {sum(u.count for u in rep.foreign)} anrop — {top}")
    print()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
