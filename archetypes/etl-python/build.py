"""Build canonical entity artifacts from open data — the ETL orchestrator.

Fetches every source client, merges into the typed Entity model, writes one JSON
per entity + an index.json summary. Idempotent: re-running rebuilds from source.
Run locally or via a GitHub Actions cron; COMMIT the output (GitHub = source of
truth). The read-API / decision-engine consume the committed JSON, never the live
API — so a source being down at read time never breaks the product.

Distilled from juvahem's etl/build_communes.py; entity-agnostic.

Usage:  python build.py
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx

import source_template as src  # one import per source client
from models import Entity, ExampleBlock, Metric, Provenance

DATA_DIR = Path(__file__).resolve().parent / "data"
ENTITIES_DIR = DATA_DIR / "entities"

# Map your model fields to this source's metric keys (juvahem's KPI dict).
METRICS = {
    "a_metric": "KEY_A",
    "another_metric": "KEY_B",
}


def _metric(table: dict, entity_id: str, source_key: str, today: str) -> Metric | None:
    """Wrap a normalized (value, period) into a Metric with provenance. Missing → None."""
    hit = table.get(entity_id)
    if hit is None:
        return None
    value, period = hit
    return Metric(
        value=value,
        provenance=Provenance(source=f"{src.SOURCE}:{source_key}", period=period, fetched=today),
    )


def main() -> None:
    today = dt.date.today().isoformat()
    ENTITIES_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=60) as client:
        entities = src.fetch_entities(client)
        print(f"Entities: {len(entities)}")
        tables = {field: src.fetch_metric(client, key) for field, key in METRICS.items()}
        for field, table in tables.items():
            print(f"  {field} ({METRICS[field]}): {len(table)} with data")

    index = []
    for e in entities:
        eid, name = e["id"], e["name"]
        entity = Entity(
            id=eid,
            name=name,
            example=ExampleBlock(
                a_metric=_metric(tables["a_metric"], eid, METRICS["a_metric"], today),
                another_metric=_metric(tables["another_metric"], eid, METRICS["another_metric"], today),
            ),
        )
        (ENTITIES_DIR / f"{eid}.json").write_text(
            entity.model_dump_json(indent=2, exclude_none=True), encoding="utf-8"
        )
        index.append({"id": eid, "name": name})

    index.sort(key=lambda x: x["name"])
    (DATA_DIR / "index.json").write_text(
        json.dumps({"generated": today, "count": len(index), "entities": index},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(index)} entities to {ENTITIES_DIR} + index.json")


if __name__ == "__main__":
    main()
