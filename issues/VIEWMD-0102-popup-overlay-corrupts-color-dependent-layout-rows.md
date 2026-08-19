---
id: VIEWMD-0102
title: Fix ToC/help popup corrupting rows whose no-color layout differs from its colored one
status: in-progress
area: [pager, render]
effort: medium
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Fix ToC/help popup corrupting rows whose no-color layout differs from its colored one

## Summary

Opening the table-of-contents or help popup over a pie-chart row (the one diagram type whose `color=False` rendering is a structurally different layout, not just a de-colored version of the same one, per VIEWMD-0043) replaces that row's on-screen content with fragments of the unrelated bar-chart rendering, visibly corrupting the diagram far beyond the popup box itself, not just the rows it actually covers.

## Motivation / problem

`_overlay` (`viewmd/interactive_pager.py`) rebuilds any row the popup touches from `plain_rows[r]` -- the `color=False` twin of the same source line -- rather than slicing the colored row directly, because slicing through live ANSI color/OSC8 state mid-span is unsafe (see `_overlay`'s own docstring). This assumes `plain_rows[r]` and `body_rows[r]` are the *same* visual content, one colored and one not. That assumption holds for every diagram type except pie charts: `viewmd/mermaid/pie/renderer.py` deliberately renders a circular pie when `color=True` and an entirely different horizontal bar chart when `color=False` (`render()`'s own branch, VIEWMD-0043's design). So on a pie-chart row, `plain_rows[r]` is bar-chart text at bar-chart column positions, not a colorless copy of the circle -- splicing it into `_overlay`'s left/right margins around the popup box overwrites those margins with unrelated, misaligned text (bar labels, percentages, a legend swatch), which reads as the pie's background "changing" or getting corrupted, as shown in the reporting conversation's screenshots (popup open vs. closed over the same pie chart).

## Requirements

1. MUST NOT let opening the ToC or help popup change the on-screen appearance of any row outside the popup's own box, regardless of diagram type.
2. MUST keep `_overlay`'s existing behavior (rebuilding from the plain twin) for every diagram type whose `color=False` output is a de-colored version of the same layout -- this is not a general rewrite of `_overlay`'s approach, only a fix for the pie-chart mismatch.
3. MUST cover the case where the popup box only partially overlaps a pie-chart row (left and/or right margins outside the box) as well as rows entirely covered by the box.

## Non-goals

Changing the pie chart's dual-rendering design itself (VIEWMD-0043) -- that behavior (bar chart when uncolored) is intentional and out of scope here; this issue is only about the pager's popup overlay incorrectly assuming every diagram's plain twin shares its colored twin's layout.

## Design notes / links

VIEWMD-0043 (pie charts render two ways, chosen by color) is the origin of the layout mismatch this issue has to work around. `_overlay`'s docstring in `viewmd/interactive_pager.py` explains why it uses the plain twin in the first place (unsafe to slice colored ANSI state mid-span) -- any fix needs to preserve that safety property while no longer assuming the plain twin is laid out identically.

## Acceptance / verification

A new pager test opens a file containing a pie chart, opens the help popup (or ToC, if the file has headings) so its box overlaps a pie-chart row, and asserts the rendered rows outside the popup box still match the un-popped colored pie output for that row -- not bar-chart text. `./run-tests.sh`.

## Peer review

Left blank until the change is implemented and tested.
