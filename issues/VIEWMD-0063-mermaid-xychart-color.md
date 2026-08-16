---
id: VIEWMD-0063
title: Color the bar and line datasets in Mermaid XY charts
status: in-progress
area: [render, mermaid]
effort: medium
created: 2026-08-16
updated: 2026-08-16
accepted_by: George Moses
accepted_at: 2026-08-16
commits: []
related: [VIEWMD-0048]
supersedes: []
changelog:
reason:
---

# Color the bar and line datasets in Mermaid XY charts

## Summary

Add `--color`-aware rendering to `viewmd/mermaid/xychart/renderer.py`: with color available, the
bar dataset's fill glyphs and the line dataset's step/staircase glyphs each get their own distinct
hue, the way every other colorable Mermaid diagram type (pie, quadrant, gantt, gitGraph, kanban)
already tints its own per-series/per-category elements. Without color, rendering is unchanged from
today (plain glyphs, no ANSI).

## Motivation / problem

VIEWMD-0048 shipped XY charts (`xychart-beta`/`xychart`) with color explicitly out of scope:
its Non-goals section states "viewmd's existing Mermaid renderers do not use ANSI color today,
and this issue does not introduce it" -- true when that issue was drafted, but no longer accurate
by the time it shipped, since VIEWMD-0043 (pie), VIEWMD-0047 (quadrant), VIEWMD-0032 (gantt), and
VIEWMD-0042 (gitGraph) all landed color support first. `viewmd/mermaid/__init__.py:render`'s own
dispatch already threads `color` through to those four renderers but not to `_render_xychart`
(`viewmd/mermaid/xychart/renderer.py:render` has no `color` parameter at all today) -- xychart is
now the only sizeable, actively-styled diagram type left without it, a visible inconsistency once
placed next to a colored pie or quadrant chart in the same document. In a combo chart especially
(bar + line on the same axes, e.g. `tests/fixtures/mermaid_xychart/sales_vs_target.mmd`), the two
datasets are today distinguished only by glyph shape (block fill vs. rounded step-line) -- color
would make the two series easier to tell apart at a glance, matching Mermaid's own upstream
`plotColorPalette` intent (referenced, and explicitly deferred, in VIEWMD-0048's Non-goals).

## Requirements

1. MUST add a `color: bool = False` parameter to `viewmd/mermaid/xychart/renderer.py:render`,
   threaded through from `viewmd/mermaid/__init__.py:render`'s dispatch to `_render_xychart`
   (currently `_render_xychart(chart, use_ascii=use_ascii, width=width)` -- add `color=color`),
   matching the pie/quadrant/gantt/gitGraph call sites already on that pattern.
2. MUST give the bar dataset's fill glyphs (`_bar_glyph`'s eighth-block characters) one fixed hue
   and the line dataset's step/staircase glyphs (`_build_line_grid`'s horizontal/vertical/corner
   characters) a different fixed hue, when both `color` is true and the chart has both a `bar` and
   a `line` dataset (a combo chart) -- reusing the categorical-palette convention
   `viewmd/mermaid/gantt/renderer.py:_status_color`/`viewmd/mermaid/gitgraph/renderer.py:_BRANCH_COLORS`
   already establish (a small fixed hex list, not a full theming system), applied via
   `viewmd/mermaid/grid/canvas.py:wrap_text_in_color` (the same primitive gantt's
   `_colorize_spans` and gitgraph already use to wrap ANSI around plain characters), not a new
   coloring mechanism.
3. MUST still color a bar-only or line-only chart's dataset with color available -- requirement 2's
   "two distinct hues" applies specifically to a combo chart; a single-dataset chart just gets that
   one dataset's hue (bar's or line's, whichever it has).
4. MUST leave axis lines, tick labels, category labels, and the chart title uncolored/plain even
   with `color` true -- matching quadrant's own posture (`viewmd/mermaid/quadrant/renderer.py`'s
   comment: "Title and axis labels stay plain/uncolored outside the box") -- color distinguishes
   the two datasets from each other, not the whole chart from plain text.
5. MUST NOT change any byte of output when `color` is false (the existing default, and every
   existing call site/test until this issue's own tests opt in) -- today's five golden fixtures in
   `tests/fixtures/mermaid_xychart/` MUST still match unchanged.
6. MUST NOT crash or change layout/geometry (column widths, row counts, glyph placement) -- color
   is applied as ANSI wrapping around glyphs already decided by today's (uncolored) layout logic,
   never something that affects `_plot_geometry`/`_snap_to_row`/`_build_bar_grid`/`_build_line_grid`
   sizing or placement decisions.
7. SHOULD pick colors that read distinctly from each other and from typical terminal backgrounds
   in both a light and dark terminal theme, consistent with how the existing categorical palettes
   (`_BRANCH_COLORS`, `_QUADRANT_COLORS`, gantt's per-status hues) were chosen -- not mandated to
   reuse the *same* two hex values as another diagram type, but should follow the same "legible in
   both themes" bar those palettes were held to.

## Non-goals

- Mermaid's actual `plotColorPalette`/`config:`/`themeVariables:` directive or front-matter block
  -- still inert extra text, same as every other Mermaid renderer in viewmd treats config blocks
  it doesn't act on; this issue adds two fixed built-in hues, not a way for a source file to
  choose its own.
- Multiple bar or multiple line series with per-series distinct colors -- VIEWMD-0048's own
  Non-goals already deferred multi-series support itself (still one bar + one line, max); this
  issue only colors within that same single-bar/single-line v1 scope.
- Any color for the plot's border/axis, title, or tick/category labels (requirement 4 explicitly
  keeps those plain) -- only the two datasets' own fill/line glyphs are in scope.
- ASCII-mode (`use_ascii=True`) color -- `use_ascii` and `color` are already independent knobs
  elsewhere in viewmd's Mermaid renderers (an ASCII-mode chart can still be colored, e.g. gantt);
  this issue doesn't change that relationship, but doesn't specifically re-verify it beyond
  requirement 6's "no layout change" either -- ordinary test coverage, not called out as its own
  requirement.

## Design notes / links

Builds directly on [VIEWMD-0048](../issues/archive/VIEWMD-0048-mermaid-xy-charts.md) (now
archived) -- see that issue's own Non-goals section for the "color is out of scope" statement this
issue reverses now that the color-support landscape has changed. Model the implementation on
`viewmd/mermaid/gantt/renderer.py`'s `_status_color`/`_colorize_spans` pair (a lookup function
mapping a domain concept -- there, task status; here, "bar" vs "line" -- to a fixed hex, plus a
helper that wraps only the spans that need color rather than re-walking the whole render), reusing
`viewmd/mermaid/grid/canvas.py:wrap_text_in_color` rather than introducing another ANSI-wrapping
helper. `_build_bar_grid`/`_build_line_grid` currently return `dict[float, list[str]]` (plain
characters per row); coloring happens at the point those grids' characters are joined into output
lines (or via a post-pass over the merged grid, distinguishing which glyphs came from which
dataset) -- exact mechanism (color-tagging cells during grid-building vs. a separate color mask)
is an implementation decision.

## Acceptance / verification

- `./run-tests.sh` green, including new `pytest` coverage for: a bar-only chart rendered with
  `color=True` producing ANSI-wrapped fill glyphs (requirement 3), a line-only chart likewise
  (requirement 3), a combo chart's bar and line glyphs wrapped in two *different* hex colors
  (requirement 2), axis/tick/category/title text remaining plain even with `color=True`
  (requirement 4), and `color=False` producing byte-identical output to today's five
  `tests/fixtures/mermaid_xychart/*.out` fixtures (requirement 5).
- Manual check: `./viewmd.sh docs/mermaid-xychart.md` (color auto-detected against a real
  terminal) and confirm the "Sales vs Target" combo chart's bars and line are visibly distinct
  colors, while `./viewmd.sh docs/mermaid-xychart.md --color never` renders identically to before
  this issue.

## Peer review

Not applicable; not yet built.
