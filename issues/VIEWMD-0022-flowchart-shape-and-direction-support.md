---
id: VIEWMD-0022
title: Render real node shapes in Mermaid flowcharts
status: in-progress
area: [render, mermaid]
effort: high
created: 2026-08-05
updated: 2026-08-06
accepted_by: George Moses
accepted_at: 2026-08-06
commits: []
related: [VIEWMD-0015, VIEWMD-0027]
supersedes: []
changelog:
reason:
---

# Render real node shapes in Mermaid flowcharts

## Summary

VIEWMD-0015 ported flowchart rendering byte-for-byte against `github.com/AlexanderGrooff/mermaid-ascii`, which turned out to only recognize `A[Label]` square-bracket syntax as a distinct node shape -- every other mermaid shape syntax (`()`, `{}`, `(())`, `[()]`, `[[ ]]`, etc.) silently flattens to a bare label. This issue is to go beyond the upstream reference and implement real shape rendering in viewmd, now that the flowchart engine (`viewmd/mermaid/grid/`, `viewmd/mermaid/flowchart/`) exists to build on. (`BT`/`RL` direction reversal, originally scoped here too, is split out to [VIEWMD-0027](VIEWMD-0027-flowchart-rl-bt-direction-reversal.md) -- same underlying limitation category, but an unrelated fix in a different part of the engine.)

## Motivation / problem

Round (`()`), stadium/pill (`([ ])`), subroutine (`[[ ]]`), cylinder (`[( )]`), and diamond (`{}`) shapes are common in real-world Mermaid flowcharts -- diamonds especially, for decision nodes. Silently flattening them to a bare-label rectangle (VIEWMD-0015's `shapes_fallback` fixture demonstrates this: `B{Decide}` renders as a box literally labelled `B{Decide}`) is a visible, surprising gap directly inherited from upstream's own limitation, not a deliberate viewmd design choice.

This isn't just a cosmetic gap: it silently breaks graph topology. `docs/example.md`/`docs/mermaid-examples.md`'s own "Branching and labelled edges" example (`A[Start] --> B{Decision}` followed by `B -->|yes| C[Do it]` / `B -->|no| D[Skip it]`) is reported by the maintainer as rendering "weirdly" -- three boxes spread across two disconnected rows instead of the expected single-diamond-with-two-branches tree. Root cause: since `{}` isn't recognized, `parse_node` treats the *entire* string `"B{Decision}"` as the node's bare name, distinct from the plain `"B"` referenced by the later `-->|yes|`/`-->|no|` lines -- two different node identities for what the user wrote as one node. Fixing shape parsing must extract the name (`B`) separately from the shape delimiter and label (`{Decision}`), the same way `[...]` already does, so `B{Decision}` and later bare `B` references resolve to the same node and the branch reunites into the tree shape real Mermaid renders.

## Requirements

1. MUST parse `()` (round), `{}` (diamond), `(())` (circle), `([ ])` (stadium), `[[ ]]` (subroutine), and `[( )]` (cylinder/database) node-shape syntax in `viewmd/mermaid/flowchart/parser.py`'s node grammar, distinct from the plain `[...]` rectangle. MUST extract the node's *name* separately from the shape delimiters and label text (the way `[...]` parsing already does), so a shaped declaration like `B{Decision}` and a later bare reference to `B` resolve to the same node -- not two different nodes as they do today (see Motivation).
2. MUST render each shape with a distinguishable border in `viewmd/mermaid/grid/canvas.py`'s box-drawing -- exact glyph choices are a design decision for this issue, not dictated by upstream since there's no reference output to match (see "Shape glyph proposal" below). Round, stadium, circle, subroutine, and cylinder MAY reuse the existing 3x3 fixed-rectangle geometry with new corner/side glyphs. Diamond MUST render as a true tapered rhombus outline (pointed top/bottom, diagonal sides), not a rectangle with diamond-marked corners -- this is the shape the motivation section is built around and a corner-marker treatment would leave the "looks like a diamond" acceptance criterion unmet. This requires `draw_box` (or a diamond-specific sibling) to support a variable per-row width, and requires edge paths to attach at the diamond's point/apex rather than a rectangle corner -- both `viewmd/mermaid/grid/canvas.py` and the path-routing logic in `viewmd/mermaid/flowchart/graph.py` (`_determine_path` and friends) are in scope for this specifically.
3. MUST NOT change the byte-for-byte-matched behavior for `[...]` rectangle nodes -- this issue only adds new rendering paths, it doesn't touch VIEWMD-0015's verified baseline.
4. MUST leave a flowchart fence untouched (no crash) on any shape that still isn't supported, same fallback discipline as VIEWMD-0015 requirement 6.

## Non-goals

- `BT`/`RL` direction reversal -- tracked separately as [VIEWMD-0027](VIEWMD-0027-flowchart-rl-bt-direction-reversal.md).
- Matching any upstream reference byte-for-byte -- there is none for this behavior, since `mermaid-ascii` doesn't implement it either. Golden fixtures for this issue are necessarily hand-authored/visually-verified, unlike VIEWMD-0014/0015/0016's differential-tested ones.
- Fill colors or other styling shapes can't represent in plain box-drawing art (unchanged from VIEWMD-0015's non-goals).
- Any other Mermaid flowchart feature not already covered by VIEWMD-0015 (e.g. new arrow styles, `click` interactions) -- out of scope unless discovered to be needed alongside shapes.

## Design notes / links

VIEWMD-0015 (`issues/archive/VIEWMD-0015-mermaid-flowchart-diagrams.md` once archived) is the byte-for-byte baseline this extends. `viewmd/mermaid/flowchart/parser.py:parse_node` is where shape parsing currently only recognizes `[...]`; `viewmd/mermaid/grid/canvas.py:draw_box` is where the border glyphs are chosen. The parsed shape also has to reach `draw_box`: `GraphNodeSpec` (parser.py) and `Node` (`viewmd/mermaid/flowchart/graph.py`) carry no shape field today, and `mk_graph()` (graph.py, where it currently copies `spec.label`/`spec.style_class` onto each `Node`) is where a new `shape` field must be threaded through, from parse result to the `canvas.draw_box(...)` call site (graph.py's node-drawing loop) -- this middle layer is easy to miss since it's neither the parser nor the canvas.

### Shape glyph proposal (pending maintainer review)

All mockups render the same content as today's baseline (`B[Decide]` -> a
6-char label, 1 cell of `BOX_BORDER_PADDING` each side) so they're directly
comparable to current output. Non-ASCII glyphs below fall back to `use_ascii`
mode's existing `+`/`-`/`|` set the same way the rectangle border already
does; that fallback mapping is an implementation detail, not re-proposed here
per-shape.

**Rectangle `[...]`** (unchanged baseline, shown for comparison):

```
┌────────┐
│        │
│ Decide │
│        │
└────────┘
```

**Round `()`** -- rounded corners, straight sides, same geometry as rectangle:

```
╭────────╮
│        │
│ Decide │
│        │
╰────────╯
```

**Stadium `([ ])`** -- fully-rounded (pill) ends: the left/right border is
`(`/`)` for its whole height, not just the corners:

```
(────────)
(        )
( Decide )
(        )
(────────)
```

**Circle `(( ))`** -- double-line border (whole box), distinguishing it from
round/stadium's single-line curves:

```
╔════════╗
║        ║
║ Decide ║
║        ║
╚════════╝
```

**Subroutine `[[ ]]`** -- square rectangle corners, but the vertical sides use
a double-bar glyph (`‖`) to hint at the extra inner divider lines real Mermaid
draws just inside the box edges, without widening the box:

```
┌────────┐
‖        ‖
‖ Decide ‖
‖        ‖
└────────┘
```

**Cylinder `[( )]`** -- rounded corners like round, but a double-line bottom
border (`═`) to suggest the drum's base/rim:

```
╭────────╮
│        │
│ Decide │
│        │
╰════════╯
```

**Diamond `{}`** -- true tapered rhombus, per requirement 2: diagonal sides
(`╱`/`╲`) meeting at a point top and bottom, box widens then narrows across
rows rather than staying a fixed rectangle. Edges attach at the apex points,
not at rectangle corners:

```
      ╱▔▔╲
    ╱      ╲
  ╱  Decide  ╲
  ╲          ╱
    ╲      ╱
      ╲__╱
```

Open questions for maintainer sign-off: (a) do the six choices above read as
visually distinct enough from each other and from the rectangle baseline; (b)
is the diamond's exact taper/row-count acceptable, or should it hug the label
more tightly; (c) subroutine's `‖` vs. a "true" double-column variant (extra
vertical divider lines one cell inside the box, costing +2 width) -- the `‖`
option above is proposed as the cheaper default.

## Acceptance / verification

- Unit tests for each new shape's parsing (node type, label extraction) and a rendered fixture per shape showing a visibly distinct border, hand-verified (no upstream binary to diff against, per non-goals).
- The `docs/mermaid-examples.md` "Branching and labelled edges" example (`A[Start] --> B{Decision}`, `B -->|yes| C[Do it]`, `B -->|no| D[Skip it]`) renders as a single diamond node with two outgoing branches, not three disconnected boxes -- a unit test asserting `B{Decision}` and a later bare `B` parse to the same node name.
- All of VIEWMD-0015's existing fixtures still pass unchanged (regression guard on the byte-for-byte baseline).
- `./run-tests.sh` green.

## Peer review

Left blank until implemented and tested; filled in as part of the Definition of Done landing gate.
