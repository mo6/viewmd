---
id: VIEWMD-0024
title: Use uppercase X for the ASCII sequence-diagram cross (failed-message) arrowhead
status: in-progress
area: [render, mermaid]
effort: low
created: 2026-08-05
updated: 2026-08-07
accepted_by: maintainer
accepted_at: 2026-08-07
commits: []
related: [VIEWMD-0014]
supersedes: []
changelog:
reason:
---

# Use a Latin capital X for the sequence-diagram cross (failed-message) arrowhead, in both charsets

## Summary

`viewmd/mermaid/sequence/charset.py`'s `ASCII` charset renders the cross/failed-message arrowhead (`-x` / `--x`) as a lowercase `x`, and the `UNICODE` charset renders it as `×` (U+00D7 MULTIPLICATION SIGN). Both read too small/faint next to the other arrowheads (`>`, `<`, `)`, `(`) at typical terminal font sizes; use a Latin capital `X` in both charsets instead.

## Motivation / problem

The `ASCII` fallback's lowercase `x` is hard to spot against the arrowhead glyphs it appears alongside. The `UNICODE` charset's `×` was originally believed to read clearly at normal size, but on review of `docs/mermaid-examples.md`'s rendered output the maintainer found it still reads as visually small/faint in-terminal — a plain Latin `X` is bolder and more consistent with the other glyphs in both charsets (reported directly by the maintainer while reviewing VIEWMD-0015's flowchart doc work, then extended to the Unicode charset after reviewing this issue's own rendered docs output).

## Requirements

1. MUST change `ASCII.cross_head` in `viewmd/mermaid/sequence/charset.py` from `"x"` to `"X"`.
2. MUST change `UNICODE.cross_head` in `viewmd/mermaid/sequence/charset.py` from `"×"` to `"X"`.
3. MUST NOT change any other glyph in either charset.

## Non-goals

- Any other ASCII/Unicode glyph legibility concerns not specifically about the cross head.

## Design notes / links

`viewmd/mermaid/sequence/charset.py:37` and `:47` are the two lines to change. See [VIEWMD-0021](archive/VIEWMD-0021-dotted-line-glyph-font-support.md) for a prior, similar single-glyph legibility fix (the dotted-line character) and its test-fixture-update pattern (`tests/fixtures/mermaid_sequence/*.ascii.out` and `*.unicode.out` fixtures containing `x`/`×` in a cross-head position need regenerating).

## Acceptance / verification

- `./run-tests.sh` green after regenerating the affected `.ascii.out` and `.unicode.out` fixtures (any fixture using `-x`/`--x`, e.g. `all_arrow_types`).
- Visual check: render a `-x` message through both `viewmd` (Unicode) and `viewmd --ascii` (or equivalent) and confirm `X` appears at the arrowhead in both.

## Peer review

- (agent, independent) PASS — verified `ASCII.cross_head` is `"X"` and `UNICODE.cross_head` is now `"X"` (was `"×"`) with no other glyph touched; the four affected fixtures (`all_arrow_types.ascii.out`/`.unicode.out`, `kitchen_sink.ascii.out`/`.unicode.out`) each change only cross-head positions, and a repo-wide grep found zero remaining `×` and no stray lowercase cross-head `x` in `tests/fixtures/mermaid_sequence/`; `./run-tests.sh`'s 324 tests pass (its overall `FAILED` label is pre-existing unrelated ruff lint noise in `poc/`, confirmed present on `develop` and untouched by this diff); `docs/mermaid-examples.md`/`docs/example.md` render live with no stale baked-in output; no stray unrelated changes in the diff.
