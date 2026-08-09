---
id: VIEWMD-0039
title: Render Mermaid flowchart parallelogram/input-output node shapes
status: in-progress
area: [render, mermaid]
effort: medium
created: 2026-08-08
updated: 2026-08-09
accepted_by: George Moses
accepted_at: 2026-08-08
commits: []
related: [VIEWMD-0022, VIEWMD-0038]
supersedes: []
changelog:
reason:
---

# Render Mermaid flowchart parallelogram/input-output node shapes

## Summary

Add two more `NodeShape` variants -- `A[/Text/]` (parallelogram) and `A[\Text\]` (parallelogram,
mirrored) -- to the flowchart node-shape set VIEWMD-0022 established, following the requester's own
worked example. Unlike every shape added so far (VIEWMD-0022's `round`/`stadium`/`circle`/
`subroutine`/`cylinder`, VIEWMD-0038's redesigned `diamond`), a parallelogram is not a uniform
rectangular box with distinct border glyphs -- each row is horizontally offset from the one above
it by exactly one column, so the shape is genuinely slanted, closer in kind to the *pre*-VIEWMD-0038
tapered diamond than to `draw_box`'s current flat-border mechanism.

## Motivation / problem

Mermaid's flowchart grammar defines `[/Text/]` and `[\Text\]` as the "parallelogram" input/output
shape (and its mirror), commonly used for I/O steps in a flowchart. viewmd's `NodeShape` enum
(`viewmd/mermaid/flowchart/parser.py:31`) doesn't recognize either delimiter pair today, so both
fall through `parse_node`'s shape-matching loop (`parser.py:185`) to the bare-label rectangle
fallback -- the diagram parses, but neither shape nor its distinguishing slant renders.

## Requirements

1. MUST recognize `A[/Text/]` as a new `NodeShape.PARALLELOGRAM` and `A[\Text\]` as a new
   `NodeShape.PARALLELOGRAM_ALT`, added to `_SHAPE_DELIMITERS` (`parser.py:47`) ordered before the
   plain `[`/`]` `RECTANGLE` entry (both new delimiters end in `]`, so `RECTANGLE`'s bare
   `trimmed.endswith("]")` check would otherwise shadow them, the same reason `SUBROUTINE`/
   `CYLINDER` are already ordered ahead of it).
2. MUST render each row of the box -- both border rows and every content row -- shifted
   horizontally by one column from the row directly above it: `PARALLELOGRAM` shifts left going
   down (top row rightmost, matching `/`'s own lean), `PARALLELOGRAM_ALT` shifts right going down
   (top row leftmost, matching `\`'s own lean). Verified against the requester's own example
   (reproduced byte-for-byte below) -- do not re-derive the slant direction independently of it.
3. MUST use `/` as both the left and right border glyph on every row of `PARALLELOGRAM`, and `\` for
   `PARALLELOGRAM_ALT`, in both the `UNICODE` and `ASCII` charsets (no substitute glyph needed --
   unlike diamond's `◇`, `/` and `\` are already ASCII-safe, ported as-is per the requester's
   example, which uses them directly in the "source" block).
4. MUST size the box like every other rectangle-family shape, ignoring the slant: `label_lines + 2`
   rows, and a content-column width of `2 * box_border_padding + label.width` (the same formula
   `graph._set_column_width`'s existing `else` branch already uses, `graph.py:319-323`) -- the slant
   is a pure horizontal *offset* per row, not a change to how tall or how many content-columns wide
   the label itself needs.
5. MUST fill each border row's dashes (`─` in `UNICODE`, `-` in `ASCII`) between that row's own
   (shifted) left and right glyph, and MUST center each content line within that row's own
   (shifted) span -- not the box's unshifted nominal span -- so the label reads upright rather than
   staircasing across rows.
6. MUST widen the node's own drawn footprint to fit the accumulated shift: a box with `n` total rows
   (top border + content rows + bottom border) needs `n - 1` extra columns of width beyond the
   unshifted `content_width + 2`, since the top and bottom rows are `n - 1` columns apart
   horizontally. This is an intentional, self-contained coupling between a parallelogram's own
   height and its own width footprint (more label lines -> taller -> wider) -- distinct from, and
   not a reintroduction of, the *sibling*-column reach-coupling bug class VIEWMD-0022/VIEWMD-0037
   documented and VIEWMD-0038 eliminated for `diamond`: a parallelogram's footprint still depends
   only on its own label, never on a sibling's width.
7. MUST attach an edge at a `PARALLELOGRAM`/`PARALLELOGRAM_ALT` node's LEFT/RIGHT side flush against
   that row's own (shifted) border glyph, and at its UP/DOWN side flush against the horizontal
   midpoint of that (shifted) border row's dash run -- the same flush-attachment guarantee every
   other shape already has (VIEWMD-0038 req. 8's carried-forward UP/DOWN/LEFT/RIGHT convention),
   not a fixed offset that happens to work only for the single-line-label case in the worked
   example.
8. MUST NOT change any existing shape (`rectangle`, `round`, `stadium`, `circle`, `subroutine`,
   `cylinder`, `diamond`) -- this issue only adds two new `NodeShape` values.

## Non-goals

- Mermaid's *trapezoid* shapes (`[/Text\]`, `[\Text/]`, mixed-direction delimiters where the two
  slants point toward or away from each other) -- a different shape family, not requested here and
  not implied by the requester's example, which uses the same slant direction on both sides of each
  node.
- A `PARALLELOGRAM`/`PARALLELOGRAM_ALT` node sharing a grid column with a much wider sibling (the
  VIEWMD-0022-diamond-style "reach" interaction) -- req. 6 already establishes this shape's width
  never depends on a sibling's width, so there is no analogous case to guard; not re-litigated here.
- Multi-line (`<br>`) label verification beyond confirming req. 4/5/7's formulas hold for it --
  no new packing behavior is introduced (same `line_gap`/content-row convention every rectangle-
  family shape already uses since VIEWMD-0036/VIEWMD-0038).

## Design notes / links

**Requester's worked example** (verbatim; the byte-for-byte target for req. 2/3):

Source:

```
graph LR
    A[/Parallelogram/] --> B[\Alt Para\]
```

Rendered:

```
  /───────────────/    \───────────\ 
 / Parallelogram /─────►\ Alt Para  \
/───────────────/        \───────────\
```

Column-indexed, this confirms: both shapes are exactly 3 rows tall (1 top border + 1 content + 1
bottom border, matching `label_lines + 2`); each shape's border-glyph columns are the same distance
apart on every row (16 for `PARALLELOGRAM`, 12 for `PARALLELOGRAM_ALT` -- the *width* doesn't change
row to row, only the row's horizontal *position* does); `PARALLELOGRAM`'s glyph columns are
`{2, 18}` / `{1, 17}` / `{0, 16}` top-to-bottom (shift -1 per row going down); `PARALLELOGRAM_ALT`'s
are `{23, 35}` / `{24, 36}` / `{25, 37}` (shift +1 per row going down). `PARALLELOGRAM`'s
content-column width (15, between the `/` pair) matches req. 4's `2 * box_border_padding(1) +
label.width` exactly (`"Parallelogram"` is 13 wide). `PARALLELOGRAM_ALT`'s does not quite --
`"Alt Para"` is 8 wide (`2*1+8=10`), one narrower than the example's actual 11-wide content span
(asymmetric: 1 leading space, 2 trailing, versus `PARALLELOGRAM`'s evenly-split 1-and-1) -- almost
certainly the example was hand-typed rather than generated from a formula. Follow req. 4's formula
(matching every other shape, evenly split padding) rather than reproducing this specific asymmetry;
what matters is the *slant* (req. 2/3), not pixel-matching a hand-typed illustration's padding.

**This needs a dedicated drawing routine, not `canvas.draw_box`.** `draw_box`'s border-fill loops
(`canvas.py:267-280`) write every row's left/right glyph at the *same* local x (`from_.x`/`to.x`);
a parallelogram needs a *different* local x per row. The pre-VIEWMD-0038 `_draw_diamond` (removed by
that issue, recoverable from history if useful as a reference for the per-row-offset loop shape, but
not otherwise reusable -- its geometry was a symmetric V-taper, this shape's is a constant-slope
diagonal) and `graph.py`'s now-removed diamond-specific `_path_grid_to_drawing` override (also
VIEWMD-0038, same history) are the closest prior art for "a shape whose LEFT/RIGHT/UP/DOWN
attachment coordinates aren't simply the shared grid cell's center" -- expect this issue to need a
similar per-shape coordinate override, not a diamond-style marker glyph (there is no center marker
here at all, per req. 3/5).

**Where the extra width (req. 6) needs to be reserved**: `graph._set_column_width`
(`graph.py:310-345`) sizes `cols`/`rows` per node and writes them into the shared
`self.column_width`/`self.row_height` grid dicts; a parallelogram's `cols` entry needs the `n - 1`
extra-column term added on top of the existing `2 * box_border_padding + label.width` formula (req.
4), analogous to how the pre-VIEWMD-0038 diamond branch added its own extra terms there (now
removed) -- but self-contained (keyed only off this node's own `label_lines`), not the old branch's
sibling-reach logic.

## Acceptance / verification

- Render the requester's exact `graph LR` example above (`./viewmd.sh` or a one-off `.mmd` file) and
  confirm the slant direction, row count, and per-row shift match the worked example exactly (per
  design notes, the requester's example's own padding is slightly asymmetric on
  `PARALLELOGRAM_ALT` and not the byte-for-byte target -- req. 4's formula is).
- New fixtures under `tests/fixtures/mermaid_flowchart/` for both shapes standalone, both shapes in
  an LR chain like the worked example, a multi-line (`<br>`) label on each, and both `UNICODE` and
  `ASCII` charsets.
- Visual check: an edge attaching to a `PARALLELOGRAM`/`PARALLELOGRAM_ALT` node's LEFT/RIGHT/UP/DOWN
  side attaches flush, no gap, matching every other shape's existing guarantee.
- Visual check: render `docs/mermaid-examples.md`'s "Node shapes" section with both new shapes added
  alongside the existing six, confirm no regression to any of them (req. 8).
- `./run-tests.sh` green.

## Peer review

- **Claude (agent)**, 2026-08-09: PASS. Verified against requirements: `PARALLELOGRAM`/
  `PARALLELOGRAM_ALT` added to `NodeShape` and ordered ahead of `RECTANGLE` in
  `_SHAPE_DELIMITERS` (req. 1); `_draw_parallelogram` shifts each row one column per the
  requester's slant direction, `/` and `\` used as border glyphs in both charsets (req. 2/3);
  sizing follows the standard rectangle-family formula independent of the slant (req. 4); border
  dashes and label centering computed per-row against that row's own shifted span (req. 5); extra
  width reserved self-contained off the node's own `label_lines`, not sibling-coupled
  (req. 6, `graph.py` diff); `_path_grid_to_drawing` overrides LEFT/RIGHT/UP/DOWN/MIDDLE
  attachment to the row-shifted border via a shared x-anchor, confirmed flush with no gap in the
  `_lr_chain`/`_td_chain`/`_multiline` fixtures (req. 7); no other `NodeShape` touched (req. 8).
  Rendered the requester's own worked example directly (`.venv/bin/python -c "from viewmd.mermaid
  import render; ..."`) -- slant direction and row count match exactly; the one difference
  (`PARALLELOGRAM_ALT`'s padding) is the asymmetric hand-typed padding the issue's design notes
  already flagged as not the byte-for-byte target. `pytest` is green (334 passed, including 10
  new parallelogram fixture cases, unicode+ascii). `ruff`/`tools/issues.py --check` fail via
  `run-tests.sh`, but only on pre-existing `poc/kanban/kanban_poc.py` /
  `poc/timeline/timeline_poc.py` lint errors already present on `develop` (confirmed
  `git show develop:poc/kanban/kanban_poc.py` has the same file) -- unrelated to this issue's
  diff, which touches only `viewmd/mermaid/flowchart/{parser,graph}.py`,
  `viewmd/mermaid/grid/canvas.py`, `docs/mermaid-examples.md`, and new fixtures. No findings.
- **George Moses (maintainer)**, 2026-08-09: tested and accepted.
