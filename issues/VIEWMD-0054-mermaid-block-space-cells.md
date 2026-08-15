---
id: VIEWMD-0054
title: Render Mermaid block-beta space/blank grid cells
status: proposed
area: [render, mermaid]
effort: low
created: 2026-08-15
updated: 2026-08-15
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0040]
supersedes: []
changelog:
reason:
---

# Render Mermaid block-beta space/blank grid cells

## Summary

Extend the `block-beta` renderer added by [VIEWMD-0040](VIEWMD-0040-mermaid-block-beta-diagrams.md)
to parse `space` and `space:N` directives, reserving one (or `N`) grid column-widths as
intentionally blank cells during layout, without drawing a box there.

## Motivation / problem

VIEWMD-0040 scoped this out explicitly ("Composite/nested blocks... and explicit `space` blocks
(blank grid cells) -- neither appears in the reference examples driving this issue"). A `space`
entry consumes grid position the same way a block declaration does (advancing the row/column
cursor and counting toward a row's fill-and-wrap threshold), but places nothing to draw. This is a
placement-logic addition on top of VIEWMD-0040's existing column/wrap/span machinery
(requirements 3-6), not new box-drawing.

## Requirements

1. MUST parse a bare `space` token as consuming exactly 1 grid column at the current cursor
   position, advancing placement the same way a 1-column block would (VIEWMD-0040 requirement 4),
   but drawing nothing there.
2. MUST parse a `space:N` token (mirroring the `:N` span suffix on blocks, VIEWMD-0040 requirement
   5) as consuming `N` grid columns at the current cursor position, drawing nothing.
3. MUST NOT let a `space`/`space:N` entry participate in per-column width equalization
   (VIEWMD-0040 requirement 9) -- it has no content, so it neither contributes to nor is affected
   by a column's computed width beyond reserving the column position itself.
4. MUST render the reserved width as blank columns (matching the surrounding inter-block gap
   convention) rather than shifting subsequent blocks in the row leftward.
5. MUST leave a `block-beta` fence whose `space` usage fails to parse (e.g. `space:0`, a negative
   or non-integer span) untouched, falling back to the raw fence.
6. MUST NOT change rendering for a diagram with no `space` entries.

## Non-goals

- Any interaction between `space` and the block-arrow shape or composite/nested blocks -- those
  are separate follow-ups ([VIEWMD-0056](VIEWMD-0056-mermaid-block-arrow-shape.md),
  [VIEWMD-0057](VIEWMD-0057-mermaid-block-composite-nested-blocks.md)); this issue only needs
  `space` to compose with plain rectangle blocks.

## Design notes / links

Mockup:

```
--- source ---
block-beta
    columns 3
    A["One"] space B["Two"]
--- rendered ---

  ┌──────────┐                    ┌──────────┐
  │   One    │                    │   Two    │
  └──────────┘                    └──────────┘
```

The blank middle column occupies the same width + gap a real block there would have, so `B`'s
horizontal position is identical to what it would be if column 2 held an (undrawn) block.

```
--- source ---
block-beta
    columns 3
    A["One"] space:2
    B["Two"] C["Three"] D["Four"]
--- rendered ---

  ┌──────────┐
  │   One    │
  └──────────┘

  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │   Two    │    │  Three   │    │   Four   │
  └──────────┘    └──────────┘    └──────────┘
```

## Acceptance / verification

- Unit tests for the parser: bare `space`, `space:N`, and a malformed span (`space:0`) falling
  back to the raw fence.
- A rendered fixture for a `space` entry mid-row, and one for a `space:N` entry that fills the
  remainder of a row, confirming subsequent blocks land at the correct horizontal position.
- `./run-tests.sh` green.

## Peer review
