#!/usr/bin/env python3
"""CNS Lab/Agency entrypoint — the full, advanced command surface.

CNS Core (`python cns.py`) deliberately exposes only validate / new / export.
Everything else — sessions, quests, ventures/roadmaps, GitHub/PR clients,
health, triage, dashboard exports — is R&D and lives here.

The agency layer (TUI, dispatch loop, agent-host, agent routing, MCP
introspection) was FROZEN on 2026-07-12 and moved to `lab/frozen/`. Those
subcommands still parse, but reject with exit 2 and a pointer to
`lab/frozen/FROZEN.md`. Do not wire new work to them.

This entrypoint reuses the command functions defined in `cns.py`; it only adds
the extra parser registrations. Run it from the repo root:

    python lab/cns_lab.py -h
    python lab/cns_lab.py venture list
    python lab/cns_lab.py selftest

Putting both the repo root and `lab/` on sys.path merges the `scripts` namespace
package (Core modules in scripts/, Lab modules in lab/scripts/) so the agency
commands can import their dependencies.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "lab"
for _p in (str(ROOT), str(LAB)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Lab help strings contain unicode (→, em-dash); guard against cp1252 consoles
# on Windows the same way cns.py wraps its Rich console.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import cns  # noqa: E402  (path bootstrap must run first)


def main() -> None:
    cns._load_env()
    parser = argparse.ArgumentParser(
        prog="cns-lab",
        description="CNS Lab/Agency — advanced/R&D commands (Core + everything else)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Lab commands")
    cns.register_core(subparsers)
    cns.register_lab(subparsers)

    args = parser.parse_args()
    if not args.command or not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
