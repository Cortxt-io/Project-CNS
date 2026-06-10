"""Kvalitetsgrind för EN agentfil — körs av /bemanna före aktivering.

Kollar att en agent är färdigskriven (inte ett skal): komplett frontmatter,
obligatoriska body-sektioner, inga skelettmarkörer, least-privilege-sanity.
ERROR/WARN; exit≠0 vid ERROR. Grunden: agent-design-playbook + onboarding-research.

Kör: python scripts/validate_agent.py <slug>
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / ".claude" / "agents"
ROSTER_DIR = ROOT / ".claude" / "org" / "roster"

REQUIRED_FM = ["name", "title", "department", "sub_department", "model", "status", "description"]
MODELS = {"claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"}
SKELETON_MARKERS = ["(TODO", "TODO vid", "Skal —", "Skal-roll", "<vad rollen", "<MCP-verktyg", "<hur vet"]
EXEC_DEPTS = {"Ledning"}


def find_file(slug: str) -> Path | None:
    for d in (AGENTS_DIR, ROSTER_DIR):
        p = d / f"{slug}.md"
        if p.exists():
            return p
    return None


def parse_fm(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def section(text: str, *titles: str) -> str:
    """Returnera body-texten under en rubrik (## eller ###) med någon av titlarna, till nästa rubrik."""
    for title in titles:
        m = re.search(rf"^#{{1,3}}\s*.*{re.escape(title)}.*$", text, flags=re.MULTILINE | re.IGNORECASE)
        if m:
            start = m.end()
            nxt = re.search(r"^#{1,3}\s", text[start:], flags=re.MULTILINE)
            return text[start: start + (nxt.start() if nxt else len(text))]
    return ""


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Användning: python scripts/validate_agent.py <slug>")
        return 2
    slug = argv[0]
    path = find_file(slug)
    if not path:
        print(f"ERROR: hittar ingen agentfil '{slug}' i .claude/agents/ eller .claude/org/roster/")
        return 1

    text = path.read_text(encoding="utf-8")
    fm = parse_fm(text)
    body = text[text.find("\n---", 3) + 4:] if text.startswith("---") else text
    errors, warns = [], []

    # 1. frontmatter komplett
    for key in REQUIRED_FM:
        if not fm.get(key):
            errors.append(f"frontmatter saknar '{key}'")
    if fm.get("model") and fm["model"] not in MODELS:
        errors.append(f"ogiltig model '{fm.get('model')}'")

    # 2. inga skelettmarkörer
    for marker in SKELETON_MARKERS:
        if marker in text:
            errors.append(f"skelettmarkör kvar: '{marker}' — kroppen är inte ifylld")
            break

    # 3. obligatoriska sektioner
    tools = section(body, "Tillåtna verktyg", "Verktyg")
    evals = section(body, "Eval-kriterier", "Eval")
    proto = section(body, "Session-protokoll")
    if not section(body, "Roll", "uppgift", "Din uppgift") and len(body.strip()) < 200:
        errors.append("ingen roll-/uppgiftsbeskrivning (tunn body)")
    if not tools.strip():
        errors.append("saknar sektion 'Tillåtna verktyg'")
    if not evals.strip():
        errors.append("saknar sektion 'Eval-kriterier'")
    if not proto.strip():
        warns.append("saknar 'Session-protokoll' (start/done-bokföring)")

    # 4. innehållssanity
    tool_lines = [l for l in tools.splitlines() if l.strip().startswith(("-", "*"))]
    eval_lines = [l for l in evals.splitlines() if l.strip().startswith(("-", "*"))]
    if tools.strip() and not tool_lines:
        warns.append("'Tillåtna verktyg' har ingen punktlista")
    if 0 < len(eval_lines) < 2:
        warns.append("'Eval-kriterier' har <2 punkter — för tunt")

    # 5. least-privilege + kostnad
    if len(tool_lines) > 12:
        warns.append(f"{len(tool_lines)} verktyg — bred yta, kolla least-privilege")
    if fm.get("model") == "claude-opus-4-8" and fm.get("department") not in EXEC_DEPTS \
            and fm.get("lead") != "true":
        warns.append("Opus på icke-exec/icke-lead roll — dyrt, motivera eller sänk tier")

    print(f"=== AGENT-GRIND: {slug} ({path.parent.name}) ===")
    for e in errors:
        print(f"ERROR: {e}")
    for w in warns:
        print(f"WARN:  {w}")
    if not errors and not warns:
        print("OK — agenten är färdig och inom riktlinjerna.")
    print(f"--- {len(errors)} error, {len(warns)} warn ---")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
