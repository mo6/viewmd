---
id: VIEWMD-0030
title: Mermaid ER diagram non-identifying relationships use box-drawing glyphs most terminal fonts do not render
status: in-progress
area: [render, mermaid]
effort: low
created: 2026-08-05
updated: 2026-08-11
accepted_by: George Moses
accepted_at: 2026-08-11
commits: []
related: [VIEWMD-0016, VIEWMD-0021]
supersedes: []
changelog:
reason:
---

# Mermaid ER diagram non-identifying relationships use box-drawing glyphs most terminal fonts do not render

## Summary

`viewmd/mermaid/er/charset.py`'s `UNICODE` charset renders a non-identifying relationship's dashed connector line with `┈` (U+2508, BOX DRAWINGS LIGHT QUADRUPLE DASH HORIZONTAL) for horizontal runs and `┊` (U+250A, BOX DRAWINGS LIGHT QUADRUPLE DASH VERTICAL, U+2508's vertical sibling) for vertical runs. Both codepoints sit outside the basic box-drawing block most monospace terminal fonts actually cover, so on many setups a dashed relationship line renders as a blank/tofu gap instead of a visible dashed line -- making non-identifying relationships look identical to empty space rather than visually distinguishable from identifying (solid) ones.

## Motivation / problem

This is the same underlying font-coverage problem VIEWMD-0021 fixed for sequence-diagram dotted arrows (`┈` in `viewmd/mermaid/sequence/charset.py`), reported by the maintainer after visually spot-checking a rendered ER diagram: a dashed relationship (`A }o..o{ B`) was effectively invisible in a common terminal font, while the corresponding real-Mermaid-inspired expectation (a clearly dashed line) was legible. ER diagrams have the added wrinkle that VIEWMD-0021 didn't: relationship lines run both horizontally (`hd`) and vertically (`vd`) through the gutter/trunk routing, so both glyphs need a broadly-renderable replacement, not just one.

## Requirements

1. MUST replace `UNICODE.hd` with a glyph that (a) reads as visually distinct from `UNICODE.h`, (b) has broad monospace terminal font coverage (verify before picking; do not assume coverage -- same standard VIEWMD-0021 required), and (c) is single-width, matching the existing box-drawing glyphs' column-alignment assumption.
2. MUST replace `UNICODE.vd` with a glyph meeting the same three criteria as requirement 1, chosen so the horizontal and vertical dashed glyphs read as a consistent visual style (e.g. both some form of "dot," as VIEWMD-0021 chose `·` for the horizontal case).
3. MUST NOT change `ASCII.hd` (`.`) or `ASCII.vd` (`:`), or any other glyph in either charset.
4. MUST update every golden fixture under `tests/fixtures/mermaid_er/` that embeds the old glyphs to the new ones.

## Non-goals

- Auto-detecting terminal font capabilities at runtime.
- Changes to the ASCII charset or to any other ER-diagram glyph (box corners, tees, crow's-foot tokens).
- VIEWMD-0031's broader ER layout-legibility review -- this issue is scoped to the two dashed-line glyphs only.

## Design notes / links

`viewmd/mermaid/er/charset.py` defines `hd`/`vd` on the `Glyphs` dataclass; `viewmd/mermaid/er/layout.py`'s `_glyph_for` selects between `g.h`/`g.hd` and `g.v`/`g.vd` based on the `solid` flag threaded through `Overlay.polyline`. [VIEWMD-0021](archive/VIEWMD-0021-dotted-line-glyph-font-support.md) is the precedent for both the problem and the fix approach (there, `┈` became `·` for `viewmd/mermaid/sequence/charset.py`'s single horizontal `DottedLine`).

## Acceptance / verification

Render an `erDiagram` with a non-identifying relationship (e.g. `A }o..o{ B`) and a self-loop or multi-entity layout exercising a vertical dashed trunk, through `viewmd` with the `UNICODE` charset selected; visually confirm both the horizontal and vertical dashed segments are visible in at least one common terminal font known to lack coverage for the current glyphs (e.g. macOS Terminal.app default). Updated fixtures and a renderer test asserting the new glyph values. `./run-tests.sh` green.

## Peer review

- **Claude** (agent), 2026-08-11: Verified `UNICODE.hd`/`UNICODE.vd` changed from `┈`/`┊` to `·`/`:` per spec — both single-width, visually distinct from solid `─`/`│`. Confirmed `ASCII.hd`/`ASCII.vd` and all other glyphs untouched, and via `grep -rlP '[\x{2508}\x{250a}]' tests/fixtures/mermaid_er/` that no fixture still embeds the old glyphs — all four affected `.unicode.out` fixtures were updated, covering both horizontal and vertical dashed runs (including a self-loop trunk). The new `test_dashed_relationship_glyphs_are_broadly_renderable` unit test pins the exact codepoints, complementing (not duplicating) the existing fixture-diff test which already exercises both glyphs end-to-end. Ran `./run-tests.sh`: 536 tests passed, ruff clean, pip-audit clean, issues check green. Pass.
- **George Moses** (maintainer), 2026-08-11: approved. Commit and close out.
