---
id: VIEWMD-0046
title: Render Mermaid treemap diagrams
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

# Render Mermaid treemap diagrams

## Summary

Add a Mermaid diagram type -- `treemap-beta` -- alongside the existing flowchart, sequence, and ER
renderers (`viewmd/mermaid/{flowchart,sequence,er}/`) and the diagram types proposed in
[VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md) through
[VIEWMD-0042](VIEWMD-0042-mermaid-gitgraph-diagrams.md). A Mermaid treemap
(https://mermaid.js.org/syntax/treemap.html) shows nested, proportionally-sized boxes: each
top-level section is a labeled outer box, subdivided into leaf boxes sized by value relative to
their siblings.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `treemap-beta` fence
today -- it falls through every `_is_*_diagram` sniff. A treemap's boxes are close cousins of a
flowchart subgraph (`viewmd/mermaid/flowchart/`, an outer labeled box containing inner boxes) but
the sizing rule is new: subgraph child layout today doesn't proportion box width to a numeric
value, which a treemap requires.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `treemap-beta`
   (`viewmd/mermaid/treemap/parser.py:sniff`, following the `sniff`/`parse`/`render` module shape
   already used by the other diagram packages) and wire it into `viewmd/mermaid/__init__.py:render`
   alongside the existing sniffs.
2. MUST parse indentation-based nesting: a quoted `"<label>"` line with no `: value` is a section
   (internal node), one whose more-indented children are parsed recursively; a quoted
   `"<label>": <value>` line is a leaf with a numeric value.
3. MUST support nesting more than one level deep (section containing a section containing leaves).
4. MUST compute a section's own total value as the sum of its children's values (recursively for
   nested sections), used for proportional sizing at each level.
5. MUST render each top-level section as its own labeled outer box (dashed/dotted border, to
   visually distinguish a container from a leaf), containing its leaf boxes (solid border) side by
   side, each leaf's width proportional to its value's share of its parent's total, each leaf
   showing its label and value.
6. MUST tolerate `%%` comment lines and blank lines anywhere in the block, ignored during parsing.
7. MUST leave a `treemap-beta` fence whose content fails to parse untouched (fall back to showing
   the raw fence), same fallback discipline as the other Mermaid renderers'
   MUST-NOT-crash requirement.
8. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- Color/theme differentiation between sections -- viewmd's existing Mermaid renderers do not use
  ANSI color today, and this issue does not introduce it.
- Exact proportional-area (2D) packing -- a single row of width-proportional leaf boxes per section
  (as termaid renders it, see reference example) is sufficient; true squarified-treemap area
  packing is not required.
- A leaf whose truncated (narrow) box can't fit both label and value legibly -- best-effort
  truncation (already the convention used for wide/CJK labels elsewhere in viewmd's Mermaid
  renderers, see `viewmd/mermaid/er/`) is sufficient; no dedicated overflow UI is required.
- Matching any upstream reference implementation byte-for-byte -- the local `mermaid-ascii` Go
  oracle used for differential-testing flowchart/sequence/ER has no treemap support, so fixtures
  here are hand-authored/visually-verified, same posture as VIEWMD-0032 onward. termaid's own
  rendering (below) is a useful cross-check, not an oracle to match exactly.

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a
`_is_treemap_diagram`/`_parse_treemap`/`_render_treemap` import trio and a new `if` branch,
mirroring the `er` branch (parse-then-render, catching a module-local `ParseError` into
`MermaidError`). New module lives at `viewmd/mermaid/treemap/` (`parser.py`, `renderer.py`),
sibling to the other diagram packages. The outer dashed-border section box is new vocabulary for
`viewmd/mermaid/grid/canvas.py` (today's box styles are all solid or double-line, per
`viewmd/mermaid/flowchart/`'s node shapes) -- worth checking whether a dashed variant of the
existing box-drawing helper is a small addition rather than a new code path.

### Reference example (termaid's actual output, `~/Documents/Projects/termaid`)

```
--- source ---
treemap-beta
    "Frontend"
        "React": 40
        "CSS": 15
    "Backend"
        "API": 35
        "Auth": 10
--- rendered ---
┌┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┐ ┌┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┐
┆           Frontend           ┆ ┆         Backend         ┆
┆┌───────────────────┐ ┌──────┐┆ ┆┌─────────────────┐ ┌───┐┆
┆│       React       │ │ CSS  │┆ ┆│       API       │ │Au…│┆
┆│        40         │ │  15  │┆ ┆│       35        │ │10 │┆
┆└───────────────────┘ └──────┘┆ ┆└─────────────────┘ └───┘┆
└┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┘ └┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┘
```

Note the `"Auth"` leaf (value 10, smallest box) truncates its label to `Au…` rather than
overflowing its border -- termaid's own truncation convention (requirement/Non-goals above); the
exact ellipsis glyph and truncation point are an implementation choice for this issue, not
dictated by this reference.

## Acceptance / verification

- Unit tests for the parser: flat leaves with no section, one level of section nesting, nesting two
  or more levels deep, a section's computed total value (sum of children, recursive for nested
  sections), and `%%` comments / blank lines ignored.
- A rendered fixture reproducing the `Frontend`/`Backend` example above, hand-verified (per
  Non-goals, no oracle to differential-test against; termaid's own output is a cross-check, not a
  target to match exactly).
- A fixture with a label too long for its proportional box width, confirming truncation doesn't
  destroy the box border (matching the existing wide-label discipline in `viewmd/mermaid/er/`).
- A malformed `treemap-beta` fence (e.g. a leaf line missing its `:` separator) falls back to
  showing the raw fence rather than crashing viewmd.
- `./run-tests.sh` green.

## Peer review

