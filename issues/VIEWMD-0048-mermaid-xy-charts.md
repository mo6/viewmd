---
id: VIEWMD-0048
title: Render Mermaid XY charts
status: proposed
area: [render, mermaid]
effort: high
created: 2026-08-09
updated: 2026-08-15
accepted_by:
accepted_at:
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Render Mermaid XY charts

## Summary

Add a Mermaid diagram type -- `xychart-beta` -- alongside the existing flowchart, sequence, and ER
renderers (`viewmd/mermaid/{flowchart,sequence,er}/`) and the diagram types proposed in
[VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md) through
[VIEWMD-0042](VIEWMD-0042-mermaid-gitgraph-diagrams.md). A Mermaid XY chart
(https://mermaid.js.org/syntax/xyChart.html) plots one or more bar and/or line datasets against a
shared category x-axis and a numeric y-axis, optionally in a horizontal-bar orientation. Checked
against both `mermaid.js.org/syntax/xyChart.html` and `mermaid.ai/open-source/syntax/xyChart.html`
(2026-08-15); see Non-goals for the syntax those references cover that this issue does not.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `xychart-beta` fence
today -- it falls through every `_is_*_diagram` sniff. Of the eight diagram types termaid supports
that viewmd does not yet track, this is the largest in termaid's own implementation
(`src/termaid/{parser,renderer,model}/xychart.py`, ~520 lines combined, termaid's biggest single
diagram module) because it combines several independent features: axis-range scaling (with or
without an explicit `y-axis ... -->` range, requiring auto-scaling from the data when omitted),
two independently-rendered mark types (bar and line, block-character-height bars per
`viewmd/mermaid/grid/canvas.py`'s existing `use_ascii` glyph-fallback convention), a combo mode
where both are overlaid on the same axes, and a horizontal-orientation transpose.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with either `xychart-beta` or the bare
   `xychart` alias (Mermaid's newer, non-`-beta` spelling of the same diagram type) via
   `viewmd/mermaid/xychart/parser.py:sniff`, following the `sniff`/`parse`/`render` module shape
   already used by the other diagram packages, and wire it into `viewmd/mermaid/__init__.py:render`
   alongside the existing sniffs. A trailing ` horizontal` keyword on that line MUST be tolerated
   (parsed and ignored -- see requirement 6, v1 always renders the same bottom-up layout whether or
   not the keyword is present).
2. MUST parse an optional `title "<text>"` line, rendered above the chart.
3. MUST parse `x-axis [<cat1>, <cat2>, ...]` (bare category list) and its optional titled form
   `x-axis "<label>" [<cat1>, <cat2>, ...]`; category count sets the number of data points every
   dataset below MUST supply.
4. MUST parse `y-axis <low> --> <high>` and its optional titled form
   `y-axis "<label>" <low> --> <high>`; when the `y-axis` line is omitted entirely, MUST auto-scale
   the range from the min/max across every dataset's values instead.
5. MUST parse one or more `bar [<v1>, <v2>, ...]` and/or `line [<v1>, <v2>, ...]` dataset lines,
   each with exactly as many values as `x-axis` has categories; MUST support a "combo" chart with
   both a `bar` and a `line` dataset plotted on the same axes.
6. MUST render every chart bottom-up: the x-axis's categories run left-to-right along the bottom
   and the y-axis's values run bottom-to-top (0/low at the bottom, high at the top) -- Mermaid's
   own default look (see the termaid reference render below, which is already bottom-up). Mermaid's
   ` horizontal` keyword, which transposes this (categories down the left edge, bars pointing
   right instead of up), is not implemented; a chart carrying the keyword still parses (requirement
   1) but renders identically to one without it.
7. MUST render bar datasets as vertical block-character bars scaled to the y-axis range, one bar
   (or bar pair, for a combo chart) per category column, with y-axis tick labels along the left and
   an x-axis category-label row along the bottom, using eighth-resolution partial-block glyphs for
   a bar's fractional top row (Unicode Block Elements `▁`/`▂`/`▃`/`▄`/`▅`/`▆`/`▇`/`█`, U+2581-U+2588,
   giving 8 fill levels per row) rather than only a full block and termaid's single half-block
   rounding (`▄`, see the Reference example below) -- finer resolution than "full or half" so a
   bar's height doesn't visibly round to the nearest whole/half row when the data doesn't land on
   one. MUST align a bar's fill to the *same* row a `line` dataset's value would land on, not to a
   row above it: a tick row labeled `V` represents the value band centered on `V` (spanning half a
   row-step on either side), exactly like the row a `line` value of `V` is drawn on (requirement
   7's line rule below), not a band that merely *ends* at `V`. Concretely, for a row step of `s`, a
   bar of height `h` fills solid every row whose value `V` satisfies `V + s/2 <= h` (the row's whole
   band sits below `h`), leaves blank every row whose `V - s/2 > h`, and gives the exactly one row
   whose band straddles `h` (`V - s/2 <= h < V + s/2`) the eighth-glyph closest to
   `(h - (V - s/2)) / s`. This means a bar landing precisely on a tick (`h` itself a multiple of the
   step) still shows a half-block (`▄`) at that row, not a clean full block -- the row's gridline
   runs through its *center*, so a fill boundary sitting exactly on that gridline always splits the
   row's band in half, same as it would if a `line` dataset had a point there instead. MUST render
   line datasets as a connected step/staircase line -- a flat run at each
   category's value, a vertical riser at the boundary to the next category's value -- using rounded
   corner glyphs at each transition (`╭`/`╮`/`╰`/`╯`, the same round-corner set
   `viewmd/mermaid/grid/canvas.py:_box_glyphs`'s `"round"`/`"stadium"` node-shape case already
   returns), not square corners (contrast the plot's own axis box, which stays square) and not a
   diagonal line; each mark type MUST have a `use_ascii`-safe fallback per the existing `use_ascii`
   convention used elsewhere in `viewmd/mermaid/` (the eighth-block glyphs collapse to a single
   `use_ascii` fill character, same loss of resolution `use_ascii` mode already accepts elsewhere).
8. MUST size the plot area between an explicit minimum and maximum, both expressed as a fraction of
   the caller's resolved render `width` (the same parameter `_render_pie`/`_render_quadrant`
   already read -- see `viewmd/mermaid/__init__.py:render`'s docstring), rather than a single fixed
   or content-derived width (contrast gantt/flowchart, which size purely from their own content and
   ignore `width` entirely):
   - **Maximum: 100% of `width`.** MUST NOT deliberately render wider than the full viewport by
     default -- unlike the general Mermaid posture of `width` as a soft target a diagram may exceed
     and let the pager scroll (VIEWMD-0018), the xychart plot area's default width is capped there.
   - **Minimum: 50% of `width`.** MUST NOT shrink the plot area's width below half the viewport
     (a floor, unlike `viewmd/mermaid/quadrant/renderer.py`'s `_MIN_QUADRANT_WIDTH`, which is a
     fixed column count -- this one scales with the viewport too, just at half the rate); below
     that, axis labels and bar/step glyphs stop being legible regardless of how narrow the terminal
     itself is, so the chart overflows/scrolls (VIEWMD-0018) rather than compressing further.
   - **Aspect ratio: ~1:1 at the minimum width, never flatter than 2:1 (width:height) at the
     maximum.** At the 50%-of-viewport floor, height MUST be close to width (a near-square plot).
     As width grows from there toward the 100% ceiling, height MAY grow more slowly than width --
     a chart doesn't need to get proportionally taller just because the terminal is wide -- but
     height MUST NOT drop below half of width at any point in that range: a plot more than twice
     as wide as it is tall starts losing the y-axis resolution (row count) that's the point of
     this whole sizing requirement. Whether "close to 1:1"/"width:height" is measured in literal
     column/row counts or a ratio corrected for a terminal character cell's own (non-square) aspect
     is an implementation decision, as is exactly how height scales down between the two bounds
     (linearly in the width:height ratio, in absolute row count, etc.) -- not mandated by this
     requirement.
   - The exact minimum-width figure in columns, and how many categories/rows that translates to,
     are implementation decisions, not mandated by this requirement.
9. MUST leave an `xychart-beta`/`xychart` fence whose content fails to parse (including a
   `y-axis`/`x-axis` range or category list that fails to parse -- see the malformed-input handling
   already present in termaid's own parser, reference below) untouched (fall back to showing the
   raw fence), same fallback discipline as the other Mermaid renderers' MUST-NOT-crash requirement.
10. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- More than one `bar` and one `line` dataset combined in a single chart (i.e. multiple bar series
  side by side, or multiple line series overlaid) -- Mermaid's spec allows multiple datasets of
  each kind; this issue's v1 scope is the single-bar/single-line combo case termaid's own test
  suite exercises (reference below), with true multi-series support deferred to a follow-up issue.
- Color/theme differentiation between datasets -- viewmd's existing Mermaid renderers do not use
  ANSI color today, and this issue does not introduce it.
- Any xychart configuration or theming, in any of its forms: the inline `%%{init}%%` directive,
  the YAML front-matter `config:`/`themeVariables:` block, and options either can carry (`width`,
  `height`, `titlePadding`, `plotColorPalette`, axis/title/label colors, etc.). v1 renders every
  chart with the same fixed layout and no color regardless of what a source file's config block
  requests; the config block itself is simply inert extra text, same as viewmd already treats
  unrecognized front matter elsewhere.
- Horizontal orientation -- Mermaid's ` horizontal` keyword, which transposes the default layout
  (categories down the left edge, bars pointing right) is not implemented; requirement 6 makes the
  default bottom-up layout the only one v1 produces, whether or not the source specifies the
  keyword.
- The numeric-range form of `x-axis` (`x-axis "title" min --> max`, plotting a continuous numeric
  axis instead of discrete categories) -- only the categorical bracketed-list form (requirement 3)
  is in scope.
- Per-point line labels (`line [1.5 "label", 2.3]`, Mermaid v11.16.0+) -- deferred.
- Matching any upstream reference implementation byte-for-byte -- the local `mermaid-ascii` Go
  oracle used for differential-testing flowchart/sequence/ER has no XY-chart support, so fixtures
  here are hand-authored/visually-verified, same posture as VIEWMD-0032 onward. termaid's own
  rendering (below) is a useful cross-check, not an oracle to match exactly.

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a
`_is_xychart_diagram`/`_parse_xychart`/`_render_xychart` import trio and a new `if` branch,
mirroring the `pie`/`quadrant` branches specifically (parse-then-render, catching a module-local
`ParseError` into `MermaidError`, and threading `width` through -- requirement 8), rather than the
`er` branch's plain `use_ascii`-only signature. New module lives at `viewmd/mermaid/xychart/`
(`parser.py`, `renderer.py`), sibling to the other diagram packages. This is the largest single new
renderer among the eight gap diagram types (see Motivation) -- worth considering whether to land
the `bar`-only case first as its own reviewable increment before adding `line`/combo, given the
size, rather than one large patch; that sequencing is left to implementation, not mandated by a
Requirement.

### Reference examples (termaid's actual output)

Bar chart with an explicit y-axis range:

```
--- source ---
xychart-beta
    title "Sales"
    x-axis [Q1, Q2, Q3, Q4]
    y-axis 0 --> 100
    bar [40, 55, 70, 90]
--- rendered ---
                Sales

    100 │
        │                  ▄▄▄▄
        │                  ████
     80 │                  ████
        │            ▄▄▄▄  ████
        │            ████  ████
     60 │            ████  ████
        │      ████  ████  ████
        │      ████  ████  ████
     40 │████  ████  ████  ████
        │████  ████  ████  ████
        │████  ████  ████  ████
     20 │████  ████  ████  ████
        │████  ████  ████  ████
        │████  ████  ████  ████
      0 └──┬─────┬─────┬─────┬─
          Q1    Q2    Q3    Q4
```

Note termaid uses a half-height glyph (`▄`) to round a bar's fractional top row rather than only
whole-block rows -- a legibility detail worth building on, not just matching: requirement 7 asks
for the full eighth-block set instead of termaid's two-level (full/half) rounding. This bar-only
render is already the bottom-up layout requirement 6 asks for (0 at the bottom row, 100 at the
top); the mockups below extend it with a `line` dataset, drawn as an orthogonal step/staircase
(requirement 7) rather than termaid's own diagonal line style -- a deliberate difference from
termaid, not an oversight, matching the reference stair-step line-chart style requested for this
issue over a diagonal one.

### Mockup: bar chart with fine-grained (non-rounded) values

Same `Sales` chart shape as the termaid reference above, but with fractional data
(`42.5`/`67.3`/`23.8`/`89.1` instead of `40`/`55`/`70`/`90`) to show the eighth-block glyphs
(requirement 7) actually earning their keep -- each bar's fractional top row uses the closest of
the 8 levels to its true fill fraction, not just "half", and every row's gridline sits at the
*center* of its band (requirement 7), the same alignment a `line` value of that row would use:

```
--- source ---
xychart-beta
    title "Precise Sales"
    x-axis [Q1, Q2, Q3, Q4]
    y-axis 0 --> 100
    bar [42.5, 67.3, 23.8, 89.1]
--- rendered (mockup) ---
                Precise Sales

100 │
 90 │                  ▃▃▃▃
 80 │                  ████
 70 │      ▂▂▂▂        ████
 60 │      ████        ████
 50 │      ████        ████
 40 │▆▆▆▆  ████        ████
 30 │████  ████        ████
 20 │████  ████  ▇▇▇▇  ████
 10 │████  ████  ████  ████
  0 └──┬─────┬─────┬─────┬─
      Q1    Q2    Q3    Q4
```

Each row `V`'s band is `[V-5, V+5)` (half the 10-unit step on either side), so a bar's fill is
solid through every row whose whole band sits below its value, and the *one* row whose band
straddles the value gets the eighth-glyph closest to how far into that band it reaches: Q1's
`42.5` fills solid through row 30 (`[25,35)` is entirely below it), then lands 75% into row 40's
`[35,45)` -> `round(0.75*8)=6` -> `▆`. Q2's `67.3` fills through row 60, then 23% into row 70's
`[65,75)` -> `round(0.23*8)=2` -> `▂`. Q3's `23.8` fills through row 10, then 88% into row 20's
`[15,25)` -> `round(0.88*8)=7` -> `▇`. Q4's `89.1` fills through row 80, then 41% into row 90's
`[85,95)` -> `round(0.41*8)=3` -> `▃`. The row-height-to-USD scale (here, one row per 10) is itself
an implementation decision, not fixed by this requirement.

### Mockup: line chart

At a larger, more legible scale than the termaid reference above (wider category columns, finer
y-axis resolution), and closer to requirement 8's aspect-ratio floor than earlier drafts of this
mockup were (40 columns by 20 rows here is exactly 2:1, the floor itself, not flatter):

```
--- source ---
xychart-beta
    title "Revenue Trend"
    x-axis [Q1, Q2, Q3, Q4]
    y-axis 0 --> 100
    line [40, 60, 20, 100]
--- rendered (mockup) ---
                    Revenue Trend

100 │                              ╭─────────
 95 │                              │
 90 │                              │
 85 │                              │
 80 │                              │
 75 │                              │
 70 │                              │
 65 │                              │
 60 │          ╭─────────╮         │
 55 │          │         │         │
 50 │          │         │         │
 45 │          │         │         │
 40 │──────────╯         │         │
 35 │                    │         │
 30 │                    │         │
 25 │                    │         │
 20 │                    ╰─────────╯
 15 │
 10 │
  5 │
  0 └┬─────────┬─────────┬─────────┬─────────
    Q1        Q2        Q3        Q4
```

Each category holds its value as a flat run until the next category, where a vertical riser jumps
to the new value -- rounded corner glyphs (`╭`/`╮`/`╰`/`╯`), the same round-corner set
`canvas.py:_box_glyphs`'s `"round"` node-shape case already returns, reused here rather than
inventing new ones or drawing a diagonal (the axis box itself, `└`/`┬`, stays square -- only the
line's own transitions are rounded). Exactly how many rows of vertical resolution a riser gets, and
where within a category's
span the flat run sits, are implementation decisions, not requirements -- as is the exact column
width per category and row count, both governed by requirement 8's min/max sizing instead of a
fixed figure.

### Mockup: combined bar + line chart

Same larger-scale treatment (wider columns than the termaid `Sales` reference above), and finer
row resolution than an earlier draft of this mockup used -- 40 columns by 24 rows, a 1.67:1
ratio, well inside requirement 8's 2:1 floor rather than sitting flat against it:

```
--- source ---
xychart-beta
    title "Sales vs Target"
    x-axis [Q1, Q2, Q3, Q4]
    y-axis 0 --> 120
    bar  [40, 60, 80, 100]
    line [60, 80, 100, 120]
--- rendered (mockup) ---
                    Sales vs Target

120 │                              ╭─────────
115 │                              │
110 │                              │
105 │                              │
100 │                    ╭─────────╯▄▄▄▄▄▄▄▄▄
 95 │                    │         ██████████
 90 │                    │         ██████████
 85 │                    │         ██████████
 80 │          ╭─────────╯▄▄▄▄▄▄▄▄▄██████████
 75 │          │         ████████████████████
 70 │          │         ████████████████████
 65 │          │         ████████████████████
 60 │──────────╯▄▄▄▄▄▄▄▄▄████████████████████
 55 │          ██████████████████████████████
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

The bar dataset draws as the block-character fill from the axis (requirement 7); the line dataset's
step path is drawn on top of it wherever the two coincide (e.g. the `╯` riser-bottoms sitting right
at a bar's own gridline) rather than being hidden behind the fill -- again, the exact resolution
when both marks want the same cell is an implementation decision, not a requirement. Every bar here
(`40`/`60`/`80`/`100`) lands exactly on a tick, so each shows a half-block `▄` at its own row rather
than a clean full top -- that's requirement 7's row-centered alignment working as intended: the
tick's gridline runs through the middle of its row, so a bar reaching precisely that value always
splits the row in half, the same as a `line` point at that value would sit centered on the row, not
at its upper edge.

### Mockup: real-file demo at 100% viewport width

[`docs/nvidia-stock-xychart.md`](../docs/nvidia-stock-xychart.md) is an existing, not-yet-rendering
demo page for this issue -- 13 categories, a single `line` dataset, real (if approximate) data:

```
xychart-beta
    title "NVDA month-end close, Aug 2025 - Aug 2026"
    x-axis [Aug25, Sep25, Oct25, Nov25, Dec25, Jan26, Feb26, Mar26, Apr26, May26, Jun26, Jul26, Aug26]
    y-axis "USD" 150 --> 230
    line [173.95, 186.34, 202.23, 176.77, 186.27, 190.90, 176.97, 174.20, 199.34, 210.89, 200.09, 200.75, 225.16]
```

At requirement 8's maximum (100% of a 100-column viewport, the same fallback `_terminal_width`
already uses for pie), values rounded to the nearest 3 USD, generated by
[`poc/xychart/xychart_poc.py`](../poc/xychart/xychart_poc.py) (`nvda` mode) rather than hand-drawn:

```
228 │
225 │                                                                                    ╭──────
222 │                                                                                    │
219 │                                                                                    │
216 │                                                                                    │
213 │                                                                                    │
210 │                                                               ╭──────╮             │
207 │                                                               │      │             │
204 │                                                               │      │             │
201 │              ╭──────╮                                         │      ╰─────────────╯
198 │              │      │                                  ╭──────╯
195 │              │      │                                  │
192 │              │      │             ╭──────╮             │
189 │              │      │             │      │             │
186 │       ╭──────╯      │      ╭──────╯      │             │
183 │       │             │      │             │             │
180 │       │             │      │             │             │
177 │       │             ╰──────╯             ╰──────╮      │
174 │───────╯                                         ╰──────╯
171 │
168 │
165 │
162 │
159 │
156 │
153 │
150 └┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────
    Aug25  Sep25  Oct25  Nov25  Dec25  Jan26  Feb26  Mar26  Apr26  May26  Jun26  Jul26  Aug26
```

26 data rows plus the axis, at 91 columns (13 categories, 7 each) -- shorter than an earlier draft
of this mockup, which chased requirement 8's 2:1 aspect floor as far as it would go (41 rows) and
ended up too tall to read comfortably in this document; ~3.5:1 here trades a closer aspect-ratio
match for a mockup that's actually easy to scan, which is the whole point of a mockup. The topmost
row is 228, not the source's stated 230 -- the 80-unit range doesn't divide evenly by the 3-unit
step, so the highest row aligned to the axis's own baseline (150) is 228, two short of the real
max. Two further honest caveats, beyond the usual "not the renderer's actual output": rounding 13
real values to the nearest 3 USD is coarser than eighth-block resolution (requirement 7) would
actually need -- a real render computes exact fractional fill from the real y-axis scale
(requirement 4), no rounding -- and generating this one with a script rather than by hand is a
direct response to an earlier hand-drawn draft silently dropping a whole riser transition, caught
only on review.

### Out of scope: multiple series + color config

The following (a real Mermaid example, not hand-authored) exercises several things Non-goals
above excludes from v1, together:

```
---
config:
  themeVariables:
    xyChart:
      plotColorPalette: '#000000, #0000FF, #00FF00, #FF0000'
---
xychart
    title "Different Colors in xyChart"
    x-axis "categoriesX" ["Category 1", "Category 2", "Category 3", "Category 4"]
    y-axis "valuesY" 0 --> 50
    line [10,20,30,40]
    bar [20,30,25,35]
    bar [15,25,20,30]
    line [5,15,25,35]
```

Two independent restrictions apply, each traced to a specific Non-goals bullet above -- the bare
`xychart` fence itself is *not* one of them, since requirement 1 recognizes both spellings:

1. **Two `bar` lines and two `line` lines** -- the multi-series Non-goal caps v1 at one bar dataset
   plus one line dataset.
2. **The `config:`/`themeVariables:`/`plotColorPalette` front matter** -- the configuration
   Non-goal; even on a chart that fit the rest of v1's scope, this block would be ignored rather
   than changing layout or introducing per-series color.

Illustrative only (not a v1 deliverable) -- a hypothetical later rendering, distinguishing series
by glyph and step-line height instead of color since ANSI color remains out of scope:

```
                Different Colors in xyChart

40 │                              ╭──○
30 │            ╭──○        ╭──○──╯
20 │      ╭──●──╯  ▓▓░░  ╭──●──╯  ▓▓░░
10 │●──╯  ▓▓░░  ╭──╯░░  ●──╯  ▓▓░░
 0 └┬─────┬─────┬─────┬─────
   C1    C2    C3    C4
```

(`▓` = first bar series, `░` = second bar series, `●` = first line series step, `○` = second line
series step -- glyph/height differentiation standing in for the four-color palette the source
requests, since v1 has neither multi-series nor color; not hand-verified to the source data's exact
values, it only needs to convey the shape a later multi-series/step-line renderer would produce.)

Malformed range input (from `tests/test_xychart.py:TestMalformedXYChartInput`), which termaid's own
parser tolerates by leaving the range unset rather than raising:

```
xychart-beta
    x-axis "t" 0.1.2 --> 10
    bar [1, 2]
```

parses with `x_range is None` (termaid tracks an optional numeric x-range analogous to the y-range,
unused by the category-axis form in requirement 3/4 above) rather than raising -- illustrating the
malformed-input tolerance requirement 9 asks for at the chart level, one layer up.

## Acceptance / verification

- Unit tests for the parser: bare and titled `x-axis`, explicit and auto-scaled (omitted)
  `y-axis`, a `bar`-only chart, a `line`-only chart, a combo bar+line chart, both the
  `xychart-beta` and bare `xychart` fence spellings, the (ignored) ` horizontal` keyword, and a
  malformed axis line (requirement 9) tolerated without raising.
- A rendered fixture for a `Sales`-style bar-only chart (overall shape/magnitude cross-checked
  against termaid's example above, not row-for-row -- termaid's own edge-anchored, two-level
  rounding differs from requirement 7's row-centered, eighth-block scheme by design; per Non-goals,
  no oracle to differential-test exactly against).
- A fixture confirming a bar landing exactly on a y-axis tick (a whole multiple of the row step,
  e.g. `40` at a 10-per-row scale) renders a half-block (`▄`) at that row, not a full block --
  requirement 7's row-centered alignment, exercised in the combo mockup above.
- A rendered fixture each for the `Precise Sales` fine-grained-bar mockup, the line-chart mockup,
  and the combined bar+line mockup above.
- A fixture confirming the chart's plot area scales with a caller-supplied `width` (requirement 8):
  one at 50% of `width` (the minimum floor, confirming height comes out close to width there and
  doesn't compress narrower than the floor), one at 100% (the maximum, confirming it doesn't grow
  past it), and one at a width in between confirming height grows more slowly than width but never
  drops below half of it (the 2:1 floor) -- plus one at a width narrow enough to force the 50%
  floor to overflow and scroll.
- A fixture confirming every eighth-block fill level (`▁` through `█`, requirement 7) appears for
  some bar value across the test data, not just the two termaid already exercises (`▄` and `█`).
- A rendered fixture for `docs/nvidia-stock-xychart.md`'s 13-category real-data `line` chart at
  100% viewport width, since that file already exists referencing this issue and currently falls
  back to a raw fence.
- A fixture confirming `use_ascii` mode's fallback glyphs for both bar (the eighth-block set
  collapsing to one fill character) and line (the step-line's corner glyphs) marks, requirement 7.
- A malformed `xychart-beta`/`xychart` fence (e.g. a dataset with fewer values than categories)
  falls back to showing the raw fence rather than crashing viewmd (requirement 9).
- A fixture for a chart that's valid Mermaid but exceeds v1's scope (e.g. the two-bar/two-line
  multi-series example above) also falls back to the raw fence rather than crashing or silently
  dropping the extra series -- same fallback discipline as requirement 9, extended to
  "unsupported" rather than only "malformed".
- `./run-tests.sh` green.

## Peer review

