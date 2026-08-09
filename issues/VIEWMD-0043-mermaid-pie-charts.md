---
id: VIEWMD-0043
title: Render Mermaid pie charts
status: proposed
area: [render, mermaid]
effort: low
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

# Render Mermaid pie charts

## Summary

Add a Mermaid diagram type -- `pie` -- alongside the existing flowchart, sequence, and ER
renderers (`viewmd/mermaid/{flowchart,sequence,er}/`) and the diagram types proposed in
[VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md) through
[VIEWMD-0042](VIEWMD-0042-mermaid-gitgraph-diagrams.md). A Mermaid `pie` chart
(https://mermaid.js.org/syntax/pie.html) is a set of labeled slices with numeric values; since a
circular pie is not something box-drawing/ANSI text can render legibly, this renders each slice as
a horizontal bar sized to its share of the total, labeled with its percentage -- the same choice
the Python project `termaid` (https://github.com/lukilabs/beautiful-mermaid,
`~/Documents/Projects/termaid`, a sibling terminal-Mermaid renderer, `src/termaid/renderer/piechart.py`)
already made for the same reason.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `pie` fence today --
it falls through every `_is_*_diagram` sniff. Pie charts are a common, simple Mermaid diagram type
and, of the eight diagram types termaid supports that viewmd does not yet track
(state, architecture, pie, treemap, mindmap, quadrant, xychart, packet), this is the smallest: no
layout algorithm is needed, only proportional bar-width math and percentage formatting.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `pie` (`viewmd/mermaid/pie/parser.py:sniff`,
   following the `sniff`/`parse`/`render` module shape already used by the other diagram packages)
   and wire it into `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
2. MUST parse an optional `title <text>` line, rendered above the chart.
3. MUST parse an optional `showData` modifier on the `pie` line itself (`pie showData`) that, when
   present, appends each slice's raw value next to its percentage.
4. MUST parse one `"<label>" : <value>` line per slice, where `<value>` is a non-negative integer
   or decimal.
5. MUST render one row per slice, in declaration order: the label right-aligned in a fixed-width
   column (sized to the longest label), a bar filled proportionally to `value / sum(values)` against
   the widest bar in the chart, and a trailing percentage (one decimal place, matching Mermaid's own
   `%.1f%%` convention visible in the reference example below).
6. MUST tolerate `%%` comment lines and blank lines anywhere in the block, ignored during parsing.
7. MUST leave a `pie` fence whose content fails to parse (e.g. a slice line missing its `:`
   separator, or a negative value) untouched -- fall back to showing the raw fence, same fallback
   discipline as the other Mermaid renderers' MUST-NOT-crash requirement.
8. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- An actual circular pie rendering -- horizontal bars are the deliberate choice here, matching
  termaid's own reasoning (see Summary); a circular ASCII-art pie is not legible at typical
  terminal font aspect ratios.
- Slice ordering by value (Mermaid renders slices in declaration order for the legend; this issue
  keeps that order rather than sorting descending by value).
- Color/theme differentiation between slices -- viewmd's existing Mermaid renderers do not use
  ANSI color today, and this issue does not introduce it.
- Matching any upstream reference implementation byte-for-byte -- the local `mermaid-ascii` Go
  oracle used for differential-testing flowchart/sequence/ER has no pie-chart support, so fixtures
  here are hand-authored/visually-verified, same posture as VIEWMD-0032 onward. termaid's own
  rendering (below) is a useful cross-check, not an oracle to match exactly.

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a
`_is_pie_diagram`/`_parse_pie`/`_render_pie` import trio and a new `if` branch, mirroring the `er`
branch (parse-then-render, catching a module-local `ParseError` into `MermaidError`). New module
lives at `viewmd/mermaid/pie/` (`parser.py`, `renderer.py`), sibling to the other diagram packages.
No new layout primitive is needed -- this is closer to a formatting problem (label column width,
proportional bar-fill width, percentage formatting) than a `viewmd/mermaid/grid/` box/arrow layout
problem, unlike every other diagram type viewmd renders today.

### Reference example (termaid's actual output, `~/Documents/Projects/termaid`)

```
--- source ---
pie title Pets adopted by volunteers
    "Dogs" : 386
    "Cats" : 85
    "Rats" : 15
--- termaid's rendered bar-chart form ---
  Dogs┃████████████████████████████████  79.4%
  Cats┃▓▓▓▓▓▓▓  17.5%
  Rats┃░   3.1%
```

termaid right-aligns the label directly against the bar's leading edge (`┃`) rather than in a
separate padded column; viewmd's exact column layout is a design decision left open for this
issue's implementation, not dictated by this reference.

## Acceptance / verification

- Unit tests for the parser: `title`, `showData` present/absent, integer and decimal values, `%%`
  comments and blank lines ignored, and an empty `pie` block (zero slices).
- A rendered fixture reproducing the reference example above (percentages, not raw termaid glyph
  choices, since viewmd's bar-fill glyph is its own decision).
- A rendered fixture with `showData` set, confirming raw values appear alongside percentages.
- A malformed `pie` fence (e.g. a slice line missing its `:` separator, or a negative value) falls
  back to showing the raw fence rather than crashing viewmd.
- `./run-tests.sh` green.

## Peer review

