# ETL archetype — reference implementation (Python)

The canonical shape of a decision-support tool's **data layer**: ingest open data →
normalize → emit versioned, provenanced artifacts the decision-engine and UI consume.
Distilled from the proven juvahem ETL (`juvahem/etl/`), kept entity-agnostic so the
next tool inherits the bones, not the domain.

> One cell of the `archetype × stack` matrix: **archetype `etl` · stack `python`**.
> Nodes tagged `archetype: etl` in `catalog.yaml` are instances of this; a product's
> cookbook `etl` step points here.

## The invariants (what makes it the archetype, not just "an ETL")

1. **Provenance on every value.** No bare numbers — each is a `Metric` wrapping
   `Provenance(source, period, fetched)`. Freshness is always visible; nothing is
   silently stale. This is the signature of a *trustworthy* decision tool.
2. **Isolated source clients.** One module per external source (`kolada.py`,
   `scb.py`, …), each `fetch_*` returning normalized tables keyed by entity id. One
   source breaking never corrupts the others.
3. **Typed model as the seam.** `models.py` is the stable contract the
   decision-engine (scoring) and the UI depend on. Change it deliberately.
4. **Per-entity JSON + index, GitHub = truth.** Write one `data/entities/<id>.json`
   plus `data/index.json` with a `generated` date. Commit the output. The read-API
   consumes committed JSON, never the live source — so a source being down at read
   time never breaks the product.
5. **Idempotent.** Re-running rebuilds from source. Run locally or via a scheduled
   GitHub Action.

## Files

| File | Role |
|------|------|
| `models.py` | Canonical typed model — `Entity`, `Metric`, `Provenance`. The contract. |
| `source_template.py` | One source client. Copy + rename `SOURCE` per data source. |
| `build.py` | Orchestrator — fetch all sources → merge → write per-entity JSON + index. |
| `requirements.txt` | `httpx` + `pydantic`. |

## Instantiate it in a new tool

1. Copy `archetypes/etl-python/` into the tool's repo (e.g. `etl/`).
2. In `models.py`: rename `Entity` to your domain entity; replace `ExampleBlock`
   with typed blocks for your real dimensions (keep every value a `Metric`).
3. Copy `source_template.py` once per data source; implement `fetch_*` against the
   real API; set `SOURCE`.
4. In `build.py`: import your source clients, fill `METRICS`, merge each block.
5. `pip install -r requirements.txt && python build.py` → commit `data/`.

The proven, fully-fleshed example to read alongside this: **`juvahem/etl/`**
(Kolada + JobTech + SCB → 290 municipalities, each with economy/population/housing/jobs).
