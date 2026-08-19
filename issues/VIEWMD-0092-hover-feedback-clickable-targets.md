---
id: VIEWMD-0092
title: Visible hover feedback for clickable targets in the interactive pager
status: proposed
area: [pager]
effort:
created: 2026-08-19
updated: 2026-08-19
accepted_by:
accepted_at:
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Visible hover feedback for clickable targets in the interactive pager

## Summary

Highlight whatever clickable target the mouse is currently positioned over — a body-text link, a row in the table-of-contents popup, a keybinding row in the `?` help screen, a directory-listing row, or the width-toggle chip in the echo area — so a reader can tell something is clickable, and which thing, before clicking it.

## Motivation / problem

The interactive pager (`viewmd/interactive_pager.py`) already resolves a mouse click to a link/row/chip on release (VIEWMD-0076's `_popup_hit` and the body-text click-to-follow path), but nothing renders differently until that click lands. A link in body text carries its normal Markdown-link styling whether or not it resolves to something clickable in the pager (a link to an external URL, for instance, is not click-to-follow-able — see the README's "if it resolves to a local .md file" qualifier), and ToC/help/directory rows and the width-toggle chip give no visual response to the cursor sitting on them. A reader has no way to discover what's actually interactive short of clicking and seeing what happens.

## Requirements

1. MUST enable xterm mouse-motion reporting (`\x1b[?1002h` or `\x1b[?1003h`, layered on the click reporting already turned on by `_MOUSE_ON`) so the pager receives events as the cursor moves, not only on click.
2. MUST visually distinguish (e.g. reverse-video or underline, consistent with the pager's existing link styling) whichever single target is currently under the cursor:
   - a body-text link that resolves to a local `.md` file (click-to-follow-able, per the existing `_resolve_click_href`/`doc_dir` logic) — MUST NOT highlight a link that does not resolve (e.g. an external URL), so hover feedback never implies a target is clickable when the click handler would treat it as a no-op;
   - a row in the ToC popup or `?` help screen (per `_popup_hit`'s existing hit-testing);
   - a directory-listing row;
   - the width-toggle chip in the echo area.
3. MUST clear the highlight immediately when the cursor moves off a target, including moving off it during a scroll or resize.
4. MUST NOT change what a click does, or which targets are click-to-follow-able — this issue is purely the visual feedback layer on top of hit-testing that already exists.
5. MUST NOT noticeably degrade scroll/redraw performance — motion-tracking mode reports every cursor movement, including drags across a wide swath of the terminal, and the highlight update must stay cheap enough not to introduce visible lag (reuse the existing partial-redraw/diff machinery rather than a full-screen repaint per motion event).
6. SHOULD fall back gracefully (no crash, no stray escape-sequence artifacts) on a terminal that does not support motion reporting — click-only behavior, exactly as today, in that case.

## Non-goals

- No change to keyboard-driven navigation or focus indication (this is mouse-hover only).
- No tooltip/status-bar description of what a hovered link points to (just the highlight itself).
- No hover feedback for plain scrollable content that isn't a clickable target.

## Design notes / links

Builds on the click-to-follow hit-testing already implemented for VIEWMD-0076 (`_resolve_click_href`, `_popup_hit`, the click-column-span table in the echo-area help hint) — this issue reuses that resolution logic for hover instead of duplicating it, firing it on motion events the same way it fires today on click events. Motion-tracking mode (1002/1003) is a meaningfully different data volume than the current click-only (1000) mode; profile against a large document before committing to always-on 1003 (any-motion) versus 1002 (motion-while-button-held, which would not achieve hover-without-clicking and is likely not sufficient for this issue's goal — confirm during implementation).

Confirmed empirically (2026-08-19, macOS Terminal.app 470.2/`TERM_PROGRAM=Apple_Terminal`, `xterm-256color`): enabling `\x1b[?1000h\x1b[?1003h\x1b[?1006h` produces a continuous stream of SGR mouse reports (`\x1b[<35;COL;ROWM`, button code `35` = `32 + 3`, xterm's "motion, no button pressed" encoding) as the mouse moves with no click — i.e. Terminal.app does support `1003` any-motion tracking, contrary to its long-standing reputation for click-only support. Requirement 6's "fall back gracefully on a terminal that does not support motion reporting" should stay as a general defensive measure for less-capable terminals, but is not expected to trigger on Terminal.app itself.

## Acceptance / verification

New tests in `tests/test_interactive_pager.py` covering: a synthesized motion event over a resolvable body link renders it highlighted and a motion event over a non-resolvable link does not; motion into and back out of a ToC/help-popup row toggles the highlight on and off; a motion event with no corresponding target leaves rendering unchanged. Manual verification in a real terminal (`./viewmd.sh` against a document with wikilinks) for the actual visual feel, since escape-sequence-level tests can't assert on-screen appearance directly.

## Peer review

