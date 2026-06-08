"""cns-watch: Auto-update 'updated' timestamp when node.md files change."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import frontmatter
from rich.console import Console
from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

NODES_DIR = Path(__file__).resolve().parent.parent / "nodes"

console = Console()


class _NodeMdHandler(FileSystemEventHandler):
    """Handle modification events for node.md files."""

    def on_modified(self, event: FileModifiedEvent) -> None:
        if event.is_directory:
            return

        path = Path(event.src_path)

        if path.name != "node.md":
            return

        try:
            post = frontmatter.load(str(path))
            today = date.today().isoformat()

            # Skip if already updated today (avoids infinite loop)
            if post.metadata.get("updated") == today:
                return

            post.metadata["updated"] = today
            path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")

            # Derive slug from parent directory name
            slug = path.parent.name
            console.print(f"[cns watch] {slug}/node.md -> updated: {today}")

        except Exception as exc:
            console.print(f"[red][cns watch] Error processing {event.src_path}: {exc}[/red]")


def run_watch() -> None:
    """Start watching nodes/ for changes and auto-update 'updated' timestamps."""
    if not NODES_DIR.exists():
        console.print(f"[red]Nodes directory not found: {NODES_DIR}[/red]")
        sys.exit(1)

    handler = _NodeMdHandler()
    observer = Observer()
    observer.schedule(handler, str(NODES_DIR), recursive=True)
    observer.start()

    console.print(f"[cns watch] Watching {NODES_DIR}/ ... (Ctrl+C to stop)")

    try:
        while observer.is_alive():
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()

    console.print("[cns watch] Stopped.")
