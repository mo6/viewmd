---
id: VIEWMD-0047
title: Render Mermaid quadrant charts
status: in-progress
area: [render, mermaid]
effort: medium
created: 2026-08-09
updated: 2026-08-10
accepted_by: George Moses
accepted_at: 2026-08-10
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Render Mermaid quadrant charts

## Summary

Add a Mermaid diagram type -- `quadrantChart` -- alongside the existing flowchart, sequence, and ER
renderers (`viewmd/mermaid/{flowchart,sequence,er}/`) and the diagram types proposed in
[VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md) through
[VIEWMD-0042](VIEWMD-0042-mermaid-gitgraph-diagrams.md). A Mermaid quadrant chart
(https://mermaid.js.org/syntax/quadrantChart.html) is a 2x2 grid with labeled axes and quadrants,
onto which labeled data points are plotted at `[x, y]` coordinates in the `0.0`-`1.0` range.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `quadrantChart` fence
today -- it falls through every `_is_*_diagram` sniff. Of the eight diagram types termaid supports
that viewmd does not yet track, this is one of the more self-contained: a fixed grid with axis
labels and quadrant titles, plus data points mapped from normalized `[0,1]` coordinates onto
terminal rows/columns -- no recursive layout, no proportional sizing, no edge routing.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `quadrantChart`
   (`viewmd/mermaid/quadrant/parser.py:sniff`, following the `sniff`/`parse`/`render` module shape
   already used by the other diagram packages) and wire it into `viewmd/mermaid/__init__.py:render`
   alongside the existing sniffs.
2. MUST parse an optional `title <text>` line, rendered above the chart.
3. MUST parse `x-axis <low label> --> <high label>` and `y-axis <low label> --> <high label>`,
   rendering the low/high labels at the corresponding ends of each axis.
4. MUST parse the four `quadrant-1`/`quadrant-2`/`quadrant-3`/`quadrant-4` labels (top-right,
   top-left, bottom-left, bottom-right, per Mermaid's own numbering) and render each inside its
   quadrant.
5. MUST parse a data point line `<label>: [<x>, <y>]`, where `<x>` and `<y>` are decimals; MUST
   support one or more data points.
6. MUST render the grid as a bordered box (box-drawing characters) with an internal cross dividing
   it into the four quadrants, with each data point plotted as a marker at its `(x, y)` position
   (mapped from `[0,1]` onto the grid's column/row extent within its quadrant) labeled directly
   below the marker, matching the box layout in the Design notes' mockups below rather than a
   free-floating axis-cross with no border.
7. MUST size the box's default dimensions relative to the caller's resolved render width rather
   than a fixed constant, the same posture as the pie chart's `--width` handling
   (`viewmd/mermaid/pie/renderer.py:_default_radius`, VIEWMD-0043 requirement 5b): each quadrant
   cell's width scales so the full box (plus its left-margin y-axis label and title) still fits the
   target width, floored at a sane legible minimum, rather than the fixed `qw=24` used by this
   issue's own mockups above (which are illustrative at one particular width, not the shipped
   default). `width` MUST be threaded down through `viewmd/mermaid/__init__.py:render`'s existing
   `width` parameter into the quadrant renderer -- reusing the already-resolved value the same four
   call sites the pie chart threads it through, not re-querying the raw terminal size independently
   (VIEWMD-0043's own peer review caught exactly this mistake: an initial pie-chart implementation
   queried the terminal directly instead of accepting `width`, so `--width 60` vs `--width 200`
   against the same file rendered byte-identical output despite every unit test passing, because
   every test called the renderer with the correct `width` directly rather than tracing where it
   came from end to end -- see AGENTS.md's VIEWMD-0043 lesson).
8. MUST render in color when the caller's resolved `color` flag is true -- the same boolean
   `viewmd/mermaid/__init__.py:render` already threads to the pie renderer (VIEWMD-0043;
   `--color`/`NO_COLOR`/tty auto-detection all already resolve to this one flag in
   `viewmd/__main__.py`, nothing new to add there) -- and fall back to today's plain monochrome box
   (mockup 1 above, byte-for-byte) when it's false. Color is strictly additive, never a different
   layout: the same character grid renders either way. When enabled, using the palette and
   derivation validated in `poc/quadrant/quadrant_poc.py` (`QUADRANT_COLORS`/`_darken`) as the
   shipped default rather than a new palette invented at implementation time:
   a. Each quadrant's own border segments, its `quadrant-N` label text, and every point marker and
      point label inside it are tinted with that quadrant's own hue (`QUADRANT_COLORS`; the POC's
      `--fill quadrant`).
   b. That quadrant's entire interior additionally gets a solid background fill, darkened from the
      same hue (`_darken`, 28% brightness) so foreground text stays legible on top (the POC's
      `--bg quadrant`).
   c. A data point's own `color:` style key, or its `:::class` reference's `classDef color:`, MUST
      override that fallback quadrant tint when present (the POC's `--points styled`); `radius:`,
      `stroke-color:`, and `stroke-width:` keys, and any `classDef` values other than `color`,
      remain parsed-and-discarded per the Non-goals entry below.
   d. Title and x-axis/y-axis labels stay plain/uncolored outside the box, matching mockup 1a below.
9. MUST leave a `quadrantChart` fence whose content fails to parse untouched (fall back to showing
   the raw fence), same fallback discipline as the other Mermaid renderers'
   MUST-NOT-crash requirement. A single malformed data-point line (e.g. a non-numeric coordinate)
   MUST be skipped rather than aborting the whole chart, matching Mermaid's own tolerance for a bad
   data row.
10. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- Point `radius:`/`stroke-color:`/`stroke-width:` styling, and any `classDef` value other than
  `color` -- a single-character marker has no terminal-cell equivalent for a radius or a stroke
  ring; only a point's `color:` (or its class's `classDef color:`) is read, per requirement 8c.
- Mermaid's own `chartWidth`/`chartHeight`/`pointRadius` numeric config knobs, whether via an
  inline `%%{init}%%` directive or the equivalent YAML `---\nconfig:\n  quadrantChart: ...\n---`
  front-matter block -- requirement 7 makes viewmd size the chart itself from the caller's resolved
  render width, the same way the pie chart ignores Mermaid's own pixel-based sizing knobs in favor
  of its own terminal-relative default; Mermaid's explicit pixel-dimension overrides are parsed away
  (ignored) rather than translated into a terminal-cell equivalent.
- Mermaid's presence-dependent `xAxisPosition`/`yAxisPosition` defaults (axis-label line moves to
  the top/right, or centers inside each quadrant, when a chart has no data points) -- viewmd's grid
  always renders the x-axis label under the box and the y-axis label to its left, points or not
  (see the config/theme mockup below), rather than reproducing that conditional placement.
- Collision handling for two data points that map to the same terminal cell -- best-effort (e.g.
  last-write-wins, or a combined label) is acceptable; a dedicated jitter/offset algorithm is out
  of scope.
- Matching any upstream reference implementation byte-for-byte -- the local `mermaid-ascii` Go
  oracle used for differential-testing flowchart/sequence/ER has no quadrant-chart support, so
  fixtures here are hand-authored/visually-verified, same posture as VIEWMD-0032 onward. termaid's
  own rendering (below) is a useful cross-check, not an oracle to match exactly.

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a
`_is_quadrant_diagram`/`_parse_quadrant`/`_render_quadrant` import trio and a new `if` branch,
mirroring the `pie` branch rather than the `er` one for this specific detail: `render`'s existing
`width` *and* `color` parameters both need to reach `_render_quadrant` the same way they already
reach `_render_pie` (`return _render_pie(chart, use_ascii=use_ascii, color=color, width=width)`),
so requirement 7's dynamic sizing has a real value to size against and requirement 8's coloring has
a real flag to gate on, instead of falling back to a freshly-queried terminal size or defaulting
color on/off independently at the renderer. `viewmd/mermaid/quadrant/renderer.py` is thus the
*second* Mermaid renderer (after pie) to read `color` at all -- every other diagram package still
ignores it, unaffected (requirement 10). New module lives at `viewmd/mermaid/quadrant/`
(`parser.py`, `renderer.py`), sibling to the other diagram packages, with a
`_default_box_width`/`_terminal_width` pair modeled directly on
`viewmd/mermaid/pie/renderer.py`'s `_default_radius`/`_terminal_width`, and its own
`QUADRANT_COLORS`/`_darken` ported from `poc/quadrant/quadrant_poc.py` rather than redefined from
scratch (requirement 8).
The axis-cross-and-plot primitive is new but simple relative to the other gap diagram types --
it's arithmetic (linear-map a `[0,1]` coordinate to a grid cell) rather than a new box/tree/routing
layout, closer in spirit to VIEWMD-0048's (xychart) axis math than to anything
`viewmd/mermaid/grid/canvas.py` does today.

### Reference example (termaid's actual output)

```
--- source ---
quadrantChart
    title Priority Matrix
    x-axis Low Effort --> High Effort
    y-axis Low Impact --> High Impact
    quadrant-1 Do First
    quadrant-2 Plan
    quadrant-3 Delegate
    quadrant-4 Skip
    Cache: [0.2, 0.8]
    Rewrite: [0.9, 0.3]
--- rendered (abridged) ---
                       Priority Matrix

                                │
             ● Cache            │
               Plan             │          Do First
                                │
  ──────────────────────────────┼─────────────────────────────
                                │
                                │               Rewrite●
             Delegate           │            Skip
                                │

                   Low Effort -> High Effort
```

termaid does not render the `y-axis` labels at all in this output (only `x-axis`, at the bottom) --
whether viewmd's own implementation should also surface the y-axis low/high labels (requirement 3
requires parsing both) is a layout decision left open for this issue, not dictated by this
reference.

### Mockups of mermaid.js.org's own syntax-doc examples

Hand-drawn viewmd-style mockups (not a real render, no implementation exists yet) for the three full runnable `quadrantChart` examples on https://mermaid.js.org/syntax/quadrantChart.html, to sanity-check the design notes above against every example the upstream docs actually ship, not just the termaid reference above. Two of the page's examples exercise Non-goals territory (per-point `radius`/`color`/`stroke-*` styling, `classDef`, and `config`/`themeVariables` overrides) -- both are still mocked up below to show what viewmd renders when it silently ignores that styling and falls back to a plain marker, which is the intended degraded behavior per this issue's Non-goals rather than a parse failure.

Unlike the free-floating axis-cross in the termaid reference above, these three use a bordered box, matching how mermaid.js.org itself actually renders the chart -- a rectangle with an internal cross dividing the four quadrants, quadrant labels pinned to each cell's top-left corner, and each point's label centered directly under its marker, per the mermaid.js.org-rendered SVG of this same example referenced in this issue's revision history (a filled-color rectangle with rounded typography, not reproducible as literal text here, but that overall layout -- box, corner-anchored quadrant labels, label-under-marker points, axis labels outside the box -- is what these mockups approximate in monospace).

Adopting that same box for viewmd is cheap to implement: it is the same axis-cross-and-plot arithmetic from the Design notes above, just drawn with box-drawing characters (`┌┬┐├┼┤└┴┘─│`) instead of a plain `┼`/`─`/`│` cross, plus a fixed left margin for the y-axis label and a bottom row for the x-axis label -- no new layout primitive. Quadrant labels sit at the top-left corner of their own cell (matching the real render above, and Mermaid's own "points present -> quadrant text at the top" rule); each point's label is centered directly below its marker rather than beside it, which is both closer to the real output and avoids the beside-the-marker text frequently crossing the box's internal divider that the termaid-style mockups above ran into.

**1. The page's main "Example"** -- title, both axis labels, all four quadrant labels, six data points:

```
--- source ---
quadrantChart
    title Reach and engagement of campaigns
    x-axis Low Reach --> High Reach
    y-axis Low Engagement --> High Engagement
    quadrant-1 We should expand
    quadrant-2 Need to promote
    quadrant-3 Re-evaluate
    quadrant-4 May be improved
    Campaign A: [0.3, 0.6]
    Campaign B: [0.45, 0.23]
    Campaign C: [0.57, 0.69]
    Campaign D: [0.78, 0.34]
    Campaign E: [0.40, 0.34]
    Campaign F: [0.35, 0.78]
--- mocked-up rendering ---
                         Reach and engagement of campaigns

                ┌────────────────────────┬────────────────────────┐
                │Need to promote         │We should expand        │
                │                        │                        │
                │                        │                        │
High Engagement │                ●       │                        │
                │           Campaign F   │   ●                    │
                │              ●         │Campaign C              │
                │         Campaign A     │                        │
                ├────────────────────────┼────────────────────────┤
                │Re-evaluate             │May be improved         │
                │                        │                        │
                │                  ●     │             ●          │
 Low Engagement │             Campaign E │        Campaign D      │
                │              Campaign B│                        │
                │                        │                        │
                │                        │                        │
                └────────────────────────┴────────────────────────┘
                        Low Reach                 High Reach
```

**1a. Colored variant of the same source (requirement 8; what actually ships when `color` is
true).** Mockup 1 above is the `color=False` fallback (byte-for-byte); this is the same source
rendered with color on, matching requirement 8's `--fill quadrant`/`--bg quadrant`/`--points
styled` scheme -- also reproducible directly from the exploratory
`poc/quadrant/quadrant_poc.py` this scheme was chosen from (not part of the shipped `viewmd`
package, but its `QUADRANT_COLORS`/`_darken` constants are what the real renderer MUST use, per
requirement 8):

```
python3 poc/quadrant/quadrant_poc.py poc/quadrant/example.mmd --bg quadrant --fill quadrant --points styled
```

Character positions are identical to mockup 1 above (color doesn't move anything); requirement 8
applies each quadrant's own tint to its border segments, its quadrant-label text, and its
markers/point-labels (8a), on top of a darkened background fill covering that quadrant's whole
interior (8b, 28% brightness of the same tint so foreground text stays legible) -- everything
outside the box (title, x-axis/y-axis labels) stays plain/uncolored (8d):

| Quadrant | Label | Border/text tint (`--fill quadrant`) | Background fill (`--bg quadrant`) |
|---|---|---|---|
| 1 (top-right) | We should expand | `#6f9fd8` | `#1f2c3c` |
| 2 (top-left) | Need to promote | `#d88a3f` | `#3c2611` |
| 3 (bottom-left) | Re-evaluate | `#3fa66a` | `#112e1d` |
| 4 (bottom-right) | May be improved | `#b06fd8` | `#311f3c` |

Requirement 8c (a point's own `color:`/`classDef` overriding its quadrant's fallback tint) has no
visible effect on *this* source: none of `example.mmd`'s six points set an explicit `color:` or
`:::class`, so every marker/label falls back to its own quadrant's tint from the table above --
that override only shows up against `poc/quadrant/example-styled.mmd`'s explicit per-point styling,
which is why the Acceptance/verification section below requires a dedicated fixture for it, not
just this one.

**2. "Example on config and theme"** -- no data points at all, so per the `Syntax` note both the quadrant text *and* the axis text render centered inside each quadrant rather than at the top-left corner. The `config`/`themeVariables` front matter (`chartWidth`/`chartHeight`/`quadrant1TextFill`) is Non-goals territory and has no effect on this mockup -- viewmd renders the same fixed box it always does and ignores the override block entirely, whether it's spelled as this YAML front-matter form or an inline `%%{init}%%` directive elsewhere in Mermaid support. Per the Non-goals entry above, the x-axis/y-axis labels stay pinned outside the box (bottom/left) even with no points, rather than migrating per Mermaid's `xAxisPosition`/`yAxisPosition` defaults:

```
--- source ---
---
config:
  quadrantChart:
    chartWidth: 400
    chartHeight: 400
  themeVariables:
    quadrant1TextFill: "ff0000"
---
quadrantChart
  x-axis Urgent --> Not Urgent
  y-axis Not Important --> "Important ❤"
  quadrant-1 Plan
  quadrant-2 Do
  quadrant-3 Delegate
  quadrant-4 Delete
--- mocked-up rendering ---
              ┌────────────────────────┬────────────────────────┐
              │                        │                        │
              │                        │                        │
              │                        │                        │
  Important ❤ │           Do           │          Plan          │
              │                        │                        │
              │                        │                        │
              │                        │                        │
              ├────────────────────────┼────────────────────────┤
              │                        │                        │
              │                        │                        │
              │                        │                        │
Not Important │        Delegate        │         Delete         │
              │                        │                        │
              │                        │                        │
              │                        │                        │
              └────────────────────────┴────────────────────────┘
                        Urgent                  Not Urgent
```

**3. "Example on styling"** -- same title/axes/quadrants as example 1, but every data point line carries `radius:`/`color:`/`stroke-color:`/`stroke-width:` styling, and two points (`Campaign B`, `Campaign E`) use a `:::class1`/`:::class2` class reference with a trailing `classDef` block defining them. Both are Non-goals: viewmd MUST still parse the `<label>: [x, y]` prefix of each line and plot the point, but ignores everything after the coordinates (styling keywords and class references alike) and drops any `classDef` lines entirely, rendering every point as the same plain `●` marker. This example's six points also cluster diagonally close together (`[0.9,0.0]` through `[0.4,0.5]`) -- four of the six land in the same quadrant, which is the Non-goals-scoped collision case in practice, not a hypothetical:

```
--- source ---
quadrantChart
  title Reach and engagement of campaigns
  x-axis Low Reach --> High Reach
  y-axis Low Engagement --> High Engagement
  quadrant-1 We should expand
  quadrant-2 Need to promote
  quadrant-3 Re-evaluate
  quadrant-4 May be improved
  Campaign A: [0.9, 0.0] radius: 12
  Campaign B:::class1: [0.8, 0.1] color: #ff3300, radius: 10
  Campaign C: [0.7, 0.2] radius: 25, color: #00ff33, stroke-color: #10f0f0
  Campaign D: [0.6, 0.3] radius: 15, stroke-color: #00ff0f, stroke-width: 5px ,color: #ff33f0
  Campaign E:::class2: [0.5, 0.4]
  Campaign F:::class3: [0.4, 0.5] color: #0000ff
  classDef class1 color: #109060
  classDef class2 color: #908342, radius : 10, stroke-color: #310085, stroke-width: 10px
  classDef class3 color: #f00fff, radius : 10
--- mocked-up rendering ---
                         Reach and engagement of campaigns

                ┌────────────────────────┬────────────────────────┐
                │Need to promote         │We should expand        │
                │                        │                        │
                │                        │                        │
                │                        │                        │
High Engagement │                        │                        │
                │                        │                        │
                │                        │                        │
                │                  ●     │                        │
                │             Campaign F │                        │
                ├────────────────────────┼────────────────────────┤
                │Re-evaluate             │May be improved         │
                │                        │Campaign E              │
                │                        │●                       │
                │                        │     ●                  │
 Low Engagement │                        │Campaign D              │
                │                        │         Campaign B     │
                │                        │              ●         │
                │                        │    Campaign C    ●     │
                │                        │         ●   Campaign A │
                └────────────────────────┴────────────────────────┘
                        Low Reach                 High Reach
```

The page's remaining code blocks (the standalone `title`-only snippet, the `x-axis`/`y-axis` single-label-vs-both-labels variants, the bare `Point 1: [0.75, 0.80]` syntax notes, and the two `Point A:`/`classDef` styling-syntax fragments under "Point styling") are syntax fragments rather than full runnable diagrams -- each is just one line of the syntax already covered by the three mockups above, so they aren't mocked up separately.

## Acceptance / verification

- Unit tests for the parser: `title`, both axis lines, all four quadrant labels, one or more data
  points with decimal coordinates, a point's `color:` style key and its `:::class` ->
  `classDef color:` reference (requirement 8c), and a malformed data-point line (requirement 9)
  skipped rather than aborting the chart.
- A rendered fixture reproducing the `Priority Matrix` example above (marker placement and quadrant
  labels; exact spacing is an implementation choice, per Design notes), hand-verified (per
  Non-goals, no oracle to differential-test against; termaid's own output is a cross-check, not a
  target to match exactly).
- A colored fixture reproducing mockup 1a above (`color=True`) against `example.mmd`, confirming
  each quadrant's border/label/point tint (8a), its background fill (8b), and that title/axis
  labels stay uncolored (8d); a second colored fixture against a source with an explicit per-point
  `color:` and a `:::class` -> `classDef color:` reference (mirroring
  `poc/quadrant/example-styled.mmd`), confirming requirement 8c's override actually takes effect
  instead of silently falling back to the quadrant tint.
- A fixture confirming `color=False` renders byte-for-byte identical to the plain box (mockup 1),
  proving color is additive and never changes layout (requirement 8's own framing).
- A fixture with two data points close enough to land in the same cell, confirming the chart still
  renders without crashing (requirement 9's tolerance, per Non-goals' collision-handling scope).
- A malformed `quadrantChart` fence (e.g. missing both axis lines entirely) falls back to showing
  the raw fence rather than crashing viewmd.
- A fixture confirming the box's default width (requirement 7) scales with a mocked/injected `width`
  value passed into the renderer, mirroring
  `test_pie_chart_circular_size_respects_render_width`/`test_render_width_kwarg_overrides_raw_terminal_size`
  (`tests/test_render.py`) for the pie chart.
- Manually verified end to end, not just via the unit tests above: `./viewmd.sh <file>.md --width
  60` vs. `./viewmd.sh <file>.md --width 200` against the same quadrant-chart source produce
  differently-sized boxes -- the exact check that caught requirement 5b's threading bug in
  VIEWMD-0043 (a comprehensive passing test suite did not, because every test supplied `width`
  directly rather than tracing whether the CLI flag actually reaches the renderer). Likewise
  `./viewmd.sh <file>.md --color always` vs. `--color never` against the same file, so requirement
  8's `color` plumbing is checked the same end-to-end way, not just via a renderer called with the
  right kwarg directly.
- `./run-tests.sh` green.

## Peer review

- **Claude Sonnet 5** (agent, independent review -- fresh context, not the implementing session), 2026-08-10: reviewed `viewmd/mermaid/quadrant/{parser,renderer}.py`, the `viewmd/mermaid/__init__.py` dispatch wiring, and the `viewmd/mermaid/grid/canvas.py` color-helper addition against every numbered requirement, ran `./run-tests.sh`, and independently exercised the renderer/CLI with hand-crafted edge cases rather than only reading code. Found: (1) HIGH -- `A: [nan, inf]` parsed successfully (Python's `float()` accepts `nan`/`inf`) but then crashed the renderer with an uncaught `ValueError` in `round()`, bypassing requirement 9's raw-fence fallback entirely -- confirmed via `./viewmd.sh` on a file containing that line. (2) MEDIUM -- `_default_box_width` ignored `chart.title` entirely, only factoring in the y-axis label, despite requirement 7 explicitly naming the title as something the box must fit; confirmed a long title overflowing a narrow-width render. (3) MEDIUM -- `sniff`/`parse` didn't skip a leading YAML front-matter block, so the issue's own "Example on config and theme" mockup (which the Non-goals section says should render with the override "parsed away/ignored") was instead left as an unrendered raw fence. (4) LOW -- the Acceptance section's two named fixtures (`example.mmd`, `example-styled.mmd`, mirroring `poc/quadrant/`) didn't exist under `tests/fixtures/mermaid_quadrant/`, and no test pinned the specific per-quadrant hex values from mockup 1a's legend table. (5) LOW -- a dangling `x-axis  -->` (empty label on both sides) silently parsed as a literal `-->` label instead of failing. (6) LOW, Non-goals-scoped -- many points crowded into one cell degrade into character-level overlap rather than clean last-write-wins; left as-is, since Non-goals explicitly permits best-effort collision handling and a dedicated jitter/offset algorithm is out of scope. (7) trivial -- a `wrap_text_in_color` refactor added a `try/except` around invalid-hex parsing; flagged as technically touching requirement 10 but unreachable by any existing caller (all palettes are hardcoded), accepted as an incidental robustness fix. What checked out: dispatch wiring/width/color end-to-end threading (verified via `--width 60` vs `--width 200` and `--color always`/`never` against the real CLI, reproducing the exact VIEWMD-0043-style regression check the issue calls for), quadrant numbering and `[0,1]`->cell coordinate math (including out-of-range/negative inputs, clamped without crashing), the 8a-8d color-precedence logic, and Non-goals adherence (`radius:`/`stroke-*`/non-`color` `classDef` values parsed and discarded).
- Findings (1), (2), (3), (4), and (5) above were fixed in response (non-finite coordinates now skipped per requirement 9's tolerance, `_default_box_width` now grows for a long title, `_strip_front_matter` added to `sniff`/`parse`, `tests/fixtures/mermaid_quadrant/example.mmd`/`example-styled.mmd` added with tests pinning mockup 1a's exact hex values and the styled overrides, and a dangling `-->` now raises `ParseError`), each with a new regression test; `./run-tests.sh` re-confirmed green afterward. Findings (6) and (7) were left as-is per the reviewer's own assessment (Non-goals-scoped and unreachable/non-regression, respectively).

