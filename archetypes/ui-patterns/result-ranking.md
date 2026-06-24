# Surface pattern: result-ranking

A tool that ranks many options against the user's priorities and lets them see *why*.
Proven on **juvahem `/jamfor`** (ranks 290 municipalities). Copy this for the next
ranking surface.

## One job
"Which option ranks best for me?" → adjust priorities, see the ranked result instantly;
expand one for *why*; a map/visual for orientation (secondary).

## Layout / hierarchy
```
H1 (identity)
[Tabs]  (mode/segment — clean underline tabs)        [Sökfilter] (mobile only)
────────────────────────────────────────────┬──────────────────
 MAIN (primary)                              │ CONTROL PANEL (secondary)
   secondary visual (map/chart, short)       │  desktop: sticky in-grid card
   ranked list (THE answer)                  │  mobile:  left slide-in drawer
     ▸ expand → tabs (Why | … | …)           │           behind "Sökfilter" + backdrop
```
- **Result is primary**, visual is secondary (shorter, with its own overlay controls).
- **Controls live in one tidy panel**, never scattered or always-on across the page.
- **Expansion = tabs**, not stacked sections.

## Progressive disclosure
- Default view = result + visual + the panel (desktop) / a "Sökfilter" button (mobile).
- All tuning sits in the panel; the panel is a **left slide-in drawer on mobile**
  (`<1000px`, with backdrop + close), an in-grid sticky card on desktop.
- Row detail opens into **tabs**, not six stacked blocks.

## Control order = priority (not input order)
Order controls by value to the answer, not by "you pick this first":
**core weighting → the high-value profile input → optional shortcut (compact, last)**.
juvahem: Vikter → Jobbmatchning → Snabbval (the preset shortcut is light, compact, last).

## Slim the controls
- Sliders: **one row each** (`label · track · %`), not label-above-track (~half height).
  Long labels ellipsize with a `title` tooltip.
- Shortcuts: compact **chips**, not big description cards. No emoji-as-icons.

## Anti-patterns (learned the hard way)
- Everything visible at once → noise. Big preset cards owning the top → reads as a toy.
- Stacked detail sections → use tabs. Rendering the same component twice (e.g. a summary
  in the row *and* the expansion) → single render / prop variant.
- Map taller than the result it serves.

## Worked example
**juvahem `/jamfor`** (SvelteKit) — files:
`src/routes/jamfor/+page.svelte` (layout, tabs, panel/drawer), `src/lib/components/`:
`RankedList.svelte` (tabbed expansion), `WeightSliders.svelte` (one-row sliders),
`PresetPicker.svelte` (chips), `Map.svelte` (short, overlay controls),
`Explanation.svelte` (compact/full variant). Shipped PRs #6–#11.

**Per stack:** Svelte version is juvahem above. For the React/`@cortxt/ui` cockpit, the
same structure composes on shadcn/ui primitives — add a React worked example here when
cockpit /vertikal adopts it.
