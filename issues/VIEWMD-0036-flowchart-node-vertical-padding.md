---
id: VIEWMD-0036
title: Remove the blank row above/below a flowchart node's label to match sequence/ER density
status: in-progress
area: [render, mermaid]
effort: medium
created: 2026-08-07
updated: 2026-08-07
accepted_by: George Moses
accepted_at: 2026-08-07
commits: []
related: [VIEWMD-0015, VIEWMD-0022]
supersedes: []
changelog:
reason:
---

# Remove the blank row above/below a flowchart node's label to match sequence/ER density

## Summary

Every flowchart node box (rectangle, round, stadium, circle, subroutine, cylinder -- everything except the tip-sized diamond) renders one blank interior row above and below its label, making it 2 rows taller than it needs to be. Sequence-diagram actor boxes and ER entity tables have no such padding. Remove the vertical padding so flowchart node boxes are exactly as tall as their label content (plus the border), matching the density already used elsewhere in viewmd's own Mermaid rendering.

## Motivation / problem

`viewmd/mermaid/flowchart/graph.py:368` sizes a node's interior row height as `n.label.content_height() + 2 * self.box_border_padding`, and `box_border_padding` (`viewmd/mermaid/flowchart/parser.py:16`, `BOX_BORDER_PADDING = 1`) is also reused as the *horizontal* label padding (`graph.py:367`). That single constant being shared between axes is why fixing the horizontal gap (correct: one space of breathing room either side of the label reads better) also inflates the vertical size (wrong: a blank row above and below a label adds no readability and only costs space). This is a faithful, byte-for-byte port of the upstream `github.com/AlexanderGrooff/mermaid-ascii` reference's own behavior (confirmed by running the reference binary directly against a two-node graph), not a viewmd-introduced bug -- so, per this project's porting convention, it's tracked as its own opt-in divergence rather than "fixed" silently inside a porting issue.

For a large flowchart (deeply nested decisions, long branching chains -- see `docs/mermaid-examples.md`'s "Nested decisions" example), 2 extra rows per node compounds quickly: a diagram with a dozen boxes in its longest vertical chain pays 24 rows of pure whitespace for no legibility benefit. Sequence diagrams (`viewmd/mermaid/sequence/renderer.py`) and ER diagrams (`viewmd/mermaid/er/renderer.py`) don't have this padding and read fine at that density; flowcharts should match.

## Requirements

1. MUST render a flowchart node's label immediately adjacent to its top and bottom border (no blank interior row above or below), for every node shape except diamond: rectangle, round, stadium, circle, subroutine, cylinder.
2. MUST NOT change horizontal label padding (the one space of breathing room either side of the label inside the border) -- this issue is vertical-only.
3. MUST NOT change diamond sizing/rendering (`_draw_diamond` / `canvas.diamond_height_for_width`) -- its tip-based height formula doesn't have this padding term to begin with.
4. MUST NOT change inter-node spacing: arrow/edge length between boxes (`padding_y`, the blank grid rows/columns between nodes) is a separate concern and stays as-is.
5. A multi-line label (`<br>`-separated, e.g. "Multi-line labels" in `docs/mermaid-examples.md`) MUST still render one row per line with no extra blank row *between* lines, matching how it already packs today -- only the padding rows *outside* the full label block (above the first line, below the last) are removed.
6. MUST regenerate every flowchart golden fixture under `tests/fixtures/mermaid_flowchart/` affected by this sizing change, and verify each byte-for-byte against a hand-checked expected render (not just "whatever the new code produces") per this project's fixture-diffing convention, since this touches shared grid/row-height sizing code that many fixtures share.

## Non-goals

- Diamond decision-node sizing (already tip-based, not part of this padding).
- Horizontal padding/width of any node shape.
- Edge/arrow length or routing between nodes.
- Subgraph border padding/label spacing (`Graph._layout_subgraphs`'s `subgraph_padding`/`subgraph_label_space`) -- separate constants, out of scope unless review finds they visually depend on this change.

## Design notes / links

The sizing formula to change is `viewmd/mermaid/flowchart/graph.py:368` (`rows = (1, n.label.content_height() + 2 * self.box_border_padding, 1)`), which currently reuses the same `box_border_padding` constant as the horizontal formula on the line above it (`graph.py:367`). The likely fix is splitting that shared constant into independent horizontal/vertical padding values (e.g. keep `box_border_padding` for `cols`, introduce a `box_vertical_padding = 0` for `rows`), then checking every other place `box_border_padding` is read (`graph.py:345` diamond `mid_col`, `graph.py:358` diamond `label_min` -- both horizontal, should be unaffected) to confirm nothing else silently depended on the vertical term. `_node_box_height` (`graph.py:620-621`) sums two grid row-heights per node and will need re-checking once the vertical term drops, particularly for nodes sharing a grid row with a taller sibling (a diamond, or a multi-line-label box) -- see AGENTS.md's note on VIEWMD-0022's diamond/rectangle row-sharing bug for the kind of cross-node interaction to watch for here. `draw_box`/`_place_label` (`viewmd/mermaid/grid/canvas.py:244`) center the label within the `height` passed in, so once the caller passes a smaller height for single/multi-line labels, no separate change should be needed there -- but verify the centering math doesn't leave a stray blank row for even/odd label-height mismatches.

### Mockups: current vs. proposed

**Node-shape row** (`docs/mermaid-examples.md`, "Node shapes" -- reference binary output, confirmed byte-for-byte with today's viewmd):

Current:

```
┌───────────┐     ╭───────╮     (─────────)     ╔════════╗
│           │     │       │     (         )     ║        ║
│ Rectangle ├────►│ Round ├────►( Stadium ├────►║ Circle ║
│           │     │       │     (         )     ║        ║
└───────────┘     ╰───────╯     (─────────)     ╚════════╝
```

Proposed:

```
┌───────────┐     ╭───────╮     (─────────)     ╔════════╗
│ Rectangle ├────►│ Round ├────►( Stadium ├────►║ Circle ║
└───────────┘     ╰───────╯     (─────────)     ╚════════╝
```

**Two-node chain** (`graph TD` / `A[Start] --> B[End]`):

Current:

```
┌───────┐
│       │
│ Start │
│       │
└───┬───┘
    │
    │
    │
    │
    ▼
┌───────┐
│       │
│  End  │
│       │
└───────┘
```

Proposed (2 rows saved per box, edge length between them unchanged -- non-goal 4):

```
┌───────┐
│ Start │
└───┬───┘
    │
    │
    │
    │
    ▼
┌───────┐
│  End  │
└───────┘
```

**Multi-line label** (`docs/mermaid-examples.md`, "Multi-line labels"):

Current:

```
┌──────────┐
│          │
│ Line one │
│          │
│ Line two │
│          │
└─────┬────┘
```

Proposed (only the padding *outside* the label block is removed; the existing blank row *between* "Line one" and "Line two" is a separate mechanism -- `LABEL_LINE_GAP` in `viewmd/mermaid/grid/label.py`, also a faithful upstream port -- and stays exactly as it is today, per requirement 5):

```
┌──────────┐
│ Line one │
│          │
│ Line two │
└─────┬────┘
```

**Existing precedent** for the target density, already shipping today, unchanged by this issue -- sequence-diagram actor box (`viewmd/mermaid/sequence/renderer.py`):

```
┌───────┐
│ Alice │
└───┬───┘
```

and ER entity header (`viewmd/mermaid/er/renderer.py`):

```
┌──────────────────────────┐
│         CUSTOMER         │
├────────┬────────────┬────┤
```

## Acceptance / verification

- `./run-tests.sh` green after regenerating every affected fixture under `tests/fixtures/mermaid_flowchart/`.
- Each regenerated fixture hand-diffed against its pre-change version to confirm only the vertical padding rows were removed -- no unintended width/horizontal-padding drift (per this project's "golden fixture that gets edited to match new output isn't proof of no regression" rule).
- Visual check: render `docs/mermaid-examples.md` through viewmd and confirm every non-diamond node shape (rectangle, round, stadium, circle, subroutine, cylinder) matches its "Proposed" mockup above, diamonds are visually unchanged, and multi-line labels still pack their lines with no blank row between them.
- Visual check: a flowchart with a node sharing a grid row with a diamond or a multi-line-label node (e.g. "Nested decisions" or "Multi-line decision label" in `docs/mermaid-examples.md`) still renders with correct alignment -- no stray blank/missing row from the row-height sharing interaction called out in Design notes.

## Peer review

- **Claude** (agent, independent review), 2026-08-07: PASS. Confirmed the one-line fix in `viewmd/mermaid/flowchart/graph.py`'s `_set_column_width` (non-diamond `rows` dropped `+ 2 * self.box_border_padding`, `cols`/horizontal padding and the diamond branch untouched). Diffed all 46 regenerated fixtures under `tests/fixtures/mermaid_flowchart/` and confirmed every changed file is a pure removal of blank interior rows -- zero added lines, no width/content drift, no wrong rows removed. Confirmed `multiline_label.*.out` keeps its `LABEL_LINE_GAP` blank row *between* "Line one"/"Line two", only the outer padding is gone. Confirmed diamond-only fixtures (`shape_diamond.*.out`, `shape_diamond_lr_chain.*.out`) are byte-for-byte unchanged, and a mixed-shape fixture (`shapes_fallback`) shows its diamond unchanged while sibling rectangles lost padding. `.venv/bin/pytest tests/test_mermaid_flowchart.py -q` (53 passed) and full `./run-tests.sh` (324 passed) green; the script's overall `FAILED` is pre-existing unrelated ruff noise in `poc/`, confirmed untouched by this diff. Rendered `docs/mermaid-examples.md` end-to-end: every non-diamond shape matches the issue's mockups, row-sharing with a taller diamond sibling still behaves as documented (pre-existing, not a regression), subgraphs/self-loops/obstacle-routing/classdef sections unaffected. No stray unrelated changes.
- **George Moses** (maintainer), 2026-08-07: "commit and close it out" -- approved for landing.
