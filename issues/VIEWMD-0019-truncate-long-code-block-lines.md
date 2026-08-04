---
id: VIEWMD-0019
title: Long lines in code blocks should stay intact, not wrapped or cut off
status: in-progress
area: [render]
effort: medium
created: 2026-08-04
updated: 2026-08-04
accepted_by: George Moses
accepted_at: 2026-08-04
commits: []
related: [VIEWMD-0018]
supersedes: []
changelog:
reason:
---

# Long lines in code blocks should stay intact, not wrapped or cut off

## Summary

A line inside a fenced ` ``` ` code block that is longer than the render width is currently wrapped onto additional lines. It should instead stay on one line at its own natural width, the same way mermaid diagram art does ([[VIEWMD-0018]]), rather than reflowing into the surrounding layout or losing content. **Revised 2026-08-04**: an earlier version of this issue asked for the line to be hard-cropped (truncated) instead of wrapped; real-world testing showed that silently discards content even when the terminal is wide enough to show it, which is worse than the original wrapping bug for anyone who actually needs to read the full line. The fix now matches VIEWMD-0018 exactly: never lose content, rely on the pager (`less -S`) for horizontal scrolling.

## Motivation / problem

The document is rendered by a single Rich `Console` at a fixed width (`viewmd/render.py:48,54`). Rich's default Markdown `CodeBlock` word-wraps and right-pads code content to the console width, and Rich 15.0.0 hardcodes this in the default code-block element, so there's no config flag to flip. Example: a code block containing one 120-character line, rendered at width 100, currently produces two output lines (100 chars + 20 chars, both padded to 100) instead of one truncated line.

## Requirements

1. MUST render fenced code-block lines with `no_wrap=True` (or equivalent) so a line longer than the render width stays on one line instead of folding onto additional lines.
2. MUST implement this via a custom Markdown `CodeBlock` element override wired into the `Markdown(...)` call in `viewmd/render.py:54`, since Rich has no built-in flag for this.
3. MUST NOT lose any content: a line longer than the render width (or the default `min(100, terminal_width)` cap) MUST still render in full at its own natural width, exactly like mermaid-rendered diagram output does per [[VIEWMD-0018]], relying on the pager's horizontal scroll (`less -S`) rather than cropping.
4. MUST distinguish mermaid-rendered output from ordinary fenced code (sentinel info-string or separate render path) so both get their own natural-width treatment without one path affecting the other, coordinated with [[VIEWMD-0018]]. (In practice both end up needing the same "don't crop" treatment, but they still route through different renderers -- `Syntax`, with highlighting, for code; raw segments for pre-rendered diagram art.)
5. A block whose lines all already fit within the render width MUST still fill/pad to that width, matching the existing visual style (no shrinking short blocks down to their content width).

## Non-goals

Changing how mermaid diagram art is rendered or wrapped is out of scope here — that's [[VIEWMD-0018]]; this issue only concerns ordinary fenced code blocks.

## Design notes / links

Depends on / coordinates with [[VIEWMD-0018]] (the Mermaid width issue): mermaid art is rendered *as* a code block (`viewmd/mermaid/preprocess.py`), tagged with a `MERMAID_RENDERED_INFO` sentinel info-string. `ViewmdCodeBlock` in `viewmd/render.py` keys off that sentinel: mermaid-tagged fences emit raw `Segment`s at their natural width (VIEWMD-0018's mechanism); ordinary fences re-render their `Syntax` object against a widened `ConsoleOptions` (`options.update(width=...)`, at least the console's own width so a block that already fits still fills the row) instead of the console's declared width, so a long line is never cropped -- Rich's `Syntax` otherwise bounds each line's length to whatever width it's rendered against, which is why the earlier hard-crop version still needed `word_wrap=False` plus this width override, not `crop=False` alone (that only stops the *final* buffer-level crop, same as it does for mermaid).

Source: https://github.com/mo6/viewmd/issues/3

## Acceptance / verification

- Reproduction case: a code block containing a single 120-character line, rendered at width 100, produces exactly one output line, the full 120 characters present in the output (not folded, not cropped).
- A regression test confirming a short code block (all lines fit within the render width) still fills/pads to the full render width, unchanged from before this issue.
- A regression test confirming mermaid diagram output and ordinary code still route through distinct renderers (highlighted+padded vs. raw segments) even though neither loses content (covered jointly with [[VIEWMD-0018]]).
- `./run-tests.sh` green.

## Peer review

- **Cursor Grok** (agent), 2026-08-04: accept. Implemented jointly with VIEWMD-0018 via the shared `mermaid-rendered` sentinel. Ordinary fences go through `ViewmdCodeBlock` → `Syntax(..., word_wrap=False, padding=0)`, which hard-crops at the console width; mermaid-tagged fences take the Segment path and are unaffected. Open question (req. 4): hard crop rather than an ellipsis marker — silent cut matches Rich's native no-wrap crop and is consistent with the pager's new `-S` chop; an ellipsis would invent content that was never in the source. Reproduction: 120-char line at width 100 → exactly one 100-column output line. Cross-issue discrimination test confirms ordinary code still truncates when mermaid bypasses. `./run-tests.sh` green (192 passed).
- **Claude** (agent), 2026-08-04: independent re-verification, jointly with VIEWMD-0018 (same branch). Found `padding=0` was an unrequested regression -- silently dropped the blank-line/left-margin style every code block had via Rich's prior `padding=1`, not something req. 1 actually required (verified `word_wrap=False` still hard-crops correctly with `padding=1` restored). Fixed, and updated the test that had over-specified the no-padding output. Truncation behavior itself (single line, hard-cropped, never lets the full long line through) is unchanged and still verified. `./run-tests.sh` green (192 passed) after the fix.
- **George Moses** (maintainer), 2026-08-04: accept (superseded by the revision below, found during this same round of manual testing) -- flagged that the hard-crop behavior silently drops real content even on a terminal wider than the render width, unlike VIEWMD-0018's diagrams which stay fully visible via horizontal scroll. Asked for code to behave the same way: always full natural width, never cropped.
- **Claude** (agent), 2026-08-04 (revision): accept. Reworked `ViewmdCodeBlock` to re-render ordinary `Syntax` fences against a widened `ConsoleOptions` (`options.update(width=max(natural_line_width, console_width))`) instead of letting `Syntax` bound each line to the console's declared width -- so a long line now survives at full width exactly like mermaid's raw-`Segment` path already did, and `crop=False` (already in place for VIEWMD-0018) is what lets it reach the buffer intact. Verified: the 120-char reproduction line is now present in full in the output; a short block (all lines fitting) still pads to the full render width, unchanged (req. 5); mermaid and code still take visibly different paths (code gets `Syntax`'s padding=1 blank-line margin, mermaid doesn't) even though neither loses content anymore. Updated the two tests that had asserted the old hard-crop behavior (`test_long_code_block_line_is_truncated_not_wrapped` → `test_long_code_block_line_is_not_truncated_or_wrapped`; the cross-issue discrimination test now checks render-path distinction instead of width). Updated `docs/example.md`'s prose to match. `./run-tests.sh` green (192 passed).

