---
id: VIEWMD-0037
title: Shrink flowchart diamonds to be proportionate to the now-denser rectangle-family boxes
status: implemented
area: [render, mermaid]
effort: high
created: 2026-08-07
updated: 2026-08-07
accepted_by: George Moses
accepted_at: 2026-08-07
commits: [29d925e]
related: [VIEWMD-0022, VIEWMD-0036]
supersedes: []
changelog: "[1.9.0]"
reason:
---

# Shrink flowchart diamonds to be proportionate to the now-denser rectangle-family boxes

## Summary

Diamond decision nodes render far taller (and wider) than a rectangle-family box holding comparable content -- a gap that VIEWMD-0036 made much more visually obvious by shrinking every other node shape. A one-word diamond like `{OK}` renders as a 7-row rhombus next to a 3-row rectangle holding a longer word (`[Start]`); an 8-character label like `{Decision}` renders 11 rows tall. Diamonds should shrink to be proportionate to their content and to their rectangle-family siblings, while still reading as a genuine pointed rhombus rather than a flat hexagon.

## Motivation / problem

`viewmd/mermaid/flowchart/graph.py`'s `_set_column_width` sizes a diamond's interior as `mid_row = label_lines + 2 * (tip_hw + 1)` where `tip_hw` (1, 2, or 3, from `canvas.diamond_tip_half_width`) is chosen from the label's character width. Even the smallest tip size (`tip_hw=1`, labels of 2 characters or fewer) adds 4 rows of pure taper on top of the label's own line(s); the largest (`tip_hw=3`, any label over 6 characters -- i.e. most real decision text) adds 8. Compare a same-content rectangle, which since VIEWMD-0036 is exactly `label_lines` rows tall plus its two border rows.

This was tolerable when rectangles themselves carried the same 2-row padding VIEWMD-0036 just removed (a 7-row diamond next to a 5-row rectangle read as "a bit taller, tapered shape needs more room"); next to a 3-row rectangle it reads as badly out of proportion, and it compounds badly in diagrams with several diamonds in a vertical chain (see `docs/mermaid-examples.md`'s "Nested decisions" example, two diamonds stacked with rectangles between them).

Diamonds are a viewmd-original design (VIEWMD-0022 req. 2 -- upstream `mermaid-ascii` has no real diamond rendering to diverge from), so this is a first-party sizing decision, not a byte-for-byte-port question.

## Requirements

1. MUST reduce a diamond's rendered height and width to be proportionate to its label content and to a same-content rectangle-family box, for short and medium labels. Long labels (see Design notes for why) are bound by a geometric floor tied to the taper's fixed one-cell-per-row growth rate -- a label wide enough that its own minimum width already forces several taper rows to reach it without a gap gets no smaller no matter how the tip-size/padding constants are tuned; closing that gap too would require changing the growth rate itself (see Design notes for why that's riskier than this issue's scope), so it MUST NOT regress (no larger than today) but need not shrink.
2. MUST still render a genuine tapered rhombus -- a pointed single-cell top/bottom apex widening/narrowing by whole rows, not a flat-sided hexagon -- preserving the existing `tip_hw`-based tip-size selection (short/medium/long labels keep visually distinct tip widths) unless the chosen redesign has a good reason to change that too.
3. MUST keep the existing attachment invariants: `mid_row` stays odd (so `height // 2` lands exactly on the middle grid cell for LEFT/RIGHT edge attachment), and the UP/DOWN attachment cell stays centered on the tip.
4. MUST keep the taper reaching the box's own left/right border by the middle row with no gap before the `/`/`\` glyph (the VIEWMD-0022-follow-up bug class described in `graph.py`'s existing comments) -- see Design notes for why this constrains any naive height reduction.
5. MUST NOT change rectangle-family node sizing (that's VIEWMD-0036's, already landed) or edge/arrow routing length.
6. SHOULD keep the label fitting inside the shape with at least one column of horizontal breathing room, matching the rectangle family's own horizontal padding convention.

## Non-goals

- An exact target row/column count or formula -- judged against the mockups' proportions and the Acceptance criteria below, not a specific number.
- Changing the taper's per-row growth rate or otherwise redesigning `_draw_diamond`'s drawing algorithm -- see Design notes for why that's a bigger, riskier change than tuning the existing formula's constants and thresholds.
- Diamond color/style handling, or any non-diamond shape.

## Design notes / links

The sizing code is `viewmd/mermaid/flowchart/graph.py:333-368` (the `NodeShape.DIAMOND` branch of `_set_column_width`) and its near-duplicate `viewmd/mermaid/grid/canvas.py:362-393` (`diamond_intrinsic_height` / `diamond_height_for_width`); drawing itself is `_draw_diamond` (`canvas.py:396-473`).

**A naive shrink of `mid_row` alone does nothing** -- confirmed by hand while drafting this issue. `_set_column_width` runs a second pass after every node is sized (`graph.py`'s "diamonds need extra horizontal margin..." loop, `graph.py:230-246`) that recomputes `canvas.diamond_height_for_width(n.label, 1 + column_width[mid_x])` and raises `row_height[mid_y]` back up if the diamond's *width* isn't tall enough for its one-cell-per-row taper to reach that width by the middle row. Since the taper's growth rate (`_draw_diamond`'s `hw = tip_hw + y`, exactly 1 half-width unit per row) and the label-driven minimum width are both held fixed, this reassert step recomputes the same self-consistent (tall) height regardless of what the initial `mid_row` formula says -- tried patching `mid_row`'s formula alone against a live checkout and the rendered output was byte-identical to before. Any real fix has to change one of: the taper's per-row growth rate (more than 1 half-width unit per row shortens the rows needed to reach a given width), the tip-size thresholds/values, or the label-driven width floor itself -- not just the additive constants in the current formula.

**Implemented as:** dropping the fixed "+1" and "+4" margin terms from the `mid_row`/`mid_col` formulas (`label_lines + 2 * tip_hw` and `2 * border_padding + label.width + 2`, down from `+ 2 * (tip_hw + 1)` and `+ 4`), plus loosening `diamond_tip_half_width`'s thresholds (`<=3`/`<=9`/else, up from `<=2`/`<=6`/else) so more medium-length labels get a smaller tip. This works because, unlike the additive constants alone, these two changes together shift where the width/height fixed point in the reassert loop actually settles -- verified empirically on a live checkout (see Acceptance below), not just derived on paper. Confirmed behavior across label lengths: short labels (`OK`) drop from 7 to 5 rows; a same-shape sibling comparison (`shape_diamond_lr_chain`, three chained diamonds of different lengths) each shrink individually; a 14-character label (`Authenticated?`) stays at its original 13 rows -- its own `label_min` was already the binding constraint before this change, so it's an example of requirement 1's carve-out, not a missed case. This is the safe, empirically-validated ceiling without touching the taper's growth rate; see the paragraph above for why that would be a bigger, riskier change than this issue's scope.

## Mockups: current vs. proposed

Both mockups below are real rendered output, before and after this issue's implementation (not illustrative), paired with a short rectangle (`[Go]`) narrow enough that it doesn't stretch to share the diamond's column width and mask the diamond's own size.

**Short label** (`{OK}`):

Current (7-row diamond vs. 3-row rectangle):

```
┌───────┐
│   Go  │
└───┬───┘
    │
    │
    │
    │
    ▼
   /▔\
  /   \
 /     \
/  OK   \
 \     /
  \   /
   \▁/
```

Implemented (5-row diamond -- still a real taper, not a hexagon, but noticeably closer to the rectangle's own footprint):

```
┌─────┐
│  Go │
└──┬──┘
   │
   │
   │
   │
   ▼
  /▔\
 /   \
/ OK  \
 \   /
  \▁/
```

**Medium label** (`{Decision}`, 8 characters -- today's "long" tier since it's over the 6-character medium threshold):

Current (11-row diamond vs. 3-row rectangle):

```
┌───────────────┐
│       Go      │
└───────┬───────┘
        │
        │
        │
        │
        ▼
     /▔▔▔▔▔\
    /       \
   /         \
  /           \
 /             \
/   Decision    \
 \             /
  \           /
   \         /
    \       /
     \▁▁▁▁▁/
```

Implemented (9-row diamond -- the geometric minimum for an 8-character label without a gap in the taper, per the reassert-loop coupling in Design notes; not quite the 7 rows this issue originally hoped for, but still a real ~18% row reduction, and the diamond's own width dropped from 17 to 13 columns):

```
┌───────────┐
│     Go    │
└─────┬─────┘
      │
      │
      │
      │
      ▼
    /▔▔▔\
   /     \
  /       \
 /         \
/ Decision  \
 \         /
  \       /
   \     /
    \▁▁▁/
```

## Acceptance / verification

- `./run-tests.sh` green after regenerating every flowchart golden fixture under `tests/fixtures/mermaid_flowchart/` containing a diamond -- in practice exactly `shape_diamond`, `shape_diamond_lr_chain`, and `shapes_fallback` (the only fixtures with a diamond node; `diamond_merge` turns out to contain no actual diamonds despite its name, confirmed during VIEWMD-0036's independent review), each hand-diffed against its pre-change version to confirm the reduction is intentional (blank taper rows removed, no gaps introduced) and nothing else drifted.
- Visual check: render `docs/mermaid-examples.md`'s "Branching and labelled edges" and "Nested decisions" examples and confirm each diamond reads as noticeably more proportionate to its neighboring rectangles than before, while still visibly tapering to a point at top and bottom (not flat-sided).
- `test_diamond_chain_arrows_land_flush_on_both_sides` and `test_diamond_reaches_column_forced_wide_by_sibling_rectangle` (`tests/test_mermaid_flowchart.py`) -- the two existing regression tests for the taper-reaching-the-border invariant -- still pass unmodified against the new, smaller dimensions.
- Visual check: a diamond attached to LEFT/RIGHT edges (e.g. the "no"-branch arrow in "Branching and labelled edges") still attaches flush with no gap, confirming requirement 4 held under the new, smaller sizing.

## Peer review

- **Claude** (agent, independent review), 2026-08-07: PASS. Confirmed the two source diffs (`graph.py`'s `mid_row`/`mid_col` formula tightening, `canvas.py`'s matching `diamond_intrinsic_height`/`diamond_tip_half_width` changes) touch nothing else -- no other node shape, edge/routing logic, or `_draw_diamond`'s drawing mechanics. Confirmed by grepping every fixture `.mmd` for `{...}` syntax that `shape_diamond`, `shape_diamond_lr_chain`, and `shapes_fallback` are the only three containing a diamond (`diamond_merge` has none, as the issue claims); only their `.out` files changed, no `.mmd` source changed. Explicitly checked column positions of `/`/`\` per row in two regenerated fixtures and confirmed the taper has zero gaps, one column per row throughout. `test_diamond_chain_arrows_land_flush_on_both_sides` and `test_diamond_reaches_column_forced_wide_by_sibling_rectangle` are unmodified in the diff and still assert sizing-agnostic properties, both passing. Empirically re-verified the long-label-floor claim by rendering `{Authenticated?}` on both `develop` and this branch -- identical 13-row output on both, confirming genuine no-op rather than a silent regression. `.venv/bin/pytest` (324 tests) and `tests/test_mermaid_flowchart.py` (53 tests) pass; `./run-tests.sh`'s ruff failures are pre-existing and untouched by this branch (`git diff develop --stat -- poc/` empty). Rendered `docs/mermaid-examples.md` end-to-end: diamonds visibly smaller/more proportionate, arrows flush, no gaps. Noted one pre-existing rendering oddity in "Nested decisions" (a `yes`-labelled edge overlapping oddly near the second diamond), confirmed present identically on `develop` -- an unrelated pre-existing routing quirk, not a regression from this change. No stray unrelated changes.
- **George Moses** (maintainer), 2026-08-07: "commit and close" -- approved for landing.
