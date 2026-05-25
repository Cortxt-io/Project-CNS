from pathlib import Path
import stat

HOOK_CONTENT = """#!/bin/sh
# CNS post-commit hook – trigger analyze for changed projects
cd "$(git rev-parse --show-toplevel)"
python cns.py post-commit-analyze
"""


def install_post_commit_hook() -> None:
    hook_path = Path(".git") / "hooks" / "post-commit"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(HOOK_CONTENT)
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)
    print(f"Installed post-commit hook: {hook_path}")


if __name__ == "__main__":
    install_post_commit_hook()
