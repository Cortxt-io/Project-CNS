# UI surface-pattern catalog

The UI counterpart to the code archetypes (`archetypes/etl-python/`). A **surface
type** (result-ranking, overview, input-wizard, detail/readout…) has a reusable
layout + interaction pattern. Codify it once from a proven example, then the next
surface of that type *copies the reference* instead of rediscovering it.

Stack-agnostic pattern (structure / hierarchy / disclosure) + pointers to the proven
per-stack worked example. Built via the working method below — *build one surface
right, generalise from the result* (same as the ETL archetype, not a framework in a
vacuum).

## The working method (loop per surface)
1. **One job** — one sentence: what question does this surface answer / what single
   action does it drive? Everything else is noise to cut.
2. **Hierarchy before pixels** — a low-fi wireframe, approved before building.
3. **Compose, don't author** — only from the design system's tokens/primitives; no
   ad-hoc CSS/colour.
4. **Progressive disclosure** — default minimal; tuning behind a panel / drawer / tabs.
5. **Look & cut** — render → look at it → cut against the one job. Floor: responsive,
   empty/error states, a11y.

## Surface types
| Type | Pattern | Status | Proven example |
|------|---------|--------|----------------|
| **result-ranking** | [result-ranking.md](result-ranking.md) | ✅ proven | juvahem `/jamfor` (Svelte) |
| **detail / readout** | [detail-readout.md](detail-readout.md) | ✅ proven | cockpit `/vertikal` (React) |
| **overview / portfolio** | [overview.md](overview.md) | ✅ proven | orgkomp Home (React) |
| input / editor | _tbd_ | planned | (orgkomp /edit, next) |

## Shared primitives (used within surfaces)
| Primitive | Doc | Recipe | Used by |
|-----------|-----|--------|---------|
| **node graph** | [graph.md](graph.md) | ELK + ReactFlow, skin per surface | cockpit `@cortxt/graph`, orgkomp `OrgGraph` |

## How to use
Building a new surface? Identify its type → read that type's pattern doc → copy the
worked example, adapting to the product's stack + identity. New type → run the method
on one surface, then add a pattern doc here.
