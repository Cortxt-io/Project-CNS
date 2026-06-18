"""UserPromptSubmit hook — injicerar öppna idéer från det aktuella arbetspasset.

Läser stdin-JSON från Claude Code och skriver öppna idéer (session_id-filtrerade)
till stdout som kontext-injektion. Tyst om inga idéer finns eller om session_id
saknas. Crash-proof: exit 0 alltid.

Registrering (arbetsytans .claude/settings.json):
  "UserPromptSubmit": [{"hooks": [{"type": "command",
    "command": "python .../idea_prompt_hook.py", "async": false}]}]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Repots rot — navigera upp från scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return

        payload = json.loads(raw)
        session_id = payload.get("session_id") or payload.get("sessionId")
        if not session_id:
            return

        from scripts.idea_inbox import list_ideas

        ideas = list_ideas(status="open", session_id=session_id)
        if not ideas:
            return

        lines = ["Öppna idéer från det här passet:"]
        for idea in ideas:
            lines.append(f"- {idea['text']} (id: {idea['id']})")

        print("\n".join(lines))

    except Exception:
        # Crash-proof: hooken ska aldrig blockera en prompt
        pass


if __name__ == "__main__":
    main()
