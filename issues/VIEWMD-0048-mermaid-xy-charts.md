---
id: VIEWMD-0048
title: Render Mermaid XY charts
status: proposed
area: [render, mermaid]
effort: high
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

# Render Mermaid XY charts

## Summary

Add a Mermaid diagram type -- `xychart-beta` -- alongside the existing flowchart, sequence, and ER
renderers (`viewmd/mermaid/{flowchart,sequence,er}/`) and the diagram types proposed in
[VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md) through
[VIEWMD-0042](VIEWMD-0042-mermaid-gitgraph-diagrams.md). A Mermaid XY chart
(https://mermaid.js.org/syntax/xyChart.html) plots one or more bar and/or line datasets against a
shared category x-axis and a numeric y-axis, optionally in a horizontal-bar orientation.

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

1. MUST recognize a ` ```mermaid ` fence beginning with `xychart-beta` (optionally followed by
   ` horizontal`, requirement 6) via `viewmd/mermaid/xychart/parser.py:sniff`, following the
   `sniff`/`parse`/`render` module shape already used by the other diagram packages, and wire it
   into `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
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
6. MUST parse the ` horizontal` modifier on the `xychart-beta` line and, when present, transpose
   the chart: categories run down the left edge instead of along the bottom, and bars extend
   rightward instead of upward.
7. MUST render bar datasets as vertical (or, per requirement 6, horizontal) block-character bars
   scaled to the y-axis range, one bar (or bar group, for combo charts) per category, with y-axis
   tick labels and an x-axis category-label row; MUST render line datasets as a connected sequence
   of points across the same axes; each mark type MUST have a `use_ascii`-safe fallback per the
   existing `use_ascii` convention used elsewhere in `viewmd/mermaid/`.
8. MUST leave an `xychart-beta` fence whose content fails to parse (including a `y-axis`/`x-axis`
   range or category list that fails to parse -- see the malformed-input handling already present
   in termaid's own parser, reference below) untouched (fall back to showing the raw fence), same
   fallback discipline as the other Mermaid renderers' MUST-NOT-crash requirement.
9. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- More than one `bar` and one `line` dataset combined in a single chart (i.e. multiple bar series
  side by side, or multiple line series overlaid) -- Mermaid's spec allows multiple datasets of
  each kind; this issue's v1 scope is the single-bar/single-line combo case termaid's own test
  suite exercises (reference below), with true multi-series support deferred to a follow-up issue.
- Color/theme differentiation between datasets -- viewmd's existing Mermaid renderers do not use
  ANSI color today, and this issue does not introduce it.
- `%%{init}%%` sizing/theming overrides.
- Matching any upstream reference implementation byte-for-byte -- the local `mermaid-ascii` Go
  oracle used for differential-testing flowchart/sequence/ER has no XY-chart support, so fixtures
  here are hand-authored/visually-verified, same posture as VIEWMD-0032 onward. termaid's own
  rendering (below) is a useful cross-check, not an oracle to match exactly.

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a
`_is_xychart_diagram`/`_parse_xychart`/`_render_xychart` import trio and a new `if` branch,
mirroring the `er` branch (parse-then-render, catching a module-local `ParseError` into
`MermaidError`). New module lives at `viewmd/mermaid/xychart/` (`parser.py`, `renderer.py`),
sibling to the other diagram packages. This is the largest single new renderer among the eight gap
diagram types (see Motivation) -- worth considering whether to land the `bar`-only case first as
its own reviewable increment before adding `line`/combo/`horizontal`, given the size, rather than
one large patch; that sequencing is left to implementation, not mandated by a Requirement.

### Reference examples (termaid's actual output, `~/Documents/Projects/termaid`)

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
whole-block rows -- a legibility detail worth matching for reasonable vertical resolution, though
the exact glyph choice is an implementation decision for this issue.

Malformed range input (from `tests/test_xychart.py:TestMalformedXYChartInput`), which termaid's own
parser tolerates by leaving the range unset rather than raising:

```
xychart-beta
    x-axis "t" 0.1.2 --> 10
    bar [1, 2]
```

parses with `x_range is None` (termaid tracks an optional numeric x-range analogous to the y-range,
unused by the category-axis form in requirement 3/4 above) rather than raising -- illustrating the
malformed-input tolerance requirement 8 asks for at the chart level, one layer up.

## Acceptance / verification

- Unit tests for the parser: bare and titled `x-axis`, explicit and auto-scaled (omitted)
  `y-axis`, a `bar`-only chart, a `line`-only chart, a combo bar+line chart, the ` horizontal`
  modifier, and a malformed axis line (requirement 8) tolerated without raising.
- A rendered fixture reproducing the `Sales` bar-chart example above, hand-verified (per Non-goals,
  no oracle to differential-test against; termaid's own output is a cross-check, not a target to
  match exactly).
- A rendered fixture for a combo bar+line chart and for the `horizontal` orientation.
- A fixture confirming `use_ascii` mode's fallback glyphs for both bar and line marks.
- A malformed `xychart-beta` fence (e.g. a dataset with fewer values than categories) falls back to
  showing the raw fence rather than crashing viewmd.
- `./run-tests.sh` green.

## Peer review

