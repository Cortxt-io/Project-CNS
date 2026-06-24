# Surface pattern: overview / portfolio

The entry surface of a tool — scan the whole set, find one thing, drill in. Proven on
**orgkomp Home** (`/`, the teams list). Copy this for the next "land here and orient" surface.

## One job
"What's in here, and where's the thing I want?" Scan a few headline numbers, search/filter,
open one item. Not deep detail — that's the detail/readout surface.

## Layout / hierarchy
```
Nav
[stat strip]  N teams · N deliveries · N cross-fn KPIs        (a few real numbers)
[view switcher]  Live views as tabs · future views → SoonSlot
[search]  one prominent field
[result count]
[card grid]  one card per item → click → detail
```
- **Search + card grid are primary** (the find-and-open path). Stats are a thin orienting strip.
- **One prominent search**, not a wall of filters. Filters arrive when real (SoonSlot until then).

## Progressive disclosure & noise rules (learned)
- **Don't ship disabled stubs that hog prime space** — a disabled "Filters — coming soon" bar,
  three disabled view tabs, a fake "Health" stat. Signpost the future quietly with **SoonSlot**
  (a small muted line), or hide it until it's real. This was orgkomp Home's main noise.
- Cards are scannable: name + type chip + one-line pitch + a signature metric (orgkomp: the
  ports motif ← in · out →). Keep each card to a glance.

## Worked example
**orgkomp Home** — `orgkomp/app/page.tsx` (stat strip + `ViewSwitcher` + `TeamsList`).
Modules: `SoonSlot` (quiet "coming" signpost), live-only `ViewSwitcher`. Shipped orgkomp#3.
React/Next + shadcn tokens.
