---
id: VIEWMD-0022
title: Render real node shapes in Mermaid flowcharts
status: implemented
area: [render, mermaid]
effort: high
created: 2026-08-05
updated: 2026-08-06
accepted_by: George Moses
accepted_at: 2026-08-06
commits: [3a9288c, 5acc96b, 63ceecb, 775771b]
related: [VIEWMD-0015, VIEWMD-0027]
supersedes: []
changelog: "[1.7.0]"
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

**Diamond `{}`** -- true tapered rhombus, per requirement 2: ASCII `/` `\`
diagonals (cleaner in monospace than ╱╲), wide flat tip capped with `▔`/`▁`,
one-cell-per-row taper, label lines packed with no gap. Edges attach at the
apex points. Shape tuned against `docs/decision.txt`:

```
     /▔▔▔▔▔\
    /       \
   /         \
  / Decisions \
  \ Triangles /
   \         /
    \       /
     \▁▁▁▁▁/
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

- **Cursor Grok** (agent), 2026-08-06: Implemented against the glyph proposal on the issue. Parser recognizes all six shapes (longest-delimiter-first) with name/label split; `GraphNodeSpec`/`Node` carry `shape`; bare later refs no longer wipe an earlier shaped declaration. Canvas draws round/stadium/circle/subroutine/cylinder via distinct border glyphs on the existing box geometry; diamond is a true per-row tapered rhombus with apex edge attachment (T-junctions skipped at diamond exits), retuned to the `docs/decision.txt` mockup (ASCII `/` `\` diagonals, wide `▔`/`▁` tip, packed multi-line labels). Hand-verified fixtures: `shape_{round,stadium,circle,subroutine,cylinder,diamond}` plus updated `shapes_fallback` (single diamond + yes/no branches) and `complex_backend` (real cylinders). Parser unit tests cover each shape and the `B{Decision}`/`B` identity fix. Rectangle-only VIEWMD-0015 goldens unchanged (`./run-tests.sh` 314 passed). Updated `docs/mermaid-examples.md` to drop the stale "only `[...]`" limitation note (BT/RL still points at VIEWMD-0027). Notes for maintainer: (1) ASCII mode keeps `+`/`-`/`|` for every non-diamond shape per the proposal's fallback note -- only unicode distinguishes them (diamond keeps `/` `\` in both modes); (2) a diamond sharing grid columns with a rectangle widens that rectangle via `column_width` max (inherent to the 3x3 layout), visible in `shapes_fallback`'s slightly wider Start box; (3) hexagon/`{{}}` and other unsupported shapes still don't crash (req. 4) but aren't specially recognized.
- **Claude (Sonnet 5)** (agent), 2026-08-06: Independent pass over `3a9288c`/`5acc96b`, not just re-reading the diff -- ran the full suite, rendered `docs/diamonds.md` and every example in `docs/mermaid-examples.md`, and diffed fixtures against pre-VIEWMD-0022 baselines byte-for-byte. Found and fixed three issues, all on top of the same two commits (`63ceecb`): (1) **req. 3 violation** -- the horizontal-label padding added for the "spaces around labels" ask was applied to vertical labels too, widening `bidirectional`'s plain `[...]` boxes from 8 to 10 columns and silently breaking VIEWMD-0015's byte-for-byte baseline (the golden fixture had been edited to match rather than preserved); scoped the padding to horizontal label lines only and restored `bidirectional.*.out` byte-for-byte. (2) Diamonds could leave a 1-column gap before the `/`/`\` border at the middle row whenever the one-cell-per-row taper didn't reach the box's own edge -- visible as inconsistent arrow spacing between diamonds of different tip sizes in the shipped `docs/diamonds.md`, and whenever a diamond shared a TD grid column with a wider sibling rectangle (`docs/mermaid-examples.md`'s "Decision with stadium terminals" and "Nested decisions"); fixed by capping/growing the diamond's width and height (`canvas.diamond_height_for_width`) so the taper always closes flush -- verified zero remaining gaps across every fixture and every doc diagram. (3) `A{{Hexagon}}` mismatched the DIAMOND `{...}` delimiter and rendered a diamond with a corrupted `{Hexagon}` label instead of falling back per req. 4's discipline; `parse_node` now explicitly rejects doubled braces. Added regression tests for all three (`shape_diamond_lr_chain` fixture, plus assertions in `test_mermaid_flowchart.py`/`test_mermaid_flowchart_parser.py`). `./run-tests.sh` green, 320 passed. Verdict: requirements 1-4 and the acceptance criteria are met after these fixes; recommend proceeding to maintainer sign-off.
- **George Moses** (maintainer), 2026-08-06: Shown the diff (`3a9288c`, `5acc96b`, `63ceecb`, `775771b`; 33 files, +947/-170) and the review findings above. Said yes -- "commit and close this out."
