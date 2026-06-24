"""Canonical data model for ONE entity in a decision-support tool.

Reference implementation of the ETL archetype's typed contract (Python stack).
Replace `Entity` with your domain entity (municipality, course, company, ...) and
the `ExampleBlock` with your real dimensions. Keep the INVARIANT that makes this an
archetype: every value is a `Metric` carrying `Provenance`, so data freshness is
always visible and nothing is silently stale. This schema is the stable seam the
decision-engine (scoring) and the UI depend on — keep fields stable once shipped.

Distilled from the proven juvahem ETL (etl/models.py); kept entity-agnostic.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    """Where a value came from and when it was fetched. The trust layer."""

    source: str  # "<source>:<key>", e.g. "kolada:N00901"
    period: str | int | None = None  # the data period the value refers to
    fetched: str  # ISO date the ETL pulled it


class Metric(BaseModel):
    """A single numeric value plus its provenance. The atomic unit of the model.

    Never store a bare number — wrap it so the UI can show "tax 31.2% (kolada, 2025)"
    and flag anything stale. This is the archetype's signature.
    """

    value: float | None = None
    provenance: Provenance


class ExampleBlock(BaseModel):
    """A domain block groups related Metrics. Copy this shape per dimension your
    decision-engine scores (juvahem has economy / population / housing / jobs)."""

    a_metric: Metric | None = None
    another_metric: Metric | None = None


class Entity(BaseModel):
    """One thing the tool ranks/scores. `id` is the stable key (string)."""

    id: str = Field(pattern=r"^.+$")
    name: str
    example: ExampleBlock = Field(default_factory=ExampleBlock)
    # Add typed blocks per domain dimension here. For free-form / keyed collections
    # (juvahem's jobs keyed by occupation field) use: dict[str, Metric].
