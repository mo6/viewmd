---
id: VIEWMD-0064
title: Give each XY-chart bar its own color and a gap between bars
status: in-progress
area: [render, mermaid]
effort: medium
created: 2026-08-16
updated: 2026-08-16
accepted_by: George Moses
accepted_at: 2026-08-16
commits: []
related: [VIEWMD-0048, VIEWMD-0063]
supersedes: []
changelog:
reason:
---

# Give each XY-chart bar its own color and a gap between bars

## Summary

Two related bar-only legibility changes to `viewmd/mermaid/xychart/renderer.py`'s `bar` dataset,
flagged by the maintainer while reviewing VIEWMD-0063 (which colored the bar dataset as a whole
one fixed hue, and the line dataset a different fixed hue -- unchanged by this issue): (1) give
each bar its own color from a small categorical palette, cycling by category index, instead of
every bar sharing VIEWMD-0063's single `_BAR_COLOR`; (2) leave a one-column gap between adjacent
bars' columns so neighboring bars read as visually distinct shapes instead of one solid block.

## Motivation / problem

VIEWMD-0063 (`_BAR_COLOR = "3987e5"`) deliberately gives the whole bar dataset one hue, matching
what that issue actually asked for (bar vs. line, not bar-vs-bar). Looking at the shipped result,
the maintainer noted that with every bar the same color, adjacent bars in a multi-category chart
(e.g. `tests/fixtures/mermaid_xychart/sales.mmd`'s four quarters) visually blend into each other,
especially at typical terminal widths where `col_width` (`_plot_geometry`) is only a few columns
wide -- there's nothing today distinguishing "bar 1" from "bar 2" beyond their tick-row height and
position, both of which take a moment to read. Two independent, additive fixes address that:
per-bar coloring (borrowing the same categorical-palette convention already used for pie slices,
gitGraph branches, and kanban's ticket/assignee hues) and a visible gap between bars (the same
"give shapes breathing room" instinct behind, e.g., a normal bar-chart library's inter-bar
padding), so a reader's eye separates bars without needing to trace their outlines first.

## Requirements

1. MUST introduce a small categorical color palette for the bar dataset (e.g. 6-8 fixed hex
   values, following `viewmd/mermaid/pie/renderer.py:_SLICE_COLORS`'s or
   `viewmd/mermaid/kanban/renderer.py:_CATEGORICAL`'s size/shape), and color category `i`'s bar
   with `palette[i % len(palette)]` when `color` is true, replacing VIEWMD-0063's single
   `_BAR_COLOR` constant for the bar dataset specifically.
2. MUST leave the line dataset's coloring exactly as VIEWMD-0063 shipped it (one fixed hue for the
   whole line, distinct from every bar color) -- this issue only changes how the *bar* dataset is
   colored, not the line dataset or the bar-vs-line distinction VIEWMD-0063 established.
3. MUST pick the per-bar palette so that no two adjacent categories' colors are identical when the
   palette wraps (i.e. `len(palette)` should not evenly divide typical small category counts in a
   way that repeats immediately next to itself) -- or otherwise handle the wrap-adjacency case so
   two neighboring bars are never accidentally the same color merely because the palette cycled.
4. MUST leave a fixed one-column gap between each category's bar columns (i.e. a bar's fill no
   longer spans its entire `col_width`-wide column, but `col_width` minus the trailing gap
   column), visually separating adjacent bars regardless of whether `color` is enabled -- this is
   a layout change, not a color-only change, so it MUST also improve legibility with color off.
5. MUST NOT let the gap column shrink a bar to zero width -- `_plot_geometry`'s `_MIN_COL` (or an
   adjusted floor accounting for the new gap) MUST still guarantee at least one fillable column per
   bar; widen the minimum column width if necessary rather than let a bar disappear.
6. MUST NOT change the line dataset's rendering, its own column positioning (a line point still
   plots at the same category-column center it does today), or a combo chart's line-over-bar
   layering -- only the bar dataset's own column width/gap changes.
7. MUST NOT change any byte of output for a chart with no `bar` dataset (line-only charts
   unaffected by requirement 4's gap, which is bar-specific).
8. SHOULD keep `_plot_geometry`'s existing width/aspect-ratio math (VIEWMD-0048's requirement 8,
   already adjusted once for cell-aspect and again for nice tick steps) working with the new
   narrower effective bar width -- exact accounting (whether the gap counts against `col_width` or
   is added on top, growing `plot_w` slightly) is an implementation decision, but the plot MUST
   still land in `_plot_geometry`'s documented `[50%, 100%]`-of-`width` band afterward.

## Non-goals

- Coloring the line dataset per-point (matching VIEWMD-0063's own already-settled "line dataset:
  one hue" decision) -- out of scope, see requirement 2.
- A gap between line-dataset points/segments, or any other line-rendering change -- only the bar
  dataset's spacing changes (requirement 6).
- A user-configurable palette or gap width (e.g. via a future config file per
  [VIEWMD-0061](VIEWMD-0061-global-config-file.md)) -- both are fixed, built-in choices, same
  posture as every other Mermaid renderer's categorical palette in viewmd today.
- Per-bar custom colors from the Mermaid source itself (Mermaid's `xychart-beta` grammar has no
  such per-bar-color syntax to parse in the first place) -- not applicable.
- Multiple bar series (still deferred from VIEWMD-0048's own Non-goals) -- this issue's per-bar
  coloring is about coloring each *category*'s single bar distinctly, not multiple series.

## Design notes / links

Follows directly from [VIEWMD-0063](VIEWMD-0063-mermaid-xychart-color.md) (color) and
[VIEWMD-0048](VIEWMD-0048-mermaid-xy-charts.md) (the renderer itself) -- filed as its own issue
rather than reopening either, per this project's own established pattern (VIEWMD-0015 spawning
VIEWMD-0022 through VIEWMD-0028 for post-port divergences; VIEWMD-0048 spawning VIEWMD-0063 for
color once that landscape changed) of a scope addition getting a new issue instead of expanding an
already-shipped one after the fact. `_build_bar_grid` (`viewmd/mermaid/xychart/renderer.py`) is
where a bar's column range (`col0, col1 = i * col_width, (i + 1) * col_width`) is decided today;
requirement 4's gap narrows that per-category fill range, and requirement 1's per-bar color needs
`_plot_color_spans`/`_colorize_row` (VIEWMD-0063) to know which category index a given plot column
belongs to, not just "is this a bar glyph or a line glyph" as they do today -- likely means
`_build_bar_grid` needs to record (or `_plot_color_spans` needs to derive from `col_width`) each
colored span's category index, not just its dataset kind.

### Mockup: before / after, `tests/fixtures/mermaid_xychart/sales.mmd`

Markdown can't show real ANSI color, so the "after" mockup below stands in each bar's color with a different fill character (`░`/`▒`/`▓`/`█`) instead -- the real renderer keeps using the same eighth-block glyphs (`▁`-`█`) for every bar regardless of color, per-bar color is a `wrap_text_in_color`-style ANSI wrap around those glyphs (VIEWMD-0063's own mechanism), not a new glyph set. The eighth-block partial-top row (VIEWMD-0048 requirement 7) is also simplified away here to keep the mockup readable -- rounded to the nearest whole row instead; unaffected by this issue either way.

Today (VIEWMD-0063, shipped): one hue for the whole bar dataset, bars flush against each other:

```
100 │
 95 │
 90 │                              ▄▄▄▄▄▄▄▄▄▄
 85 │                              ██████████
 80 │                              ██████████
 75 │                              ██████████
 70 │                    ▄▄▄▄▄▄▄▄▄▄██████████
 65 │                    ████████████████████
 60 │                    ████████████████████
 55 │          ▄▄▄▄▄▄▄▄▄▄████████████████████
 50 │          ██████████████████████████████
 45 │          ██████████████████████████████
 40 │▄▄▄▄▄▄▄▄▄▄██████████████████████████████
 35 │████████████████████████████████████████
 30 │████████████████████████████████████████
 25 │████████████████████████████████████████
 20 │████████████████████████████████████████
 15 │████████████████████████████████████████
 10 │████████████████████████████████████████
  5 │████████████████████████████████████████
  0 └┬─────────┬─────────┬─────────┬─────────
    Q1        Q2        Q3        Q4
```

After this issue: each bar its own color (stand-in glyph here) and a one-column gap (requirement 4) separates every bar from its neighbor, including where two full-height bars would otherwise touch (e.g. Q3/Q4 above, rows 55-70):

```
100 │
 95 │
 90 │                              █████████
 85 │                              █████████
 80 │                              █████████
 75 │                              █████████
 70 │                    ▓▓▓▓▓▓▓▓▓ █████████
 65 │                    ▓▓▓▓▓▓▓▓▓ █████████
 60 │                    ▓▓▓▓▓▓▓▓▓ █████████
 55 │          ▒▒▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▓▓ █████████
 50 │          ▒▒▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▓▓ █████████
 45 │          ▒▒▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▓▓ █████████
 40 │░░░░░░░░░ ▒▒▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▓▓ █████████
 35 │░░░░░░░░░ ▒▒▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▓▓ █████████
 30 │░░░░░░░░░ ▒▒▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▓▓ █████████
 25 │░░░░░░░░░ ▒▒▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▓▓ █████████
 20 │░░░░░░░░░ ▒▒▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▓▓ █████████
 15 │░░░░░░░░░ ▒▒▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▓▓ █████████
 10 │░░░░░░░░░ ▒▒▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▓▓ █████████
  5 │░░░░░░░░░ ▒▒▒▒▒▒▒▒▒ ▓▓▓▓▓▓▓▓▓ █████████
  0 └┬─────────┬─────────┬─────────┬─────────
    Q1        Q2        Q3        Q4
```

(`░`=Q1, `▒`=Q2, `▓`=Q3, `█`=Q4 above -- four different palette entries per requirement 1, not four different glyph shapes; a real render draws every bar with the same block glyphs, just wrapped in each category's own hex per `wrap_text_in_color`. Axis line and tick/category labels are deliberately left contiguous/unchanged -- the gap is a bar-fill-only change, requirement 4.)

## Acceptance / verification

- `./run-tests.sh` green, including new `pytest` coverage for: a multi-category bar chart with
  `color=True` producing a different hex per bar (requirement 1), no two *adjacent* bars sharing a
  color even when the category count exceeds the palette size (requirement 3), a visible blank
  gap column between adjacent bars' fill with `color` either on or off (requirement 4), a
  single-category chart still rendering a fillable bar (requirement 5), the line dataset's own
  hue/positioning unchanged in a combo chart (requirement 2, 6), a line-only chart's output
  byte-identical to before this issue (requirement 7), and `_plot_geometry`'s existing
  width-bound tests (`test_plot_width_at_fifty_percent_floor` etc.) still passing against the
  updated column-width accounting (requirement 8).
- Manual check: `./viewmd.sh docs/mermaid-xychart.md` against a real terminal and confirm the
  "Sales" chart's four bars are each a different color with visible gaps between them, and that
  the "Sales vs Target" combo chart's line is still one consistent hue, unchanged in position.

## Peer review

- **code-review agent** (agent), 2026-08-16: 2 findings at high effort, both confirmed by direct
  differential testing against the pre-VIEWMD-0064 renderer (commit `74404b1`); fixes pending.
  1. **Confirmed, high severity -- requirement 5 violated for combo charts at `_MIN_COL`.** At
     `col_width == _MIN_COL == 2` a bar has exactly one fillable column
     (`fill_w = col_width - _BAR_GAP == 1`). Combo charts have always let the line dataset win
     wherever both draw a cell (`_merge`, VIEWMD-0063, unchanged here); before this issue a bar
     had two columns to lose one to the line and still show something, but with only one
     fillable column left, a line corner/vertical-stem glyph landing on that exact column erases
     the bar's data entirely, with no visual trace it was ever there. Reproduced in a scratch doc
     (10-category combo chart, every bar at the same max value, alternating line, `--width 20`)
     -- every category except the first showed zero bar glyphs at any row. **Fixed**: reserving
     the gap as each category's *leading* column instead of its trailing one (`_build_bar_grid`)
     -- `_build_line_grid`'s own corner/vertical-stem glyph for category `i` (`i > 0`) only ever
     lands at that category's leading column (`i * col_width`), never elsewhere in its span, so
     putting the gap there keeps the fill out of the one column a line dataset can overwrite. The
     first category has no left neighbor to share a gap with, so it fills its whole span (no
     leading gap); the last category ends up flush against the plot's right edge -- which also
     fixes finding 2 below as a side effect, since that's exactly what the mockup already showed.
     New regression test `test_combo_chart_bar_survives_line_peak_at_minimum_column_width`.
  2. **Confirmed, low severity -- trailing gap after the last bar didn't match the issue's own
     mockup.** The "after" mockup above shows the last category's bar flush against the plot's
     right edge with no trailing gap column, but the shipped implementation (and
     `test_gap_between_adjacent_bars_with_color_on_or_off`'s own expectation,
     `("█"*9+" ")*4`) left a blank column after every bar including the last. **Fixed** by the
     same leading-gap change as finding 1 -- the last bar is flush right with no trailing gap
     again, matching the mockup byte-for-byte (`sales.out` regenerated).
- **George Moses** (maintainer), 2026-08-16: "commit and close it out" -- approved to land.
