---
id: VIEWMD-0101
title: Fix horizontal scroll stopping one column short of a row's true right edge
status: implemented
area: [pager]
effort: low
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: [9b8816f]
related: []
supersedes: []
changelog: "[1.46.3]"
reason:
---

# Fix horizontal scroll stopping one column short of a row's true right edge

## Summary

Scrolling all the way right on a row wider than the terminal never reaches the row's actual last column(s) -- the pager caps `left_col` one column short of where it needs to be, so the rightmost content stays permanently hidden with no `›` marker to indicate it, even though nothing more actually exists past it.

## Motivation / problem

`_crop_row` reserves one on-screen column for a `‹` truncation marker whenever `left_col > 0`, and one for a `›` marker whenever more content exists to the right (`viewmd/interactive_pager.py`). The maximum scroll position (`max_left_col`), computed in four places in `interactive_pager.py` as `max(0, max_content_width - _content_w())`, does not account for the `‹` marker column that is always present once scrolled away from the left edge -- it assumes the full content width (`_content_w()`) is available for real content at the fully-scrolled position, when only `_content_w() - 1` columns actually are. The result: at max scroll, the window ends one column short of `max_content_width`, so the row's true last column is never shown, and (because the shortfall happens to make `right_more` false) no `›` marker appears to hint that anything was cut off -- the reader sees content that looks complete but isn't. Found while testing wide sequence-diagram/table rows, screenshot attached to the reporting conversation shows a sequence diagram's rightmost participant box missing its right border.

## Requirements

1. MUST let horizontal scroll (wheel-right, `l`/right-arrow key) reach a `left_col` such that the row's true last display column is visible on screen when at max scroll.
2. MUST NOT show a `›` truncation marker at max scroll once the row's true last column is on screen (nothing further exists to hint at).
3. MUST apply the fix consistently everywhere `max_left_col`/the horizontal-scroll cap is derived (wheel-right, width toggle re-clamp (`w`), `B` back-navigation re-clamp, terminal-resize re-clamp).
4. SHOULD factor the corrected cap computation into one shared helper rather than four independent inline copies, so the four call sites can't drift out of sync again.

## Non-goals

Vertical scrolling, wrapping behavior, or the `‹`/`›` marker styling itself -- only the max-scroll boundary computation is in scope.

## Design notes / links

`_crop_row`'s own docstring (`viewmd/interactive_pager.py`) already explains the marker-reservation logic this issue's fix has to stay consistent with. `_content_col` (the click hit-testing inverse of `_crop_row`) encodes the same left/right-marker reservation and should be checked against the fix for consistency, though it is not itself reported broken here.

## Acceptance / verification

A new pager test scrolls a synthetic row wider than the terminal all the way right (repeated wheel-right/`l` past the point `left_col` stops advancing) and asserts the displayed row's last real character is visible with no `›` marker. `./run-tests.sh`.

## Peer review

- **Claude Sonnet 5** (agent), 2026-08-19: verdict CONFIRMED and fixed -- `max_left_col` in all four call sites (wheel-right, `w` width-toggle re-clamp, `B` back-navigation re-clamp, resize re-clamp) undercounted by 1, never reaching a row's true last column once scrolled all the way right, with no `›` marker to hint at the shortfall. Factored the corrected cap into a shared `_max_left_col` helper (requirement 4) and added regression tests (`test_max_left_col_reaches_the_rows_true_last_column`, `test_max_left_col_stays_reachable_by_repeated_stepping`, `test_max_left_col_no_scroll_needed_when_content_fits`). `./run-tests.sh` green.
- **George Moses** (maintainer), 2026-08-19: tested, accept and close.
