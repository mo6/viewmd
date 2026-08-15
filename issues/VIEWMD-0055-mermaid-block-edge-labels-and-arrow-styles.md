---
id: VIEWMD-0055
title: Render Mermaid block-beta edge labels and arrow styles
status: proposed
area: [render, mermaid]
effort: medium
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

# Render Mermaid block-beta edge labels and arrow styles

## Summary

Extend the `block-beta` connector support added by [VIEWMD-0040](VIEWMD-0040-mermaid-block-beta-diagrams.md)
requirement 7 (plain `A-->B`) to parse an inline edge label (`A -->|"label"| B`) and the remaining
Mermaid arrow styles -- dotted (`-.->`),  thick (`==>`), undirected (`---`), and bidirectional
(`<-->`) -- between two already-declared, same-row block ids.

## Motivation / problem

VIEWMD-0040 scoped its connector support to a single plain directed arrow ("Edge labels on the
`A-->B` connector... or any arrow style besides a plain solid arrow (dotted, thick,
bidirectional)" is listed as a Non-goal). Flowchart already parses and renders this full edge
vocabulary for its own `-->`/`-.->`/`==>`/`---`/`<-->` edges and their labels; block-beta's single
supported edge shape (a horizontal connector between two boxes in the same row) is visually
identical to a flowchart edge between two horizontally-adjacent nodes, so this is primarily reuse
of flowchart's existing edge-style parsing and glyph selection.

## Requirements

1. MUST parse an inline edge label `A -->|"label"| B` (and the equivalent for each arrow style
   below) between two already-declared block ids sitting in the same row, reusing flowchart's
   existing edge-label parsing rather than reimplementing it.
2. MUST render the edge label centered in the horizontal gap between the two blocks, on its own
   line above (or replacing, if the gap is exactly wide enough) the connector line, matching
   flowchart's existing edge-label placement convention for a horizontal edge.
3. MUST parse and render the dotted (`-.->`), thick (`==>`), undirected (`---`), and bidirectional
   (`<-->`) arrow styles between two same-row block ids, reusing flowchart's existing per-style
   connector glyphs (`viewmd/mermaid/flowchart/`) rather than inventing new ones.
4. MUST widen the inter-block gap for a given row when an edge label there is wider than the
   existing fixed gap (VIEWMD-0040's 4-column convention), so the label is never truncated or
   overlapping the adjacent boxes.
5. MUST leave VIEWMD-0040's existing plain `A-->B` (no label) behavior unchanged when no label or
   alternate style is present.
6. MUST leave a `block-beta` fence whose edge syntax fails to parse (e.g. a label or style on an
   edge referencing an undeclared id, or between two blocks not in the same row) untouched,
   falling back to the raw fence -- consistent with VIEWMD-0040's existing same-row-only Non-goal
   for edges.
7. MUST NOT change rendering for a `block-beta` diagram using only the plain unlabeled `A-->B` edge
   VIEWMD-0040 already supports, or for any other Mermaid diagram type.

## Non-goals

- Vertical/non-horizontal edges (blocks not sitting in the same row) -- still out of scope, per
  VIEWMD-0040's own Non-goals; this issue only adds label/style richness to the same-row case.
- Edges touching the block-arrow shape ([VIEWMD-0056](VIEWMD-0056-mermaid-block-arrow-shape.md)) or
  a block inside a composite/nested block
  ([VIEWMD-0057](VIEWMD-0057-mermaid-block-composite-nested-blocks.md)).

## Design notes / links

Mockup (edge label):

```
--- source ---
block-beta
    A["Source"]
    B["Target"]
    A -->|"ok"| B
--- rendered ---

  ┌──────────┐  ok  ┌──────────┐
  │  Source  │─────►│  Target  │
  └──────────┘      └──────────┘
```

Mockup (arrow styles, illustrative -- exact glyphs reused from flowchart's existing per-style
connector rendering):

```
--- source ---
block-beta
    A["X"]
    B["Y"]
    A -.-> B
--- rendered ---

  ┌──────────┐    ┌──────────┐
  │    X     │╌╌╌►│    Y     │
  └──────────┘    └──────────┘
```

## Acceptance / verification

- Unit tests for the parser: an edge label, each of the four additional arrow styles, and a
  malformed edge (label/style on a cross-row or undeclared-id edge) falling back to the raw fence.
- A rendered fixture per arrow style and one for an edge label, hand-verified (no upstream oracle,
  per VIEWMD-0040's posture).
- A rendered fixture confirming gap-widening when an edge label is wider than the default 4-column
  gap.
- `./run-tests.sh` green.

## Peer review
