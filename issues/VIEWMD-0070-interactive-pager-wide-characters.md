---
id: VIEWMD-0070
title: Interactive pager misaligns wide (emoji/CJK) characters
status: in-progress
area: [cli, render]
effort: medium
created: 2026-08-17
updated: 2026-08-17
accepted_by: George Moses
accepted_at: 2026-08-17
commits: []
related: [VIEWMD-0007]
supersedes: []
changelog:
reason:
---

# Interactive pager misaligns wide (emoji/CJK) characters

## Summary

`viewmd/interactive_pager.py` (VIEWMD-0007) treats every character as exactly one terminal column when doing column math -- horizontal scroll/crop (`_ansi_slice`/`_crop_row`), and the ToC/help popup overlay (`_overlay`, which splices new content into the left/right portions of a document row around the box). A genuinely double-width character (an emoji, most CJK characters) breaks that assumption: everything after it on that row renders one column further right in the real terminal than the module's own math accounts for, visibly misaligning the popup box's edges on any row containing one. Found live during VIEWMD-0007's own review: `README.md`'s "🖼 viewmd demo" image-alt-text line threw off the help popup's left border.

## Motivation / problem

This was a known, disclosed limitation at the time VIEWMD-0007 shipped (`_ansi_slice`'s docstring: "Assumes one column per character (no `wcwidth`) ... a CJK/emoji-heavy line would misalign here"), not something that slipped through unnoticed -- but it's a real, visible bug once a document actually contains a wide character near where the popup renders, which is common enough (emoji in prose, image alt text, CJK content) that it's worth fixing properly rather than leaving as a standing caveat. `viewmd/render.py` already depends on `wcwidth` (`wcswidth`, via its own `_display_width` helper) for exactly this reason elsewhere in the codebase -- the interactive pager choosing plain `len()` instead is an inconsistency with the rest of the project's own conventions, not a deliberate simplification that should stay.

## Requirements

1. MUST use `wcwidth.wcswidth`-based display-width calculations (matching `viewmd/render.py`'s own `_display_width` convention) everywhere `viewmd/interactive_pager.py` currently uses `len()` to mean "column count": `_ansi_slice`'s column walk, `_crop_row`'s width/truncation-marker math, `_overlay`'s left-padding and splice-point calculations, `_popup_box`/`_help_box`'s row layout, `_mode_line`'s fill/truncation, `_pad_ansi`, and `_load`'s `max_content_width` tracking.
2. MUST NOT regress any existing behavior for ordinary (single-width) content -- every test in `tests/test_interactive_pager.py` must still pass unchanged in its assertions (though fixture content may need a genuinely wide-character case added).
3. SHOULD add test coverage using a real wide character (an emoji, or a CJK string) exercising horizontal scroll/crop and the popup overlay, matching the concrete case that surfaced this (a document line containing an emoji, with the ToC or help popup open).

## Non-goals

- Combining characters, zero-width joiners, or other Unicode grapheme-cluster edge cases beyond what `wcwidth` itself already handles -- matching `viewmd/render.py`'s own existing scope, not going further.
- Anything about the *rendering* of wide characters themselves (glyph selection, terminal font support) -- this is purely about this module's own column bookkeeping agreeing with what the terminal will actually do.

## Design notes / links

`viewmd/render.py:202`'s `_display_width` is the existing, already-tested convention to match (`wcwidth.wcswidth`, with a documented override for one emoji-presentation edge case worth reading before reusing it verbatim). See VIEWMD-0007's own `_ansi_slice` docstring for the specific disclosed limitation this issue closes.

## Acceptance / verification

- `./run-tests.sh` green, including new wide-character test(s) in `tests/test_interactive_pager.py` for both horizontal crop and popup-overlay alignment.
- Manual terminal verification: `viewmd README.md` (or any document containing an emoji), opening the ToC or help popup, confirms the box's borders line up correctly across every row, including the emoji-containing one.

## Peer review

- **Claude Sonnet 5** (agent, implementer's own pass), 2026-08-17: Replaced every `len()`-as-column-count use in `viewmd/interactive_pager.py` with `wcwidth`-based measurement (`_display_width`/`_char_width`/`_wc_ljust`, matching `viewmd/render.py`'s own `_display_width` convention), covering all six sites requirement 1 lists: `_ansi_slice`'s column walk (rewritten to track true per-character width and pad a boundary-straddling wide character with space(s) instead of emitting half a glyph), `_crop_row` (unchanged internally, now receives correctly-measured `plain_len` from its callers), `_overlay` (its raw character-index splice replaced with `_ansi_slice` calls, since a wide character anywhere in the underlying document row before the splice point was exactly what misaligned the popup in the reported bug), `_popup_box`/`_help_box` (only `_popup_box` needed changes -- `_help_box`'s content is entirely this module's own hardcoded ASCII labels, never arbitrary document text, so it was never actually exposed to the bug despite requirement 1 listing it), `_mode_line`, and `_pad_ansi`. Verified against the real reported case end to end: `README.md`'s own `![viewmd demo](docs/demo.gif)` line, which Rich renders with a genuine width-2 placeholder glyph (`🌆`, confirmed via `wcswidth` directly) -- cropping it now produces exactly the requested display width (previously off by one). Requirement 2 (no regression) verified by the fact that all 52 pre-existing tests in `tests/test_interactive_pager.py` pass with zero assertion changes; requirement 3 (new coverage) met with 9 new tests using that same real character, including one demonstrating the exact bug directly (character-index 46 vs. correct display-column 47 for the popup border, the one-column discrepancy the report described). `./run-tests.sh` green (1017 tests, ruff, pip-audit, issues index). Not independently verified in a real terminal (no tty available to this agent) -- matches the Acceptance section's own manual-verification line, same caveat as VIEWMD-0007's own review.
- **George Moses** (maintainer), 2026-08-17: Tested on `README.md` in a real terminal, checking two separate places where the misalignment previously showed up. Confirmed fixed; signed off to land ("commit and close this out").
