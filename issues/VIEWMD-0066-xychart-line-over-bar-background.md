---
id: VIEWMD-0066
title: Color the bar's background where a combo chart's line crosses it
status: proposed
area: [render, mermaid]
effort: medium
created: 2026-08-16
updated: 2026-08-16
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0048, VIEWMD-0063, VIEWMD-0064]
supersedes: []
changelog:
reason:
---

# Color the bar's background where a combo chart's line crosses it

## Summary

In a combo chart (`bar` + `line` datasets on the same `xychart-beta`), wherever the `line`
dataset's glyph occupies the same cell a `bar` dataset's fill glyph would otherwise have drawn,
render that cell with the bar's own color as a true-color ANSI *background*, underneath the line
glyph's existing foreground color -- instead of today's behavior, where the line glyph fully
replaces the bar's color with nothing (the terminal's plain background), erasing all visual trace
of the bar for every cell the line passes through.

## Motivation / problem

Flagged by the maintainer looking at `tools/demo-pages/16-xychart.md`'s own "Sales vs Target"
combo chart (`bar [40, 60, 80, 100]`, `line [60, 80, 60, 120]`): at Q3, the line's value (60) sits
well inside Q3's bar (which reaches 80), and the line runs *horizontally* across the top of Q2's
falling edge and into Q3 at exactly that row, riding directly over roughly the bottom quarter of
Q3's bar. `_merge` (VIEWMD-0063's combo-chart rule, unchanged since) lets the line glyph win
outright wherever both datasets would draw the same cell, so every one of those crossed cells
prints as a plain `─`/`│`/corner glyph with no color behind it -- Q3's bar visually "breaks" where
the line passes through it, even though the bar data is still exactly as tall there as it is one
row above or below. Bars already fake a solid fill by coloring a *whole glyph* (`█` etc.) with a
foreground true-color escape (VIEWMD-0063/VIEWMD-0064); the line's thin corner/stem glyphs don't
fill a cell the same way, so simply keeping the line glyph's own foreground color (as today) can't
recover the missing bar color -- an actual background escape is needed underneath it.

## Requirements

1. MUST render a true-color ANSI background behind a `line`-dataset glyph cell, colored with that
   column's bar category color (`_bar_color(category_index)`, VIEWMD-0064's palette), whenever
   `color` is true, the chart has a `bar` dataset, and that specific cell is one where
   `_build_bar_grid` would have drawn a bar-fill glyph had `_merge` not let the line glyph
   overwrite it there.
2. MUST leave the line glyph's own existing foreground color (`_LINE_COLOR`, VIEWMD-0063)
   unchanged -- this issue adds a background only; the line itself is not recolored.
3. MUST NOT change any glyph placement -- `_merge`'s "the line dataset wins wherever both draw a
   cell" rule (VIEWMD-0063) stays exactly as is; this issue only adds color underneath a glyph
   that was already going to be there.
4. MUST NOT apply a background to a line-glyph cell that has no bar fill underneath it (e.g. a
   line-only chart, or a combo chart's line running above/below every bar's own height at that
   column) -- the background appears exactly where, and only where, a bar's own fill glyph would
   otherwise have been visible at that cell.
5. MUST NOT change any output when `color` is false, or when the chart has no `bar` dataset --
   both cases MUST stay byte-identical to today.
6. MUST NOT recolor a bar-fill cell that the line does *not* touch -- unaffected bar cells keep
   their existing foreground-only coloring (VIEWMD-0064), unchanged by this issue.
7. SHOULD reuse `viewmd/mermaid/grid/canvas.py:wrap_text_styled` (`fg=`/`bg=` in one escape/reset
   pair) for the combined line-over-bar cell, rather than nesting two separate wraps, matching how
   every other combined-attribute case in this codebase (quadrant chart backgrounds, kanban's
   underlined ticket field) already does it.

## Non-goals

- ASCII-mode output (`use_ascii=True`) -- ASCII glyphs (`#`/`+`) carry no color regardless of this
  issue; unaffected either way.
- Any change to the axis row's own line-glyph coloring (`_colorize_axis`) -- the axis baseline
  (`y_min`) sits below every level `_build_bar_grid` ever fills, so a bar's own fill glyph never
  reaches the axis row in the first place; nothing to add a background to there.
- A background behind bar-only cells the line never crosses (requirement 6) -- their existing
  foreground-only coloring is unchanged.
- Multiple bar or line series, or any other combo-chart layout change -- out of scope, unrelated
  to this issue (still deferred from VIEWMD-0048's own Non-goals).
- A user-configurable choice of whether this background applies (e.g. via
  [VIEWMD-0061](VIEWMD-0061-global-config-file.md)'s config file) -- fixed, built-in behavior,
  same posture as every other Mermaid renderer's coloring choice in viewmd today.

## Design notes / links

Follows [VIEWMD-0048](VIEWMD-0048-mermaid-xy-charts.md) (the renderer),
[VIEWMD-0063](VIEWMD-0063-mermaid-xychart-color.md) (bar/line coloring and the `_merge`
line-wins rule this issue leaves unchanged), and
[VIEWMD-0064](archive/VIEWMD-0064-xychart-per-bar-color-and-spacing.md) (per-bar categorical
palette, `_bar_color`) -- filed as its own issue rather than reopening any of them, per this
project's established pattern for a scope addition once shipped behavior surfaces a follow-up gap
(see e.g. VIEWMD-0015 spawning VIEWMD-0022 through VIEWMD-0028, or VIEWMD-0048 spawning
VIEWMD-0063 for color). `_merge` (`viewmd/mermaid/xychart/renderer.py`) already computes exactly
the information this issue needs -- it just discards it: the moment a line-grid cell overwrites a
bar-grid cell, the bar's original glyph is gone by the time `_plot_color_spans`/`_colorize_row`
run over the merged row. Implementing this likely means either (a) having `_merge` also return a
per-row "had bar fill here" boolean grid alongside the merged characters, or (b) passing the
un-merged `bar_grid[lv]` row into `_colorize_row`/`_plot_color_spans` directly so `classify()` can
check it per-column -- either way, `_plot_color_spans`'s `classify(i, ch)` needs to switch from
returning a single hex string to something that can carry both an `fg` and an optional `bg`, with
`apply_color_spans` (fg-only today) either extended or bypassed in favor of a new sibling built on
`wrap_text_styled` for just this renderer's line-over-bar runs.

### Proof of concept: real ANSI color

[`poc/xychart/line_bg_poc.py`](../poc/xychart/line_bg_poc.py) renders this exact chart
(`tools/demo-pages/16-xychart.md`'s own "Sales vs Target") two ways in real true-color ANSI: the
currently-shipped `render()` unmodified ("BEFORE"), and a reimplementation of just the
per-row colorizing step with this issue's proposed background rule added ("AFTER"), reusing the
real renderer's own `_build_bar_grid`/`_build_line_grid`/`_plot_geometry`/`_bar_color`/
`_LINE_COLOR` for every number and glyph -- only the coloring rule itself is new. Run it in a
true-color terminal:

```
python3 poc/xychart/line_bg_poc.py
```

### Mockup: which cells change

Markdown can't show real color, so the mockup below is the real (colorless) glyph layout --
identical before and after this issue, since requirement 3 leaves glyph placement untouched -- with
a `^` annotation row underneath marking exactly which cells gain the new background. Only Q3's
horizontal line segment at row 60 is affected in this chart: the line runs from Q2's falling edge
into Q3 at height 60, riding across the bottom of Q3's bar (which reaches 80) for its full leading
span before turning to climb toward Q4.

```
                     Sales vs Target

120 │                                       ╭────────────
115 │                                       │
110 │                                       │
105 │                                       │
100 │                                       │▄▄▄▄▄▄▄▄▄▄▄▄
 95 │                                       │████████████
 90 │                                       │████████████
 85 │                                       │████████████
 80 │             ╭────────────╮▄▄▄▄▄▄▄▄▄▄▄▄│████████████
 75 │             │            │████████████│████████████
 70 │             │            │████████████│████████████
 65 │             │            │████████████│████████████
 60 │─────────────╯▄▄▄▄▄▄▄▄▄▄▄▄╰────────────╯████████████
 55 │              ████████████ ████████████ ████████████
 50 │              ████████████ ████████████ ████████████
 45 │              ████████████ ████████████ ████████████
 40 │▄▄▄▄▄▄▄▄▄▄▄▄▄ ████████████ ████████████ ████████████
 35 │█████████████ ████████████ ████████████ ████████████
 30 │█████████████ ████████████ ████████████ ████████████
 25 │█████████████ ████████████ ████████████ ████████████
 20 │█████████████ ████████████ ████████████ ████████████
 15 │█████████████ ████████████ ████████████ ████████████
 10 │█████████████ ████████████ ████████████ ████████████
  5 │█████████████ ████████████ ████████████ ████████████
  0 └┬────────────┬────────────┬────────────┬────────────
    Q1           Q2           Q3           Q4
                                ^^^^^^^^^^^^
```

(Every other line cell in this chart -- the Q1-corner risers, the vertical stems in the gap
columns between bars, the climb from Q3 to the 120 peak at Q4 -- has no bar fill underneath it at
that row, so requirement 4 leaves those exactly as they render today, foreground-only.)

## Acceptance / verification

- `./run-tests.sh` green, including new `pytest` coverage for: a combo chart's line cell that has
  a bar fill underneath it producing a combined `fg`/`bg` escape via `wrap_text_styled`
  (requirement 1-2), a line cell with *no* bar fill underneath it (e.g. above every bar's height,
  or in a line-only chart) keeping today's foreground-only coloring with no background
  (requirement 4), `color=False` output byte-identical to today for a combo chart (requirement 5),
  a bar-only chart (no `line` dataset) byte-identical to today (requirement 5), and an unaffected
  bar-fill cell the line never touches keeping its existing foreground-only color (requirement 6).
- Manual check: `python3 poc/xychart/line_bg_poc.py` in a true-color terminal, confirming the
  "AFTER" render shows Q3's bar color continuing underneath the line's horizontal run at row 60,
  where "BEFORE" shows a plain-background gap; then `./viewmd.sh tools/demo-pages/16-xychart.md`
  against a real terminal to confirm the shipped combo chart matches.

## Peer review

Not applicable; not yet built.
