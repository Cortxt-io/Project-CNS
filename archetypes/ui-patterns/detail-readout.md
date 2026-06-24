# Surface pattern: detail / readout (command center)

A focused view of ONE thing (a product, an entity) where selecting a part pulls its
map + detail + related plan items into one focus. Proven on **cockpit `/vertikal`**
(React) — a per-product command center. Copy this for the next detail/command surface.

## One job
"What's the state of this thing, and what do I do next?" Selecting a node focuses the
map (dims the rest, lights neighbours) and the readout (its detail + everything that
touches it). Secondary plan/context surfaces are reachable but not all at once.

## Layout / hierarchy
```
← back · Title · status line
┌──────────── MAP / structure (HERO, full width, large) ───────────┐
│  the graph IS the answer — large, with zoom/fit controls          │
│  select a node → lean readout (overlay bottom-left on desktop)     │
└───────────────────────────────────────────────────────────────────┘
[Tabs: Plan A | Plan B | Decisions]   (secondary surfaces, one at a time)
  active tab content
```
- **The map/graph is the hero** — full-width and *large* (the thing IS its structure);
  don't shrink it to a secondary-map size (that's the result-ranking treatment, wrong here).
- **Selection is the spine**: select a node → a *lean* readout appears (identity, summary,
  links, a "touches: N/M/K" count) — the detailed related rows light in the active tab, so
  the readout doesn't duplicate them. Nothing selected → clean map + a hint + tabs.
- **Secondary surfaces are tabs**, not stacked rails. (cockpit: Roadmap / Bygg-guide /
  Beslut — was three stacked rails, now one tab at a time.)

## Progressive disclosure
- Default = clean map + tabs; the readout is *on demand* (selection). Depth (roadmap,
  guide, decisions) sits behind tabs — pick one, don't scroll past all three.
- **Readout is responsive** (same idiom as a mobile filter drawer): floating overlay on
  the graph on desktop (`≥1000px`), a **stacked section below the graph on mobile** — a
  floating card over an ELK graph covers it and clashes with pan/zoom on small screens.
- Cross-highlight ties it together: selecting in the map lights related rows in the
  active tab; clicking a linked row selects its node. Same `nodeRefs()` helper both ways.

## Anti-patterns (learned)
- Stacking every context surface below the focus → a long noisy scroll. Use tabs.
- Showing full roadmap + full guide + full decisions at once → the user can't tell
  what's primary. One focus (selection) + one open tab.

## Worked example
**cockpit `/vertikal/:slug`** (React, `@cortxt/ui` + `@cortxt/graph`):
`cortxt/apps/app/src/pages/Vertical.jsx` — full-width hero graph + readout overlay on
selection + plan tabs (Roadmap | Bygg-guide | Beslut), `nodeRefs()`/`touches()`
cross-highlight. Styles `cc-tabs`/`cc-readout-overlay` (responsive) in
`apps/app/src/styles/app.css`. Shipped PRs cortxt#24 (tabs), #25 (graph-central), #26
(large graph + responsive readout).

Shares the tab + progressive-disclosure spine with [result-ranking.md](result-ranking.md);
differs in that the **selection** (not a ranked list) is the organising principle.
