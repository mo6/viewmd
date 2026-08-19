---
id: VIEWMD-0102
title: Fix ToC/help popup corrupting content and color in the rows around it
status: implemented
area: [pager, render]
effort: medium
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: [6167522, 914deac]
related: []
supersedes: []
changelog: "[1.46.4]"
reason:
---

# Fix ToC/help popup corrupting content and color in the rows around it

## Summary

Opening the table-of-contents or help popup over a pie-chart row (the one diagram type whose `color=False` rendering is a structurally different layout, not just a de-colored version of the same one, per VIEWMD-0043) used to replace that row's on-screen content with fragments of the unrelated bar-chart rendering, visibly corrupting the diagram far beyond the popup box itself; a first fix pass corrected the content but left the popup-adjacent margins colorless, which is just as visible on a color-filled diagram like a pie chart. `_overlay` now slices the margins straight out of the real colored row instead of any separately-built plain twin, fixing both.

## Motivation / problem

`_overlay` (`viewmd/interactive_pager.py`) used to rebuild any row the popup touches from `plain_rows[r]` -- the `color=False` twin of the same source line -- rather than slicing the colored row directly, reasoning that slicing through live ANSI color/OSC8 state mid-span is unsafe. That's true of a naive character-index slice, but not of `_ansi_slice` (already used elsewhere in this module, e.g. `_crop_row`'s horizontal-scroll cropping), which exists precisely to cut a colored line at an arbitrary column without leaking or losing SGR/OSC8 state. Using a separate plain twin instead had two costs, found in two passes:

1. **Content**: `plain_rows[r]` and `body_rows[r]` were assumed to be the *same* visual content, one colored and one not. That holds for most diagram types, but not pie charts: `viewmd/mermaid/pie/renderer.py` deliberately renders a circular pie when `color=True` and an entirely different horizontal bar chart when `color=False` (`render()`'s own branch, VIEWMD-0043's design) -- even differing in total row count (`docs/example.md`: 499 colored rows vs. 484 plain rows). So on a pie-chart row, `plain_rows[r]` was bar-chart text at bar-chart column positions, not a colorless copy of the circle -- splicing it into the margins around the popup box overwrote them with unrelated, misaligned text, and every row below the pie was thrown off by the row-count delta too.
2. **Color**: even a plain twin that shared the colored row's exact layout (e.g. `_strip_ansi` of the colored row itself, the first fix pass here) is still colorless by construction, so every popup-adjacent row visibly lost all its color -- barely noticeable on ordinary prose, but glaring on a pie chart, where color fill *is* the content, not a highlight on top of it (reported after the first pass: the pie stayed structurally correct but rendered monochrome around the popup).

## Requirements

1. MUST NOT let opening the ToC or help popup change the on-screen *content* of any row outside the popup's own box, regardless of diagram type.
2. MUST NOT let opening the ToC or help popup change the on-screen *color* of any row outside the popup's own box either -- a popup-adjacent margin must keep whatever color/link state the real row carries there.
3. MUST cover the case where the popup box only partially overlaps a row (left and/or right margins outside the box) as well as rows entirely covered by the box.

## Non-goals

Changing the pie chart's dual-rendering design itself (VIEWMD-0043) -- that behavior (bar chart when uncolored) is intentional and out of scope here; this issue is only about the pager's popup overlay incorrectly rebuilding margins from something other than the row actually on screen.

## Design notes / links

VIEWMD-0043 (pie charts render two ways, chosen by color) is the origin of the content-layout mismatch this issue first worked around. `_ansi_slice`'s own docstring (`viewmd/interactive_pager.py`) explains how it safely cuts a colored line at an arbitrary column, reopening/closing whatever SGR/OSC8 span the cut lands inside -- the mechanism `_overlay` now reuses directly on `body_rows[r]` instead of needing any plain twin at all.

## Acceptance / verification

Pager tests at the `_overlay` level assert both properties directly: margin content around the popup box matches the real colored row (using a pie-chart document, where a mismatched plain twin would show unrelated bar-chart text), and margin color around the box is preserved (a colored synthetic row's SGR code survives into the margin). `./run-tests.sh`.

## Peer review

- **Claude Sonnet 5** (agent), 2026-08-19: verdict CONFIRMED and fixed (pass 1, content only) -- `draw()`'s `plain_visible` (the `plain_rows` argument to `_overlay`) was built from `plain_lines`, a wholly independent `color=False` render, which for a document containing a pie chart both diverges in per-row content *and* in total row count from the colored render (confirmed against `docs/example.md`: 499 colored rows vs. 484 plain rows) -- so once a pie chart appears, every row's plain twin below it is off by the row-count delta, not just the pie's own rows. Fixed by deriving `plain_visible` from `_strip_ansi(row) for row in visible` -- the already-displayed colored rows with their own color stripped -- which is guaranteed to share the colored rows' exact layout for every diagram type, with no second render pass. `_scrollbar_prefix`'s now-unreachable `colored=False` branch removed as dead code. Manually reproduced the reported corruption against `docs/example.md` with a 125-col terminal and a near-full-height help popup before the fix (35/35 rows in the popup's side margins showed unrelated bar-chart/prose text) and confirmed the fix resolves it. `./run-tests.sh` green.
- **George Moses** (maintainer), 2026-08-19: tested pass 1 -- content corruption/bar-chart fallback is gone, pie stays visible and structurally correct, but it still loses all color in the popup-adjacent margins. Sent back for a second pass.
- **Claude Sonnet 5** (agent), 2026-08-19: verdict CONFIRMED and fixed (pass 2, color) -- the pass-1 fix traded content-correctness for color, since `_strip_ansi`'s whole point is to remove color; any plain twin, however well-aligned, was always going to render popup-adjacent margins monochrome. Replaced the plain-twin approach entirely: `_overlay` now slices `body_rows[r]` (the real colored row) directly via `_ansi_slice`, the same token-walking slice `_crop_row`'s horizontal-scroll cropping already uses to cut through live SGR/OSC8 state safely -- the "unsafe to slice a colored row" reasoning in `_overlay`'s old docstring predated `_ansi_slice`'s existence and no longer applies. Dropped the now-unnecessary `plain_rows` parameter from `_overlay` entirely and the `plain_visible` construction in `draw()`. Reran the same manual reproduction against `docs/example.md` (125-col terminal, near-full-height help popup) and confirmed truecolor SGR codes (`\x1b[38;2;...`) now appear in the popup's left margin over the pie chart. Rewrote the `_overlay` test block for the new two-argument signature and added a color-preservation regression test (`test_overlay_margins_keep_their_own_color`) alongside the content one (`test_overlay_margins_come_from_the_real_colored_row`). `./run-tests.sh` green.
- **George Moses** (maintainer), 2026-08-19: tested pass 2, works correctly -- accept and close.
