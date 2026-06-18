"""Pytest path bootstrap.

The ``scripts`` package is a PEP 420 namespace package split across two roots:

* ``scripts/`` (repo root) — CNS Core modules (catalog, md_parser, validator,
  derive_catalog). Importable on their own; never import from Lab.
* ``lab/scripts/`` — Lab/Agency modules (dispatch, mcp_router, session_store,
  tui, …). May import ``scripts.*`` Core modules (Lab→Core is allowed).

Putting both the repo root and ``lab/`` on ``sys.path`` merges the two into a
single ``scripts`` namespace, so tests can import either layer. Core-only test
runs never need ``lab/`` on the path — that separation is the whole point.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "lab"

for p in (ROOT, LAB):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)
