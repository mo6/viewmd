---
id: VIEWMD-0057
title: Render Mermaid block-beta composite/nested blocks
status: proposed
area: [render, mermaid]
effort: high
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

# Render Mermaid block-beta composite/nested blocks

## Summary

Add support for a `block-beta` block that itself contains a nested sub-grid of blocks (a composite
block), so a declared block can recursively hold its own `columns`/span/wrap layout the same way
the top-level diagram does.

## Motivation / problem

VIEWMD-0040's Non-goals explicitly excludes "Composite/nested blocks (`block-beta` blocks
containing other blocks)... neither appears in the reference examples driving this issue." Unlike
the other VIEWMD-0040 follow-ups ([VIEWMD-0053](VIEWMD-0053-mermaid-block-shapes-and-styling.md)
through [VIEWMD-0056](VIEWMD-0056-mermaid-block-arrow-shape.md)), this is not a small addition on
top of VIEWMD-0040's grid-placement logic -- a composite block is a block whose content is itself
a `block-beta` grid, recursively, so this issue's layout/sizing work is comparable in scope to
VIEWMD-0040 itself, not a fast-follow.

## Requirements

1. MUST parse a composite block declaration (`id` followed by a nested block list and a closing
   `end`, per Mermaid's grammar) as a block whose content is itself a grid of blocks, reusing
   VIEWMD-0040's existing declaration/`columns`/span/wrap parsing recursively for the nested
   content rather than a separate parser.
2. MUST compute a composite block's own box size as large enough to contain its fully-laid-out
   nested grid (nested blocks' widths, gaps, and rows) plus an outer border/padding margin, the
   same way a top-level diagram's overall drawing size is derived from its grid today.
3. MUST support at least one level of nesting (a composite block containing plain rectangle
   blocks); arbitrarily deep nesting MAY be supported but is not required for acceptance if the
   maintainer-supplied reference examples don't exercise it.
4. MUST place a composite block into its parent grid the same way any other block is placed
   (VIEWMD-0040 requirements 3-6, 9) -- from the parent's perspective, a composite block is a
   single grid cell whose width is requirement 2's computed size.
5. MUST leave a `block-beta` fence whose composite-block syntax fails to parse (unterminated
   nesting, empty composite block, etc.) untouched, falling back to the raw fence.
6. MUST NOT change rendering for a `block-beta` diagram with no composite blocks, or for any other
   existing Mermaid diagram type.

## Non-goals

- Edges crossing into or out of a composite block's interior (an edge from a top-level block to a
  block nested inside a composite block) -- only edges between blocks at the same grid level are
  in scope, matching VIEWMD-0040's existing same-row edge restriction.
- Composite blocks using the block-arrow shape ([VIEWMD-0056](VIEWMD-0056-mermaid-block-arrow-shape.md))
  as their own outer shape.
- Styling ([VIEWMD-0053](VIEWMD-0053-mermaid-block-shapes-and-styling.md)) applied to a composite
  block's border, beyond whatever plain-rectangle styling already covers.

## Design notes / links

Mockup (illustrative -- exact border/margin sizing around the nested grid is an implementation
decision, not fixed by this issue):

```
--- source ---
block-beta
    D
        E["Inner One"]
        F["Inner Two"]
    end
--- rendered (illustrative) ---

  ┌────────────────────────────────────┐
  │  ┌────────────┐    ┌────────────┐  │
  │  │ Inner One  │    │ Inner Two  │  │
  │  └────────────┘    └────────────┘  │
  └────────────────────────────────────┘
```

Given this issue's size, it is a strong candidate for its own design-notes pass (e.g. confirming
recursion depth, nested-`columns` interaction, and margin sizing against maintainer-supplied
reference examples) before implementation, separate from the smaller VIEWMD-0053/0054/0055/0056
follow-ups.

## Acceptance / verification

- Unit tests for the parser: a single-level composite block, a composite block containing a
  `columns N` directive of its own, and a malformed composite block (unterminated, empty) falling
  back to the raw fence.
- A rendered fixture for a composite block, hand-verified against maintainer-supplied reference
  output obtained before implementation starts (no upstream oracle, per VIEWMD-0040's posture).
- A fixture confirming a composite block correctly occupies a single cell in its parent's grid
  (span/column-equalization interaction with VIEWMD-0040 requirements 9-10).
- `./run-tests.sh` green.

## Peer review
