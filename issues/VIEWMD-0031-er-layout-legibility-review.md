---
id: VIEWMD-0031
title: Review Mermaid ER diagram entity placement and connector routing for unnecessary visual clutter on small diagrams
status: proposed
area: [render, mermaid]
effort: medium
created: 2026-08-05
updated: 2026-08-05
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0016]
supersedes: []
changelog:
reason:
---

# Review Mermaid ER diagram entity placement and connector routing for unnecessary visual clutter on small diagrams

## Summary

The maintainer compared viewmd's rendering of several small ER diagrams against the same diagrams rendered by mermaid.live and found viewmd's noticeably busier -- more turns, more crossing lines, entities placed less usefully -- for diagrams that aren't conceptually complex. This issue is an open-ended investigation into `viewmd/mermaid/er/layout.py`'s entity placement (`place_entities`'s row/column grid assignment) and connector routing (the gutter/lane/trunk mechanism), both ported byte-for-byte from `pkg/er/layout.go` in VIEWMD-0016, for places where a small/typical diagram ends up more visually cluttered than the underlying relationships require, and fixing what's found.

## Motivation / problem

Three examples prompted this, each comparing viewmd's rendering against mermaid.live's SVG rendering of the same source:

1. **Self-loop routing**: `A ||--|| A : self` routes both of its stubs out of `A`'s bottom face and all the way around through a side gutter to reconnect, producing two long curved-looking paths that dominate the rendering even though the relationship is conceptually the simplest kind (an entity related to itself). mermaid.live draws the equivalent as a single small loop hugging the box.
2. **Fan-out routing**: a single entity `A` related to three others (`B`, `C`, `D`) via three separate relationships (`tests/fixtures/mermaid_er/word_and_numeric_cardinality.mmd`) lays `A`'s three stubs out through the shared gutter below it with a visible crossing (the `numeric` relationship's run to `D` crosses under the `crow's foot` relationship's run to `B`), even though the three target entities could sit directly below their respective relationship with no crossing at all. mermaid.live draws this as three uncrossed lines fanning out from `A`.
3. **Entity placement**: `ORDER ||--|{ PRODUCT : contains` (`tests/fixtures/mermaid_er/attribute_keys_and_types.mmd`) places `ORDER` (no attributes) to the *right* of `PRODUCT` (three attributes) in a side-by-side grid cell, purely because `place_entities` packs entities into a near-square `ceil(sqrt(n))`-column grid by insertion order, with no awareness of which entities relate to which. mermaid.live's layout instead stacks `ORDER` directly *above* `PRODUCT`, reflecting the relationship's natural top-to-bottom reading order and needing no horizontal connector run at all.

ASCII box-drawing art can't replicate curved SVG paths or a dagre-style constraint layout, so exact visual parity isn't the bar -- but all three examples point at the same underlying question: are `place_entities`' grid assignment and the connector-routing algorithm's choices (which face(s) a relationship exits through, how self-loops are laid out, how gutter/lane space is allocated and shared) the *simplest* correct layout for common small-diagram shapes, or just *a* correct one? This is scoped broadly across both placement and routing rather than to any one example, since a grid-assignment fix and a routing fix can interact (e.g. placing `ORDER` above `PRODUCT` changes which face their relationship exits through) and a narrow single-example fix might miss related clutter elsewhere (e.g. the multi-entity grid layout in `tests/fixtures/mermaid_er/large_grid_layout.mmd`).

## Requirements

1. MUST review `place_entities` (grid row/column assignment) and `draw_connectors`/`sides_for`/`attach`/`RoutePlan` (connector routing) in `viewmd/mermaid/er/layout.py` (and their `pkg/er/layout.go` counterparts) against a handful of small, representative diagrams -- at minimum: a single self-loop, a one-entity/three-relationship fan-out (as in `tests/fixtures/mermaid_er/word_and_numeric_cardinality.mmd`), a two-entity single-relationship diagram where one entity has attributes and the other doesn't (as in `tests/fixtures/mermaid_er/attribute_keys_and_types.mmd`), three entities in a chain, and the existing `tests/fixtures/mermaid_er/large_grid_layout.mmd` case -- and document concretely which placement or routing choices produce more turns/crossings/gutter space, or less natural entity ordering, than the relationships require.
2. MUST propose and implement at least one concrete improvement from that review (placement, routing, or both), with before/after renderings in the issue or its PR description showing the reduction in visual complexity.
3. MUST NOT regress `tests/fixtures/mermaid_er/`'s existing differential-tested cases without updating them to hand-verified fixtures for whatever specifically changed, and MUST keep any diagram shape not touched by the fix byte-for-byte identical to its current (upstream-matching) output.
4. MUST keep the change self-contained within `viewmd/mermaid/er/layout.py` (or its immediate call sites in `renderer.py`) -- no changes to the parser or to the sequence/flowchart renderers.
5. SHOULD prefer a general improvement (e.g. ordering the grid by relationship adjacency rather than insertion order, a smarter self-loop path, or tighter gutter sizing) over a special case that only fixes one exact example diagram, so the fix generalizes to other small diagrams with the same shape of relationship.

## Non-goals

- Matching mermaid.live's SVG rendering exactly, or drawing actual curved lines -- ASCII box-drawing art is inherently different from a curved SVG renderer; the bar is "as simple as the relationships allow within box-drawing art," not visual parity with mermaid.live.
- VIEWMD-0030's dashed-line glyph legibility fix -- unrelated axis of "legibility" (glyph choice vs. layout shape); land independently.
- A full rewrite or redesign of the grid/gutter/lane routing model, or replacing the grid-based placement with a general constraint/force-directed layout engine -- this is a legibility review and targeted improvement within the existing model, not a new layout engine.

## Design notes / links

[VIEWMD-0016](archive/VIEWMD-0016-mermaid-er-diagrams.md) ported the layout engine byte-for-byte; `viewmd/mermaid/er/layout.py`'s module docstring notes it's self-contained rather than reusing `viewmd/mermaid/grid`. Entity placement is `place_entities`' `cols = ceil(sqrt(n))` grid assignment (row/col from insertion-order index, no relationship awareness). Self-loop routing specifically lives in `draw_connectors`'s self-loop attach-slot spreading (the `if ea.p is eb.p:` block) and `sides_for`'s "same row (incl. self-relationships)" case. Since there's no reference Go binary output to diff a *changed* layout against (this is a deliberate departure from the byte-for-byte baseline, same posture as VIEWMD-0022/0023/0025/0026/0027/0028), verification is hand-authored/visual rather than differential.

## Acceptance / verification

- Before/after renderings of all three motivating examples (the self-loop case, the `A`/`B`/`C`/`D` fan-out case, and the `ORDER`/`PRODUCT` placement case) showing measurably fewer turns/crossing lines or more natural entity ordering, matching the maintainer's side-by-side comparisons.
- The representative diagrams from requirement 1 rendered and visually reviewed by the maintainer.
- Updated/added hand-verified fixtures for whatever changed; unaffected fixtures stay byte-for-byte identical.
- `./run-tests.sh` green.

## Peer review

Left blank until implemented and tested; filled in as part of the Definition of Done landing gate.
