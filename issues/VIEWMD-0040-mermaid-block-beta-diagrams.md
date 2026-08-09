---
id: VIEWMD-0040
title: Render Mermaid block-beta diagrams
status: proposed
area: [render, mermaid]
effort: medium
created: 2026-08-08
updated: 2026-08-08
accepted_by:
accepted_at:
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Render Mermaid block-beta diagrams

## Summary

Add a seventh Mermaid diagram type -- `block-beta` -- alongside the existing flowchart, sequence,
and ER renderers (`viewmd/mermaid/{flowchart,sequence,er}/`) and the diagram types proposed in
[VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md), [VIEWMD-0033](VIEWMD-0033-mermaid-user-journey-diagrams.md),
[VIEWMD-0034](VIEWMD-0034-mermaid-kanban-diagrams.md). A block diagram
(https://mermaid.js.org/syntax/block.html) lays out a set of labeled boxes onto an explicit or
implicit grid -- optionally spanning multiple columns -- with a `columns N` directive controlling
row width, and MAY connect two blocks with a flowchart-style arrow. This is a first version -- see
Non-goals for what's deliberately left out.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `block-beta` fence
today -- it falls through every `_is_*_diagram` sniff. A block diagram is closer to a grid of
boxes than to a routed graph: unlike a flowchart, position comes from declaration order and
`columns`/span counts, not from edges, so it doesn't fit naturally as flowchart syntax sugar and
needs its own parse/layout path (though it can reuse flowchart's existing box-drawing and
arrowhead primitives for the individual blocks and the optional connector).

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `block-beta`
   (`viewmd/mermaid/block/parser.py:sniff`, following the `sniff`/`parse`/`render` module shape
   already used by the other diagram packages) and wire it into
   `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
2. MUST parse a block declaration `id["label"]` (quoted string label in brackets, the only shape
   this issue's reference examples use -- see Non-goals for other Mermaid block shapes) in
   declaration order.
3. MUST parse a `columns N` directive, fixing the grid's column count for every block declared
   after it until the next `columns` directive (or end of diagram).
4. MUST place blocks left-to-right, top-to-bottom into the grid implied by the current column
   count, wrapping to a new row once a row's declared blocks (accounting for span widths, per
   requirement 5) fill the current column count.
5. MUST parse a block's optional `:N` column-span suffix (`A["Header"]:3`) and reserve that many
   grid columns for it, per the second reference example below.
6. MUST support a diagram with no `columns` directive at all (first and fourth reference examples
   below), laying every declared block into a single row in declaration order.
7. MUST parse a directed edge `A-->B` between two already-declared block ids and render it as a
   horizontal connector with an arrowhead between the two blocks, reusing the existing flowchart
   arrowhead glyph (`viewmd/mermaid/grid/canvas.py`/`viewmd/mermaid/flowchart/`) rather than
   inventing a new one, per the fourth reference example below.
8. MUST render each block as its own box (`┌─┐│└┘`, Unicode by default / ASCII with
   `use_ascii=True` matching the other Mermaid renderers' existing `--ascii` behavior), its label
   centered inside, sized to its content plus the existing flowchart box padding convention.
9. MUST render a spanning block's box width as wide as the combined width (plus inter-column gap)
   of the columns it spans, per the second reference example below.
10. MUST leave a `block-beta` fence whose content fails to parse untouched (fall back to showing
    the raw fence), same fallback discipline as the other Mermaid renderers' MUST-NOT-crash
    requirement.
11. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- Any block shape other than the quoted-label rectangle (`id["label"]`) used throughout this
  issue's reference examples -- block-beta's round/stadium/diamond/hexagon/arrow-shaped blocks
  (mirroring flowchart's shape vocabulary) and its literal "block-arrow" shape are follow-up work,
  not required for this issue's acceptance.
- Composite/nested blocks (`block-beta` blocks containing other blocks) and explicit `space`
  blocks (blank grid cells) -- neither appears in the reference examples driving this issue.
- Edge labels on the `A-->B` connector (`A-- "label" -->B`), or any arrow style besides a plain
  solid arrow (dotted, thick, bidirectional).
- `classDef`/`style`/`class` styling directives for blocks.
- Vertical/non-horizontal edges between blocks not sitting in the same row.
- Terminal-width responsiveness/reflow -- fixed-width rendering, matching the other Mermaid
  renderers' current posture.
- Matching any upstream reference implementation byte-for-byte -- the local `mermaid-ascii` Go
  oracle used for differential testing the flowchart/sequence/ER ports has no `block-beta`
  support, so fixtures here are necessarily hand-authored against the maintainer-supplied
  reference examples below (same posture as VIEWMD-0032/0033/0034).

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a
`_is_block_diagram`/`_parse_block`/`_render_block` import trio and a seventh `if` branch,
mirroring the `er` branch (parse-then-render, catching a module-local `ParseError` into
`MermaidError`). New module lives at `viewmd/mermaid/block/` (`parser.py`, `renderer.py`), sibling
to the other diagram packages. Box-drawing and the arrowhead glyph should be reused from
`viewmd/mermaid/grid/canvas.py` / `viewmd/mermaid/flowchart/` (`draw_box`, the flowchart
connector-drawing helpers) rather than reimplemented, since block-beta's individual boxes and
its one supported edge type are visually identical to a flowchart rectangle node and a plain
`-->` edge -- the new code this issue adds is the grid-placement logic (columns/span/wrap), not a
new box-rendering primitive.

### Reference examples (maintainer-supplied)

```
--- source ---
block-beta
    A["Hello World"]
    B["Goodbye"]
--- rendered ---

  ┌─────────────┐    ┌──────────┐
  │ Hello World │    │ Goodbye  │
  └─────────────┘    └──────────┘
```

```
--- source ---
block-beta
    columns 3
    A["Header"]:3
    B["Left"] C["Center"] D["Right"]
--- rendered ---

  ┌──────────────────────────────────────────┐
  │                  Header                  │
  └──────────────────────────────────────────┘

  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │   Left   │    │  Center  │    │  Right   │
  └──────────┘    └──────────┘    └──────────┘
```

```
--- source ---
block-beta
    columns 3
    A["Frontend"] B["API"] C["Database"]
    D["Cache"] E["Queue"] F["Worker"]
--- rendered ---

  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │ Frontend │    │   API    │    │ Database │
  └──────────┘    └──────────┘    └──────────┘

  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │  Cache   │    │  Queue   │    │  Worker  │
  └──────────┘    └──────────┘    └──────────┘
```

```
--- source ---
block-beta
    A["Source"]
    B["Target"]
    A-->B
--- rendered ---

  ┌──────────┐    ┌──────────┐
  │  Source  │───►│  Target  │
  └──────────┘    └──────────┘
```

Open questions for maintainer sign-off: (a) the exact inter-block horizontal gap and inter-row
blank-line count implied by the reference examples (4 columns / 1 blank line respectively, by
inspection) should be treated as the concrete spec unless the maintainer says otherwise; (b)
whether same-row block widths must always be uniform (as in the "Left"/"Center"/"Right" example,
all width 10 despite "Center" needing less) or should size independently per label when labels
differ more than in the reference examples -- the reference examples don't disambiguate this
since "Left"/"Center"/"Right"/"Frontend"/"API"/etc. happen to be close in length; (c) how a
spanning block's width should be computed when the columns it spans would naturally have been
uneven widths (not exercised by the `:3`-spans-the-whole-row case in the second example, where
this doesn't yet come up).

## Acceptance / verification

- Unit tests for the parser: bare block declarations, `columns N` directives (including a
  mid-diagram change to a new column count), `:N` span parsing, and `A-->B` edge parsing
  referencing already-declared ids.
- A rendered fixture for each of the four reference examples above, hand-verified against the
  maintainer-supplied output (per Non-goals, no oracle to differential-test against).
- A fixture covering a diagram with more declared blocks than fit one row under a `columns N`
  directive, confirming correct wrap to a second row.
- A malformed `block-beta` fence (e.g. `A-->B` referencing an undeclared id) falls back to showing
  the raw fence rather than crashing viewmd.
- `./run-tests.sh` green.

## Peer review

