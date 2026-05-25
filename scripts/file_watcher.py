"""cns-watch: Auto-update 'updated' timestamp when project.md files change."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import frontmatter
from rich.console import Console
from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

PROJECTS_DIR = Path(__file__).resolve().parent.parent / "projects"

console = Console()


class _ProjectMdHandler(FileSystemEventHandler):
    """Handle modification events for project.md files."""

    def on_modified(self, event: FileModifiedEvent) -> None:
        if event.is_directory:
            return

        path = Path(event.src_path)

        if path.name != "project.md":
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
            console.print(f"[cns watch] {slug}/project.md -> updated: {today}")

        except Exception as exc:
            console.print(f"[red][cns watch] Error processing {event.src_path}: {exc}[/red]")


def run_watch() -> None:
    """Start watching projects/ for changes and auto-update 'updated' timestamps."""
    if not PROJECTS_DIR.exists():
        console.print(f"[red]Projects directory not found: {PROJECTS_DIR}[/red]")
        sys.exit(1)

    handler = _ProjectMdHandler()
    observer = Observer()
    observer.schedule(handler, str(PROJECTS_DIR), recursive=True)
    observer.start()

    console.print(f"[cns watch] Watching {PROJECTS_DIR}/ ... (Ctrl+C to stop)")

    try:
        while observer.is_alive():
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()

    console.print("[cns watch] Stopped.")
