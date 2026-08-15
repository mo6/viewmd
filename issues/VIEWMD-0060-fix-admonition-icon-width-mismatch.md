---
id: VIEWMD-0060
title: Fix admonition card border misalignment for ambiguous-width icons
status: in-progress
area: [render]
effort: low
created: 2026-08-15
updated: 2026-08-15
accepted_by: George Moses
accepted_at: 2026-08-15
commits: []
related: [VIEWMD-0059]
supersedes: []
changelog:
reason:
---

# Fix admonition card border misalignment for ambiguous-width icons

## Summary

The `WARNING` and `IMPORTANT` admonition cards (VIEWMD-0059) render with a misaligned right
border in real terminals -- the border doesn't reach the same right edge as `NOTE`/`TIP`/
`CAUTION` cards, producing a visibly bent/uneven corner. Confirmed by the maintainer in a real
terminal, both in color and with `--no-pager`, against `docs/example.md`'s "Admonition callouts"
section.

## Motivation / problem

`ViewmdBlockQuote.__rich_console__` (`viewmd/render.py`) sizes the header's trailing dash-fill by
subtracting `wcwidth.wcswidth()` of the icon from the available width. `wcswidth` reports **2**
for every canonical icon, including `❗` (U+2757, `IMPORTANT`) and `⚠️` (U+26A0+U+FE0F,
`WARNING`). Both are "ambiguous-width" dingbats: `wcswidth`'s Unicode-9 emoji-presentation rule
treats them as wide, but they have a legitimate narrow (text-presentation) glyph and several
terminal fonts render them at 1 column, not 2 -- unlike `📝`/`💡`/`🛑` (`NOTE`/`TIP`/`CAUTION`),
which are fully in the astral plane with no narrow fallback and render wide essentially
everywhere. When the real terminal consumes fewer columns for the icon than `wcswidth` assumed,
the computed dash-fill (sized for the wider assumption) undershoots the terminal's real column
count, so the card's right border lands short of where the other cards' borders land.

VIEWMD-0059's own requirement 6 already flagged this class of bug for `WARNING` specifically
("several terminals render the pair one column wider than wcwidth alone reports for it") and
hand-adjusted the header's icon-to-label spacing (`icon_pad`) for it during peer review -- but
that only fixed the visual gap between the icon and the label. The border-fill math still trusts
`wcwidth`'s width-2 verdict for both `WARNING` and `IMPORTANT`, which this issue's report shows is
wrong for the maintainer's terminal.

## Requirements

1. MUST size the header's dash-fill for `WARNING` and `IMPORTANT` using a hand-verified narrow
   (1-column) width for their icons, independent of what `wcwidth.wcswidth()` reports for them --
   analogous to how `icon_pad` already overrides the icon-to-label gap independent of `wcwidth`.
2. MUST leave `NOTE`/`TIP`/`CAUTION` (and the generic fallback) unaffected -- their icons are
   unambiguously wide and their cards already render flush.
3. MUST keep the header and footer borders landing on the same right column for every canonical
   type and the generic fallback, verified both with and without color, matching this issue's
   report.
4. MUST NOT regress VIEWMD-0059's fixture/test suite; update whichever fixtures/tests assumed the
   old (wrong) width math.

## Acceptance / verification

- A fixture or test asserting the header and footer land at the same rendered width for
  `IMPORTANT` and `WARNING` specifically (the existing `test_header_and_body_borders_share_display_width`
  check is self-consistent against `wcwidth` and won't catch this -- it needs to check against the
  intentional override instead).
- `./run-tests.sh` green.
- Maintainer re-verifies the rendered `docs/example.md` admonitions section in their own terminal.

## Peer review
