---
id: VIEWMD-0047
title: Render Mermaid quadrant charts
status: proposed
area: [render, mermaid]
effort: medium
created: 2026-08-09
updated: 2026-08-09
accepted_by:
accepted_at:
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
6. MUST render the grid as two perpendicular axis lines crossing at the chart's center, dividing it
   into the four quadrants, with each data point plotted as a marker at its `(x, y)` position
   (mapped from `[0,1]` onto the grid's column/row extent) labeled beside the marker.
7. MUST leave a `quadrantChart` fence whose content fails to parse untouched (fall back to showing
   the raw fence), same fallback discipline as the other Mermaid renderers'
   MUST-NOT-crash requirement. A single malformed data-point line (e.g. a non-numeric coordinate)
   MUST be skipped rather than aborting the whole chart, matching Mermaid's own tolerance for a bad
   data row.
8. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- Data point styling (`classDef`, per-point size/color) -- viewmd's existing Mermaid renderers do
  not use ANSI color today, and this issue does not introduce it.
- Configurable point-radius/chart-width `%%{init}%%` overrides -- a single reasonable fixed grid
  size, matching the other Mermaid renderers' current posture, is sufficient.
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
mirroring the `er` branch (parse-then-render, catching a module-local `ParseError` into
`MermaidError`). New module lives at `viewmd/mermaid/quadrant/` (`parser.py`, `renderer.py`),
sibling to the other diagram packages. The axis-cross-and-plot primitive is new but simple relative
to the other gap diagram types -- it's arithmetic (linear-map a `[0,1]` coordinate to a grid
cell) rather than a new box/tree/routing layout, closer in spirit to VIEWMD-0048's (xychart) axis
math than to anything `viewmd/mermaid/grid/canvas.py` does today.

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

## Acceptance / verification

- Unit tests for the parser: `title`, both axis lines, all four quadrant labels, one or more data
  points with decimal coordinates, and a malformed data-point line (requirement 7) skipped rather
  than aborting the chart.
- A rendered fixture reproducing the `Priority Matrix` example above (marker placement and quadrant
  labels; exact spacing is an implementation choice, per Design notes), hand-verified (per
  Non-goals, no oracle to differential-test against; termaid's own output is a cross-check, not a
  target to match exactly).
- A fixture with two data points close enough to land in the same cell, confirming the chart still
  renders without crashing (requirement 7's tolerance, per Non-goals' collision-handling scope).
- A malformed `quadrantChart` fence (e.g. missing both axis lines entirely) falls back to showing
  the raw fence rather than crashing viewmd.
- `./run-tests.sh` green.

## Peer review

