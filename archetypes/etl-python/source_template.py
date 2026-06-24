"""Template source client — ONE module per external data source.

Each source client isolates one API: fetch + normalize into tables keyed by entity
id, returning plain values the orchestrator wraps into Metrics. Keep sources
isolated (juvahem has kolada.py / scb.py / jobtech.py) so one source breaking never
corrupts the others. COPY this file per source and rename SOURCE.

Distilled from juvahem's etl/kolada.py.
"""
from __future__ import annotations

import httpx

SOURCE = "example"  # used in Provenance.source as "<SOURCE>:<key>"
BASE_URL = "https://api.example.org/v1"


def fetch_entities(client: httpx.Client) -> list[dict]:
    """Return the canonical entity list: [{"id": ..., "name": ...}, ...].

    Usually ONE source owns the entity universe (juvahem: Kolada's municipality list);
    the rest only contribute metrics keyed by that id.
    """
    resp = client.get(f"{BASE_URL}/entities")
    resp.raise_for_status()
    return [{"id": row["code"], "name": row["title"]} for row in resp.json()]


def fetch_metric(client: httpx.Client, key: str) -> dict[str, tuple[float, str | int]]:
    """Return {entity_id: (value, period)} for one metric key.

    The orchestrator turns each into Metric(value, Provenance(source=f"{SOURCE}:{key}",
    period=period, fetched=today)). Normalize here — the orchestrator stays dumb.
    """
    resp = client.get(f"{BASE_URL}/metric/{key}")
    resp.raise_for_status()
    return {row["id"]: (row["value"], row["period"]) for row in resp.json()}
