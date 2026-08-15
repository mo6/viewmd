---
id: VIEWMD-0056
title: Render Mermaid block-beta block-arrow shape
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

# Render Mermaid block-beta block-arrow shape

## Summary

Add support for Mermaid's "block-arrow" shape (`A>["label"]`, `A<["label"]`, and up/down
variants) -- a directional chevron-style box distinct from every shape flowchart already renders
-- to the `block-beta` renderer added by [VIEWMD-0040](VIEWMD-0040-mermaid-block-beta-diagrams.md).

## Motivation / problem

VIEWMD-0040's Non-goals list block-beta's "literal 'block-arrow' shape" as follow-up work.
Unlike the shapes covered by [VIEWMD-0053](VIEWMD-0053-mermaid-block-shapes-and-styling.md), the
block-arrow shape has no flowchart equivalent to reuse (`viewmd/mermaid/flowchart/parser.py`'s
`NodeShape` enum has no chevron/arrow-box shape) -- it needs a new box-glyph primitive in
`viewmd/mermaid/grid/canvas.py`, sized and pointed per its declared direction.

## Requirements

1. MUST parse `A>["label"]` (arrow pointing right) and `A<["label"]` (arrow pointing left) block
   declarations. Up/down variants, if any exist in the current Mermaid grammar beyond `>`/`<`,
   MUST be confirmed against the maintainer-supplied reference examples this issue is accepted
   with before being included in scope -- absent those, this issue covers left/right only.
2. MUST render a right-pointing block-arrow as a box whose right edge comes to a chevron point (and
   symmetrically for left-pointing), sized to its label plus the existing block minimum-width/
   padding rules ([VIEWMD-0040](VIEWMD-0040-mermaid-block-beta-diagrams.md) requirements 8-9),
   applied to the shape's usable interior rather than its full bounding width.
3. MUST add a `block_arrow` (or equivalent) shape entry to `viewmd/mermaid/grid/canvas.py`'s
   glyph table, following the existing per-shape `_box_glyphs`/`draw_box` pattern rather than a
   parallel drawing path.
4. MUST support both Unicode and `--ascii` rendering for the new shape, matching every other
   Mermaid shape's existing `use_ascii` behavior.
5. MUST participate in the same grid placement, column-span, and per-column width-equalization
   rules as a rectangle block ([VIEWMD-0040](VIEWMD-0040-mermaid-block-beta-diagrams.md)
   requirements 3-6, 9).
6. MUST leave a `block-beta` fence whose block-arrow syntax fails to parse untouched, falling back
   to the raw fence.
7. MUST NOT change rendering for a rectangle block or any other existing Mermaid diagram type.

## Non-goals

- Any styling (`style`/`classDef`) applied to a block-arrow shape -- covered, if at all, by a
  future extension of [VIEWMD-0053](VIEWMD-0053-mermaid-block-shapes-and-styling.md).
- A block-arrow shape as an edge endpoint inside composite/nested blocks
  ([VIEWMD-0057](VIEWMD-0057-mermaid-block-composite-nested-blocks.md)).

## Design notes / links

Mockup (illustrative -- exact chevron glyph choice is an implementation decision, not fixed by
this issue):

```
--- source ---
block-beta
    A>["Right"]
    B<["Left"]
--- rendered (illustrative) ---

  ┌─────────┐      ╱────────┐
  │  Right   >     │  Left  ╲
  └─────────┘      ╲────────┘
```

## Acceptance / verification

- Unit tests for the parser: `A>["label"]`, `A<["label"]`, and a malformed block-arrow declaration
  falling back to the raw fence.
- A rendered fixture for each direction supported, hand-verified against maintainer-supplied
  reference output obtained before implementation starts (no upstream oracle, per VIEWMD-0040's
  posture) -- this issue's own reference examples must be confirmed at Definition-of-Ready time,
  not invented during implementation.
- `./run-tests.sh` green.

## Peer review
