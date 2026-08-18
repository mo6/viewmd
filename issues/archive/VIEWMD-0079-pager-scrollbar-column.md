---
id: VIEWMD-0079
title: Scrollbar column showing visible extent in the interactive pager
status: implemented
area: [pager]
effort: medium
created: 2026-08-18
updated: 2026-08-18
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-18
commits: [32a65dd]
related: []
supersedes: []
changelog: "[1.39.0]"
reason:
---

# Scrollbar column showing visible extent in the interactive pager

## Summary

The interactive pager (`viewmd/interactive_pager.py`) reserves its leftmost screen column for a vertical scrollbar that shows, at a glance, how much of the document is visible and where the current viewport sits within it -- using both a color and a fill pattern (glyph) to mark the "thumb" (visible range) versus "track" (rest of the document), so the indicator still reads correctly with `--no-color`/monochrome terminals or for color-blind readers.

## Motivation / problem

`_mode_line` already reports scroll position as text (`_mode_line`'s `top`/`end`/`len(lines)` line-count summary), but that requires reading and mentally computing a fraction; a vertical bar makes "how much more is there, and where am I" visible without reading anything. `less`/`most` don't offer this either, but many modern pagers and editors (e.g. terminal `bat`, most GUI editors) do, and it's a natural fit for viewmd's own Info-style split-screen layout, which already reserves fixed rows (mode line, echo area) for chrome -- this issue reserves one fixed column the same way.

## Requirements

1. MUST reserve column 0 of every body row (the `body_h` rows `draw()` composes, between the top of the screen and the mode line) for a one-character-wide scrollbar cell, followed by column 1 as a blank one-character-wide gap column that sets the scrollbar apart from the document content, for the single-document pager (`run`), the directory listing pager (`run_directory_listing`), and the multi-file pager (`run_multi_file`) -- i.e. everywhere `_run`'s `draw()` is used.
2. MUST shrink the usable content width by 2 columns (scrollbar cell + gap cell) to make room for the scrollbar, so no rendered content is clipped or overwritten by either reserved column -- `term_w` itself does not change, but the content area `_crop_row`/`_ansi_slice` operate over does.
3. MUST compute the scrollbar's thumb (the sub-range of the `body_h` rows representing the currently visible slice of `lines`) from `top`, `body_h`, and `len(lines)`, proportionally sized and positioned the same way `_mode_line`'s existing percentage/line-range text is derived, and MUST recompute it every `draw()` call so it stays in sync with scrolling (arrow keys, mouse wheel, search jumps, ToC jumps, resize).
4. MUST render the thumb cells and the track cells with both a distinct fill glyph and a distinct color/style from each other (e.g. a solid block glyph for the thumb vs. a lighter/dotted glyph for the track), so the distinction still reads under `--no-color` or a monochrome terminal, not through color alone.
5. MUST leave the scrollbar and gap columns blank (or omit both reserved columns entirely, falling back to today's full-width layout) when the whole document already fits within `body_h` rows -- i.e. no scrollbar when there is nothing to scroll.
6. MUST NOT interfere with mouse-wheel scrolling, existing mouse click targets (link click-to-follow, ToC/help popup row selection -- VIEWMD-0076), or the popup/help overlay compositing (`_overlay`) -- content's column 0 shifts by exactly the scrollbar-plus-gap width (2 columns) for all of these, consistently.
7. SHOULD make clicking within the scrollbar column jump the viewport to roughly that proportional position in the document (click-to-scroll), consistent with the click-driven interactions VIEWMD-0076 already added elsewhere in the pager.
8. MUST NOT change any non-interactive rendering path (`render_markdown`/`render_directory_listing`/`render_multi_file`, `--no-pager` output, piped/non-tty output) -- this is a pager-only (interactive-viewport) affordance, not a change to rendered document content.

## Non-goals

- A horizontal scrollbar for `left_col`/horizontal scroll -- out of scope; the mode line's existing horizontal-scroll indicator is unaffected.
- Configurability (toggling the scrollbar off, choosing its glyphs/colors) -- ship one fixed, sensible default; a follow-up issue can add configuration if requested.
- Applying this to the plain (non-interactive) rendering path.

## Design notes / links

`draw()` in `viewmd/interactive_pager.py` (around `_run`, roughly lines 1124+) is where each frame's `visible` rows are assembled before the mode line/echo area are appended; this is the natural place to prepend the per-row scrollbar cell plus its gap cell. `_mode_line` (line ~627) already derives the line-range/percentage text this issue's thumb math should mirror. `_crop_row`/`_ansi_slice` (lines ~350, ~524) are the existing column-cropping logic that content width needs to route through once the usable width shrinks by 2.

### Mockup

Leftmost column glyph/color scheme (`█` colored = thumb/visible range, `░` dim = track/rest of document), followed by a blank gap column, next to today's layout for comparison:

```
Today (no scrollbar column):              With scrollbar column (this issue):

# Getting Started                       █ # Getting Started
                                        █
viewmd is a command-line Markdown       █ viewmd is a command-line Markdown
viewer. It renders headers, tables,     █ viewer. It renders headers, tables,
and code blocks straight to your        █ and code blocks straight to your
terminal.                               █ terminal.
                                        ░
## Installation                         ░ ## Installation
                                        ░
Run `pip install viewmd` to get         ░ Run `pip install viewmd` to get
started, or clone the repo and use      ░ started, or clone the repo and use
`./viewmd.sh` for local development.    ░ `./viewmd.sh` for local development.
                                        ░
## Usage                                ░ ## Usage
                                        ░
viewmd path/to/file.md                  ░ viewmd path/to/file.md
--- Getting Started ------- 1-13/40 33% --- Getting Started ------- 1-13/40 33%
? help  / search  t contents  q quit      ? help  / search  t contents  q quit
```

The thumb (`█`, e.g. rendered in the accent color already used for headings/mode line) occupies roughly `body_h * (body_h / len(lines))` of the column's rows, positioned at roughly `body_h * (top / len(lines))` rows down -- proportional to the 33% shown in the mode line's own percentage. The track (`░`) fills the remainder. The blank gap column to its right (unstyled, always a plain space) runs the full `body_h` height regardless of thumb position, keeping the scrollbar visually separated from the document text. Scrolling further down slides the thumb down the column; scrolling to the very bottom flushes it against the last row.

## Acceptance / verification

- New unit tests in `tests/test_interactive_pager.py` (or a sibling test module, matching whatever exists for `_mode_line`/`_crop_row` today) covering: thumb size/position math for a few `(len(lines), body_h, top)` combinations, including the boundary cases top=0 and top=max_top; the "document fits, no scrollbar" case; and that content width shrinks by exactly 2 columns (scrollbar + gap) when the scrollbar is present.
- Manual verification: `./viewmd.sh` a long document in a real terminal, confirm the scrollbar thumb tracks scroll position via arrow keys, mouse wheel, search jump, and ToC jump, and disappears for a short document that fits on one screen.
- `./run-tests.sh` green.

## Peer review

- **code-review agent** (agent), 2026-08-18: found one severe, highly-reproducible bug -- shrinking the content crop width by the scrollbar's reserved 2 columns without accounting for `render_markdown`'s (Rich's) own right-padding of every line out to the full render width made `_crop_row` mistake that padding for real off-screen content, stamping a false `›` truncation marker on nearly every row whenever the render width and the viewport were close enough (the common case: terminal ≤100 columns, or full-width mode). Fixed inline: `draw()`'s two `_crop_row` call sites now measure a row's "real" width after `.rstrip(" ")`, so trailing Rich padding no longer counts as content; re-verified against the review's own 80-column/`CHANGELOG.md` repro (no false markers) and `./run-tests.sh` stayed green. Also flagged `issues/VIEWMD-0080-...md` as apparently deleted -- false alarm, the file is untracked in the primary checkout (created by a sibling worktree session), invisible to this worktree by design, not touched by this change.
- **George Moses** (maintainer), 2026-08-18: accepted, approved to land.

