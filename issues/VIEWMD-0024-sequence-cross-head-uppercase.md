---
id: VIEWMD-0024
title: Use uppercase X for the ASCII sequence-diagram cross (failed-message) arrowhead
status: proposed
area: [render, mermaid]
effort: low
created: 2026-08-05
updated: 2026-08-05
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0014]
supersedes: []
changelog:
reason:
---

# Use uppercase X for the ASCII sequence-diagram cross (failed-message) arrowhead

## Summary

`viewmd/mermaid/sequence/charset.py`'s `ASCII` charset renders the cross/failed-message arrowhead (`-x` / `--x`) as a lowercase `x`. It reads too small next to the other ASCII arrowheads (`>`, `<`, `)`, `(`) at typical terminal font sizes; use uppercase `X` instead.

## Motivation / problem

The `UNICODE` charset already uses `×` (U+00D7 MULTIPLICATION SIGN) for this glyph, which reads clearly at normal size. The `ASCII` fallback's lowercase `x` is comparatively hard to spot against the arrowhead glyphs it appears alongside (reported directly by the maintainer while reviewing VIEWMD-0015's flowchart doc work).

## Requirements

1. MUST change `ASCII.cross_head` in `viewmd/mermaid/sequence/charset.py` from `"x"` to `"X"`.
2. MUST NOT change `UNICODE.cross_head` or any other glyph in either charset.

## Non-goals

- Any other ASCII/Unicode glyph legibility concerns not specifically about the cross head.

## Design notes / links

`viewmd/mermaid/sequence/charset.py:37` is the single line to change. See [VIEWMD-0021](archive/VIEWMD-0021-dotted-line-glyph-font-support.md) for a prior, similar single-glyph legibility fix (the dotted-line character) and its test-fixture-update pattern (`tests/fixtures/mermaid_sequence/*.ascii.out` fixtures containing `x` in a cross-head position need regenerating).

## Acceptance / verification

- `./run-tests.sh` green after regenerating the affected `.ascii.out` fixtures (any fixture using `-x`/`--x`, e.g. `all_arrow_types`).
- Visual check: render a `-x` message through `viewmd --ascii` (or equivalent) and confirm `X` appears at the arrowhead.

## Peer review

Left blank until implemented and tested; filled in as part of the Definition of Done landing gate.
