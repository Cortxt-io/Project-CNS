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
────────────────────────────────────────────────
 MAP / structure (primary)   │ READOUT (primary, mirrors selection)
                             │  selected node detail + related items
────────────────────────────────────────────────
 [Tabs: Plan A | Plan B | Decisions]   (secondary surfaces, one at a time)
   active tab content
```
- **Selection is the spine**: one selected item drives both the map focus and the
  readout. Nothing selected → an overview in the readout.
- **Secondary surfaces are tabs**, not stacked rails. (cockpit: Roadmap / Bygg-guide /
  Beslut — was three stacked rails, now one tab at a time.)

## Progressive disclosure
- Primary focus (map + readout) always visible; the depth (roadmap, guide, decisions)
  sits behind tabs — pick one, don't scroll past all three.
- Cross-highlight ties it together: selecting in the map lights related rows in the
  active tab; clicking a linked row selects its node. Same `nodeRefs()` helper both ways.

## Anti-patterns (learned)
- Stacking every context surface below the focus → a long noisy scroll. Use tabs.
- Showing full roadmap + full guide + full decisions at once → the user can't tell
  what's primary. One focus (selection) + one open tab.

## Worked example
**cockpit `/vertikal/:slug`** (React, `@cortxt/ui` + `@cortxt/graph`):
`cortxt/apps/app/src/pages/Vertical.jsx` — graph + readout grid (primary), plan tabs
(Roadmap | Bygg-guide | Beslut), `nodeRefs()`/`touches()` cross-highlight. Tab styles
`cc-tabs`/`cc-tab`/`cc-tabpanel` in `apps/app/src/styles/app.css`. Shipped PR cortxt#24.

Shares the tab + progressive-disclosure spine with [result-ranking.md](result-ranking.md);
differs in that the **selection** (not a ranked list) is the organising principle.
