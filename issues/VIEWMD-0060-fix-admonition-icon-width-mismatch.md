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

The `WARNING` admonition card (VIEWMD-0059) renders with a misaligned right border in real
terminals -- the border doesn't reach the same right edge as `NOTE`/`TIP`/`IMPORTANT`/`CAUTION`
cards, producing a visibly bent/uneven corner. Confirmed by the maintainer in a real terminal,
both in color and with `--no-pager`, against `docs/example.md`'s "Admonition callouts" section.

## Motivation / problem

`ViewmdBlockQuote.__rich_console__` (`viewmd/render.py`) sizes the header's trailing dash-fill by
subtracting `wcwidth.wcswidth()` of the icon from the available width. `wcswidth` reports **2**
for `⚠️` (U+26A0+U+FE0F, `WARNING`) -- Unicode's emoji-presentation rule for the VS16-suffixed
pair -- but the *bare* base codepoint's own per-character `wcwidth` is 1, and several terminal
fonts render the pair narrow (1 column), unlike `📝`/`💡`/`🛑` (`NOTE`/`TIP`/`CAUTION`), which are
fully in the astral plane with no narrow fallback and render wide essentially everywhere. When the
real terminal consumes fewer columns for the icon than `wcswidth` assumed, the computed dash-fill
(sized for the wider assumption) undershoots the terminal's real column count, so `WARNING`'s
right border lands short of where the other cards' borders land.

**`IMPORTANT`'s `❗` (U+2757) is not part of this bug** -- both `wcswidth` and the bare
per-character `wcwidth` already agree it's width 2, with no ambiguity, and it renders flush in the
maintainer's terminal. An earlier draft of this fix incorrectly generalized the diagnosis to
`IMPORTANT` too and applied the same 1-column override to it, which *introduced* a real
misalignment (the header became 1 column too wide, overshooting past the footer) that the
maintainer caught in review; that override was reverted, and `IMPORTANT` needs no code change.

VIEWMD-0059's own requirement 6 already flagged this class of bug for `WARNING` specifically
("several terminals render the pair one column wider than wcwidth alone reports for it") and
hand-adjusted the header's icon-to-label spacing (`icon_pad`) for it during peer review -- but
that only fixed the visual gap between the icon and the label. The border-fill math still trusted
`wcwidth`'s width-2 verdict for `WARNING`, which this issue's report shows is wrong for the
maintainer's terminal.

## Requirements

1. MUST size the header's dash-fill for `WARNING` using a hand-verified narrow (1-column) width
   for its icon, independent of what `wcwidth.wcswidth()` reports for it -- analogous to how
   `icon_pad` already overrides the icon-to-label gap independent of `wcwidth`.
2. MUST leave `NOTE`/`TIP`/`IMPORTANT`/`CAUTION` (and the generic fallback) unaffected -- their
   icons are unambiguously wide (or already render flush) and their cards already render flush.
3. MUST keep the header and footer borders landing on the same right column for every canonical
   type and the generic fallback, verified both with and without color, matching this issue's
   report.
4. MUST NOT regress VIEWMD-0059's fixture/test suite; update whichever fixtures/tests assumed the
   old (wrong) width math.

## Acceptance / verification

- A fixture or test asserting the header and footer land at the same rendered width for `WARNING`
  specifically (the existing `test_header_and_body_borders_share_display_width` check is
  self-consistent against `wcwidth` and won't catch this -- it needs to check against the
  intentional override instead), and confirming `IMPORTANT` is unchanged from VIEWMD-0059.
- `./run-tests.sh` green.
- Maintainer re-verifies the rendered `docs/example.md` admonitions section in their own terminal.

## Peer review

- Claude (2026-08-15): first implementation attempt applied the `icon_width=1` override to both
  `WARNING` and `IMPORTANT`, reasoning both were "ambiguous-width dingbats" -- wrong for
  `IMPORTANT`, whose `❗` has no `wcswidth`/per-character-`wcwidth` disagreement at all (both agree
  on 2). This introduced a real regression (header 1 column too wide, overshooting the footer),
  which the maintainer caught by re-screenshotting their terminal.
- Claude (2026-08-15): reverted the `IMPORTANT` override (back to `None`, i.e. trust `wcswidth`,
  matching VIEWMD-0059's original, correct behavior) and regenerated `important.out` to match.
  Kept the `WARNING` override (`icon_width=1`), which the maintainer's screenshots show is
  correctly flush. Narrowed `test_header_and_body_borders_share_display_width`'s intentional-gap
  table (`_WCWIDTH_OVERSHOOT`) to `WARNING` only. `./run-tests.sh` green.
