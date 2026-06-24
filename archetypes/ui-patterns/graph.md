# Shared primitive: node graph (ELK + ReactFlow)

The relationship-graph visual used wherever a surface shows nodes + edges. Treated like
a **shared design-system primitive** (same thinking as the shadcn primitives): one hardened
engine, each surface skins it with its own node type, edge semantics, colours and click
action. Two surfaces use it today; more coming — so the recipe is codified, not re-invented.

## The recipe
- **Layout = elkjs** (`elk.algorithm: layered`, direction by semantics — usually RIGHT for a
  directed flow). Async → run in an effect, store positions, feed them to the renderer.
- **Render = ReactFlow v11** — custom node component (the "skin"), hidden `<Handle>`s
  (left target / right source — *required* or edges don't attach), `smoothstep` edges with
  `MarkerType.ArrowClosed`, `<Controls>` for zoom/fit, `fitView`.
- **Standard interactions:** select/hover a node → it + its neighbours stay lit, the rest
  dims; edges to/from it highlight (label on hot); click → open that node's detail.
- **Gotchas (learned):** edges need Handles or they silently don't render; gate edges on
  positions so they appear with their nodes (orphaned edges never revive); scale height to
  node count (a few nodes in a tall panel reads barren).

## Per-surface skin (shared engine, own identity)
Each surface passes its own node type + colours + click action — like shadcn primitives:
shared behaviour, own face. Don't fork the engine; fork the skin.

## Worked examples
- **cockpit `@cortxt/graph`** (`cortxt/packages/graph/src/NodeGraph.jsx`) — `CnsNode`,
  feeds/depends_on/part_of edges, kind-colour + health dot, expand/collapse parents.
- **orgkomp `OrgGraph`** (`orgkomp/components/OrgGraph.tsx`) — `TeamNode`, delivery edges,
  support/line colours, in/out-degree badge, click → team profile.

## Consolidation direction (the real next step)
Today the recipe is **copied per repo** (cortxt monorepo has `@cortxt/graph`; orgkomp carries
its own copy, since it's a separate repo). The goal — exactly the shadcn move — is **one shared
graph primitive across repos**: make `@cortxt/graph` publishable/consumable from other repos so
every graph surface consumes the same hardened ELK+ReactFlow engine and only ships its skin.
Same cross-repo-sharing problem already solved for the shadcn primitives. Until then: copy the
recipe, keep the two in sync, consolidate when a third graph makes sharing clearly worth it.
