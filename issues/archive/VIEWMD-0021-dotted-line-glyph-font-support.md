---
id: VIEWMD-0021
title: Mermaid sequence diagram dotted arrows use a box-drawing glyph most terminal fonts do not render
status: implemented
area: [render, mermaid]
effort: low
created: 2026-08-04
updated: 2026-08-05
accepted_by: George Moses
accepted_at: 2026-08-05
commits: [725eeb6]
related: [VIEWMD-0014]
supersedes: []
changelog: "[1.4.2]"
reason:
---

# Mermaid sequence diagram dotted arrows use a box-drawing glyph most terminal fonts do not render

## Summary

`viewmd/mermaid/sequence/charset.py`'s `UNICODE` charset renders dotted message lines (`-->>`, `-->`, `--x`, `--)`, `<<-->>`, and the `alt`/`else` divider) with `┈` (U+2508, BOX DRAWINGS LIGHT QUADRUPLE DASH HORIZONTAL). That codepoint sits outside the basic box-drawing block most monospace terminal fonts actually cover, so on many setups it renders as a blank cell or a tofu glyph instead of a visible dashed line, making dotted arrows look identical to empty space rather than distinguishable from solid ones.

## Motivation / problem

Mermaid sequence diagrams distinguish request messages (solid arrows) from reply/async messages (dotted arrows) by line style alone; that distinction is part of the diagram's meaning. `docs/PLAN.md`'s box-drawing approach assumes the chosen glyphs are broadly renderable, but U+2508 is a rarer glyph than the basic `─`/`│`/corner set used everywhere else in the renderer — several common terminal fonts (e.g. macOS Terminal.app's default font) ship without it, silently dropping the dashed segment. The practical effect reported: dotted lines "are not rendered" — the arrowhead and lifeline tees still show, but the line body between them disappears.

## Requirements

1. MUST replace `UNICODE.dotted_line` with a glyph that both (a) reads as visually distinct from `UNICODE.solid_line` and (b) has broad monospace terminal font coverage — e.g. a basic dash/hyphen-minus run, or a widely-supported box-drawing dash variant confirmed to render in common terminal fonts (verify before picking; do not assume coverage).
2. MUST keep column alignment: the replacement glyph must remain single-width so lifelines and arrowheads stay aligned, matching the existing `circle` width-safety comment in `charset.py`.
3. MUST NOT change `ASCII.dotted_line` (`.`) or any other glyph in either charset.
4. SHOULD note the font-coverage reasoning next to the new glyph choice in `charset.py`, the way the existing `circle` field documents its East-Asian-width constraint.

## Non-goals

- Auto-detecting terminal font capabilities at runtime; this issue is about picking a more broadly-safe default glyph, not adding font probing.
- Changes to the ASCII charset or to any other sequence-diagram glyph (arrowheads, corners, `alt` frame borders).

## Design notes / links

`docs/PLAN.md` for the box-drawing rendering approach; [VIEWMD-0014](archive/VIEWMD-0014-mermaid-sequence-diagrams.md) introduced the `UNICODE`/`ASCII` charsets and the current `dotted_line="┈"` value.

## Acceptance / verification

Render a `sequenceDiagram` with a `-->>` message and an `alt`/`else` block through `viewmd` with the `UNICODE` charset selected, and visually confirm the dotted segment is visible in at least one common terminal font known to lack U+2508 coverage (e.g. macOS Terminal.app default). Add/update a renderer test asserting the new glyph value.

## Peer review

- **Claude** (agent), 2026-08-05: `UNICODE.dotted_line` changed from `┈` (U+2508) to `·` (U+00B7 MIDDLE DOT); updated the 14 `.unicode.out` golden fixtures under `tests/fixtures/mermaid_sequence/` that embedded the old glyph. `./run-tests.sh` (pytest, ruff, pip-audit, issues check) all green; visually confirmed dotted arrows and the `alt`/`else` divider render correctly. `ASCII.dotted_line` and all other glyphs left untouched, per requirements 2-3.
- **George Moses** (maintainer), 2026-08-05: approved — "it's much clearer now". Commit and close out.
