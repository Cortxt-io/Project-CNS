"""Capture `/btw` asides from a Claude Code transcript into the btw session log.

Designed to run from a Claude Code **Stop hook**, which feeds the hook JSON on
stdin (``session_id`` + ``transcript_path``). On every stop this reconciles the
session's log against every `/btw` command in the transcript and appends only
the ones not already logged (dedup on the command's uuid). Most stops add
nothing and do nothing.

It is deliberately crash-proof: any error is swallowed and the process exits 0,
so a hook failure can never break the user's session. Pushing to GitHub is
best-effort — if ``CNS_GITHUB_TOKEN``/``GITHUB_REPO`` aren't set (typical for a
local session), the log is still written to disk and the push is skipped.

Standalone, not wired into ``cns.py`` (the subcommand wiring waits). Run it
manually for testing:

    python -m scripts.btw_capture --session <id> --transcript <path>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Run as a hook command (`python .../scripts/btw_capture.py`) from any cwd:
# put the repo root on sys.path so `from scripts ...` / `from app ...` resolve.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# /btw command invocation: a local_command carrying <command-name>/btw</...>
_BTW_NAME_RE = re.compile(r"<command-name>\s*/?btw\s*</command-name>", re.IGNORECASE)
_ARGS_RE = re.compile(r"<command-args>(.*?)</command-args>", re.DOTALL)
# Fork banner emitted right after the command, e.g.
# <local-command-stdout>⑂ forked jag-vill-egentligen (b5f4)</local-command-stdout>
_FORK_RE = re.compile(r"forked\s+(.*?)\s*</local-command-stdout>", re.DOTALL)


def _load_lines(transcript_path: str) -> list[dict]:
    """Parse a .jsonl transcript into objects, skipping unparseable lines."""
    objs: list[dict] = []
    path = Path(transcript_path)
    if not path.exists():
        return objs
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            objs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return objs


def _is_btw_command(obj: dict) -> bool:
    return (
        obj.get("type") == "system"
        and obj.get("subtype") == "local_command"
        and isinstance(obj.get("content"), str)
        and bool(_BTW_NAME_RE.search(obj["content"]))
    )


def _fork_name(obj: dict) -> str | None:
    """Pull the fork name from a local-command-stdout entry, if present."""
    content = obj.get("content")
    if not isinstance(content, str):
        return None
    m = _FORK_RE.search(content)
    return m.group(1).strip() if m else None


def find_asides(objs: list[dict]) -> list[dict]:
    """Extract every `/btw` aside from a parsed transcript, in order.

    Returns dicts of {uuid, text, fork, ts}. The fork name is read from a
    local_command stdout entry whose parentUuid is the command (best-effort).
    """
    # Index children by parentUuid so we can find each command's fork banner.
    children: dict[str, list[dict]] = {}
    for obj in objs:
        parent = obj.get("parentUuid")
        if parent:
            children.setdefault(parent, []).append(obj)

    asides: list[dict] = []
    for obj in objs:
        if not _is_btw_command(obj):
            continue
        args = _ARGS_RE.search(obj["content"])
        text = args.group(1).strip() if args else ""
        uuid = obj.get("uuid", "")
        if not uuid or not text:
            # Skip an argument-less /btw (just prints usage) — nothing to keep.
            continue
        fork = None
        for child in children.get(uuid, []):
            fork = _fork_name(child)
            if fork:
                break
        asides.append(
            {
                "uuid": uuid,
                "text": text,
                "fork": fork,
                "ts": obj.get("timestamp"),
            }
        )
    return asides


def capture(session_id: str, transcript_path: str) -> dict:
    """Reconcile a session's btw log with the transcript. Returns a summary."""
    from scripts import btw_log

    objs = _load_lines(transcript_path)
    asides = find_asides(objs)

    added = []
    for a in asides:
        _, was_added = btw_log.add_aside(
            session_id,
            text=a["text"],
            src_uuid=a["uuid"],
            fork=a["fork"],
            ts=a["ts"],
        )
        if was_added:
            added.append(a)

    pushed = None
    if added:
        pushed = _push(session_id)

    return {"found": len(asides), "added": len(added), "pushed": pushed}


def _push(session_id: str) -> str:
    """Best-effort GitHub push of the session log; degrades to local-only."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass
    try:
        from app.git_ops import push_file_immediately
        from scripts import btw_log

        path = btw_log._session_path(session_id)
        ok, msg = push_file_immediately(path, f"cns-vault: btw log {session_id}")
        return msg if ok else f"local-only ({msg})"
    except Exception as exc:  # never let a push failure surface to the hook
        return f"local-only ({exc})"


def _read_hook_stdin() -> dict:
    """Parse the hook JSON on stdin, if any. Empty dict when absent."""
    if sys.stdin is None or sys.stdin.isatty():
        return {}
    # Read raw bytes and decode utf-8-sig: locale-independent and BOM-stripping
    # (Windows text stdin uses the system code page, which mangles UTF-8 input).
    try:
        buffer = getattr(sys.stdin, "buffer", None)
        data = buffer.read() if buffer is not None else sys.stdin.read()
    except Exception:
        return {}
    if isinstance(data, bytes):
        data = data.decode("utf-8-sig", errors="replace")
    raw = data.strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture /btw asides into the btw log.")
    parser.add_argument("--session", help="Session id (overrides hook stdin).")
    parser.add_argument("--transcript", help="Transcript .jsonl path (overrides hook stdin).")
    args = parser.parse_args()

    hook = _read_hook_stdin()
    session_id = args.session or hook.get("session_id")
    transcript_path = args.transcript or hook.get("transcript_path")

    if not session_id or not transcript_path:
        # Nothing to do (e.g. invoked with no hook payload). Stay silent.
        return 0

    try:
        result = capture(session_id, transcript_path)
        if result["added"]:
            print(
                f"btw: +{result['added']} aside(s) for {session_id} "
                f"(push: {result['pushed']})"
            )
    except Exception as exc:  # crash-proof: a hook must never break the session
        print(f"btw_capture: skipped ({exc})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
