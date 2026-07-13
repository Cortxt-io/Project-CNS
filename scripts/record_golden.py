"""Spela in de fyra levande endpoints till tests/golden/.

Kontraktet mot app.cortxt.io. Kör före och efter en rivning — `pytest tests/test_api_contract.py`
säger då om appen fortfarande får det den läser.

    python scripts/record_golden.py [--base URL]

Default är drift (Railway). Peka om med --base för att spela in mot en lokal server.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

DEFAULT_BASE = "https://project-cns-production.up.railway.app"
GOLDEN = Path(__file__).resolve().parent.parent / "tests" / "golden"

# namn → path. Slugen är orgkomp: den enda vertikal som har både roadmap och nodgraf.
ENDPOINTS = {
    "command-center": "/api/command-center",
    "vertical-orgkomp": "/api/vertical/orgkomp",
    "nodes-orgkomp": "/api/nodes?domain=orgkomp",
    "cookbook-orgkomp": "/api/cookbook/orgkomp",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    args = ap.parse_args()

    GOLDEN.mkdir(parents=True, exist_ok=True)
    failed = False

    for name, path in ENDPOINTS.items():
        url = f"{args.base}{path}"
        try:
            with urllib.request.urlopen(url, timeout=45) as r:
                payload = json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 — vi vill se vilken som föll, inte krascha
            print(f"{name:20} FEL: {exc}", file=sys.stderr)
            failed = True
            continue

        out = GOLDEN / f"{name}.json"
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{name:20} ok  ({len(json.dumps(payload))} tecken)")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
