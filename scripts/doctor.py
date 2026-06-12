"""CNS doctor — environment diagnostics and mode recommendations."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = PROJECT_ROOT / "catalog.yaml"
EXPORTS_DIR = PROJECT_ROOT / "exports"
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "catalog_schema.json"
ENV_PATH = PROJECT_ROOT / ".env"


def run_doctor(console: Console) -> None:
    """Run diagnostic checks and print a report."""
    load_dotenv(ENV_PATH)

    table = Table(title="CNS Doctor", show_lines=True)
    table.add_column("Check", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Detail")

    # 1. .env file
    env_exists = ENV_PATH.exists()
    table.add_row(
        ".env file",
        "[green]OK[/green]" if env_exists else "[red]MISSING[/red]",
        str(ENV_PATH) if env_exists else "Copy .env.example to .env",
    )

    # 2. API key
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    key_valid = bool(api_key) and api_key != "your_key_here"
    table.add_row(
        "PERPLEXITY_API_KEY",
        "[green]OK[/green]" if key_valid else "[yellow]NOT SET[/yellow]",
        "Configured" if key_valid else "Optional — needed only for api mode",
    )

    # 3. catalog.yaml
    catalog_exists = CATALOG_PATH.exists()
    sys_count = 0
    if catalog_exists:
        try:
            from scripts.catalog import load_catalog
            sys_count = len(load_catalog())
        except Exception:
            sys_count = 0
    table.add_row(
        "catalog.yaml",
        "[green]OK[/green]" if catalog_exists else "[red]MISSING[/red]",
        f"{sys_count} system" if catalog_exists else "Run cns new <slug> to create one",
    )

    # 4. exports/ directory
    exports_exist = EXPORTS_DIR.exists()
    table.add_row(
        "exports/ directory",
        "[green]OK[/green]" if exports_exist else "[yellow]MISSING[/yellow]",
        str(EXPORTS_DIR) if exports_exist else "Created automatically on first export",
    )

    # 5. JSON schema
    schema_exists = SCHEMA_PATH.exists()
    table.add_row(
        "catalog_schema.json",
        "[green]OK[/green]" if schema_exists else "[red]MISSING[/red]",
        str(SCHEMA_PATH) if schema_exists else "Schema file is missing — validation will fail",
    )

    console.print(table)
    console.print()

    # Mode recommendation
    if key_valid:
        console.print(
            "[green]All three modes available:[/green] local, connector (prepare), api"
        )
    else:
        console.print(
            "[yellow]Available modes:[/yellow] local, connector (prepare)\n"
            "Add PERPLEXITY_API_KEY to .env to enable api mode."
        )
