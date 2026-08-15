---
id: VIEWMD-0053
title: Render Mermaid block-beta alternate shapes and style/classDef coloring
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

# Render Mermaid block-beta alternate shapes and style/classDef coloring

## Summary

Extend the `block-beta` renderer added by [VIEWMD-0040](VIEWMD-0040-mermaid-block-beta-diagrams.md)
to accept the same shape delimiters flowchart already supports (round, stadium, circle,
subroutine, cylinder, diamond, parallelogram) instead of only the quoted-label rectangle, and to
apply `style`/`classDef`/`class` text coloring the same way flowchart already does.

## Motivation / problem

VIEWMD-0040 deliberately scoped its first version to the rectangle shape only (its Non-goals: "Any
block shape other than the quoted-label rectangle... mirroring flowchart's shape vocabulary...
are follow-up work"). `viewmd/mermaid/flowchart/parser.py`'s `NodeShape` enum and
`viewmd/mermaid/grid/canvas.py`'s `_box_glyphs` already implement round/stadium/circle/subroutine/
cylinder/diamond/parallelogram box drawing, and `flowchart/parser.py:_CLASSDEF_RE` already parses
`classDef`, with `graph.py:245` applying its `color` style key as node label text color. Block
diagrams use identical delimiter syntax for the same shapes, so this is parser reuse plus wiring,
not new box-drawing or color primitives.

## Requirements

1. MUST parse the same shape delimiter pairs flowchart's `NodeShape` recognizes -- `(...)` round,
   `([...])` stadium, `((...))` circle, `[[...]]` subroutine, `[(...)]` cylinder, `{...}` diamond,
   `[/.../]` and `[\...\]` parallelogram -- on a block declaration, reusing
   `viewmd/mermaid/flowchart/parser.py`'s delimiter table rather than re-deriving it.
2. MUST render each shape with the same glyphs `_box_glyphs` already produces for that shape in
   flowchart (`viewmd/mermaid/grid/canvas.py:461-490`), in both Unicode and `--ascii` modes.
3. MUST size a non-rectangle block using the same minimum-width/per-column-equalization rules as
   VIEWMD-0040 requirements 8-9, computed against the shape's own content width (e.g. a diamond's
   narrower usable interior), not the rectangle case's numbers verbatim.
4. MUST parse `style <id> ...` and `classDef <name> ...` / `class <id> <name>` directives
   referencing declared block ids, reusing `flowchart/parser.py:_CLASSDEF_RE` and the associated
   style-class parsing rather than reimplementing it.
5. MUST apply only the `color` style key as the block's label text color, matching flowchart's
   existing behavior (`graph.py:245`) -- `fill`/`stroke` keys are parsed (so unknown-key parsing
   doesn't fail) but not rendered, since terminal box borders don't support fills.
6. MUST leave a `block-beta` fence whose shape/style content fails to parse untouched (fall back to
   the raw fence), matching VIEWMD-0040 requirement 11.
7. MUST NOT change rendering for a plain rectangle block (`id["label"]`) or any other existing
   Mermaid diagram type.

## Non-goals

- Shapes flowchart itself does not yet implement (hexagon, double circle, trapezoid, asymmetric/
  flag) -- those need a flowchart-side issue first; block-beta can pick them up as a fast-follow
  once they exist there.
- The block-arrow shape (`A>["label"]`) -- covered by [VIEWMD-0056](VIEWMD-0056-mermaid-block-arrow-shape.md).
- Composite/nested blocks -- covered by [VIEWMD-0057](VIEWMD-0057-mermaid-block-composite-nested-blocks.md).
- Rendering `fill`/`stroke` as anything beyond parsed-but-ignored -- terminal rendering has no box
  fill concept, matching flowchart's existing posture.

## Design notes / links

Mockup (round + stadium + circle, reusing existing flowchart glyphs verbatim):

```
--- source ---
block-beta
    A("Round")
    B(["Stadium"])
    C(("Circle"))
--- rendered (illustrative) ---

  ╭──────────╮    (  Stadium   )   ╔──────────╗
  │   Round  │                     ║  Circle  ║
  ╰──────────╯                     ╚──────────╝
```

Mockup (styling):

```
--- source ---
block-beta
    A["Alert"]
    style A color:red
--- rendered (illustrative, "Alert" rendered in red) ---

  ┌──────────┐
  │  Alert   │
  └──────────┘
```

## Acceptance / verification

- Unit tests for the parser: each new shape delimiter pair, a `style`/`classDef`/`class` directive
  referencing a declared id, and an unknown style key being parsed without error and ignored.
- A rendered fixture per new shape, hand-verified (no upstream oracle, per VIEWMD-0040's posture).
- A rendered fixture for `color`-styled block text.
- A malformed shape delimiter or style directive falls back to the raw fence rather than crashing.
- `./run-tests.sh` green.

## Peer review
