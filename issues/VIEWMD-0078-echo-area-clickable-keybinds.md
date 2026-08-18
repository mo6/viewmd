---
id: VIEWMD-0078
title: Make the echo-area's short keybinding hint chips clickable
status: in-progress
area: [pager]
effort: medium
created: 2026-08-17
updated: 2026-08-18
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-18
commits: []
related: [VIEWMD-0076]
supersedes: []
changelog:
reason:
---

# Make the echo-area's short keybinding hint chips clickable

## Summary

The echo area (the pager's bottom status row, `_keybind_help()`) always shows a short, context-sensitive taste of keybindings as keycap chips -- `↑/↓ scroll`, `/ search`, `t contents`, `? help`, `q quit`, and so on -- distinct from the full reference the `?` help screen opens (which VIEWMD-0076 already made click-to-invoke). This issue extends the same click-to-invoke mechanism to the echo area's own chips, so a reader can click e.g. the `t` chip directly to open the table of contents without first opening the full `?` help screen.

## Motivation / problem

Raised by the maintainer while verifying VIEWMD-0076's help-screen click-invoke: "file an issue to make the key bindings clickable too" -- the full `?` help table is already click-to-invoke, but the always-visible echo-area hint line (the thing a reader actually looks at moment-to-moment, not just when `?` is open) isn't. `_keybind_help()` (`viewmd/interactive_pager.py:754-791`) builds this line as a sequence of `(key, label)` pairs joined into one colored string, with no per-chip column-span tracking today -- unlike `_HELP_GROUPS`/`_help_box` (VIEWMD-0076), there's currently no way to tell which chip a given column of the rendered echo line belongs to.

## Requirements

1. MUST resolve a click landing on the echo-area row (the last terminal row) to whichever keycap chip (if any) it fell on, and invoke that chip's action exactly as if the corresponding key were pressed -- reusing `_dispatch_base` (VIEWMD-0076) the same way the help screen's click-invoke does.
2. MUST cover every chip `_keybind_help()` can currently show, in both its `popup_open` and base layouts -- including the `B`/`prev file` chip once it's showing (VIEWMD-0076/this session's follow-up) and any other conditionally-shown chip (`w`, `Esc`/clear-highlight, `t`).
3. MUST NOT change `_keybind_help()`'s visible text, chip order, or styling -- this issue only adds a way to resolve a click against the *existing* rendered line, not change what it says.
4. MUST NOT apply while the echo area is showing something other than the default keybinding hint (the search prompt, a one-shot message like "Search failed", or the raw `Search: ...` typing state) -- a click during any of those is a no-op, matching how the row's meaning has already changed to something click-invoke doesn't apply to.
5. SHOULD share as much of the click-resolution approach with the `?` help screen's own (VIEWMD-0076) as is reasonable, rather than inventing a second, differently-shaped mechanism for what is conceptually the same problem (click column -> which chip -> which action).

## Non-goals

- Any change to which chips are shown or when (that's `_keybind_help()`'s existing, unrelated logic) -- this issue is purely about making the *existing* chips clickable.
- Click-invoke for the popup-open echo-area layout's chips if any of them turn out to have the same single-vs-ambiguous-action distinction the `?` help screen's rows do (VIEWMD-0076's `_HELP_GROUPS` comment) -- apply the same "no single unambiguous action -> no-op" rule there rather than forcing an action onto an ambiguous chip.
- Hover states, tooltips, or any other affordance beyond the click itself.

## Design notes / links

Directly follows [VIEWMD-0076](VIEWMD-0076-mouse-click-navigation.md), reusing its click event (`_read_event`'s `click` kind) and `_dispatch_base` dispatch. The open design question: `_keybind_help()` returns one opaque colored string today, built by joining `f"{_keycap(key)} {label}"` pieces (`viewmd/interactive_pager.py:791`) -- this needs to change shape to also expose each chip's column span and invoke event, the same way `_help_box` was changed (VIEWMD-0076) to return `(box, invokes)` instead of just `box`. Likely the cleanest approach: build the pairs list with an attached `Event | None` per chip (mirroring `_HELP_GROUPS`' own third element) and have `_keybind_help` return `(text, spans)` where `spans` is a list of `(start_col, end_col, Event | None)` -- the caller (`draw()`) already knows the echo line starts at column 0 of the last terminal row, so no popup-origin math is needed here, just a column-range lookup, simpler than `_popup_hit`.

## Acceptance / verification

- `./run-tests.sh` green, including: a test that every chip `_keybind_help()` can render has a resolvable column span; a test that clicking within a chip's span in the interactive pager invokes the same action pressing that key would (reusing whatever fixture/pattern VIEWMD-0076 used for its own click-dispatch tests, to the extent the loop itself remains only indirectly testable); a test that a click on the echo area while it's showing the search prompt or a one-shot message is a no-op (requirement 4).
- Manual check: the maintainer clicks a chip in the bottom status line (e.g. `t`) with no popup/help open and confirms it performs that action, the same as pressing the real key.

## Peer review

- (agent, independent) Verified `_keybind_help()`'s new `(text, spans)` column-span arithmetic against 48 parameter combinations (all spans matched their chip's exact text, no drift/overlap); mechanically reconstructed the old `"  ".join(...)` output across the same 48 combinations and diffed byte-for-byte against the new output (requirement 3, all match); confirmed `echo_showing_default_hint` is captured before `echo_message` is cleared later in the same loop iteration (requirement 4); confirmed the echo row's `ev.row - 1 == body_h + 1` coordinate math against the existing document-click convention; checked narrow-terminal truncation, zero-chips (impossible, `q` always appended), and click-in-gap edge cases; confirmed test coverage is meaningful, not tautological, and matches VIEWMD-0076's own precedent for what's unit- vs. loop-tested. `./run-tests.sh` green (1062 passed, ruff/pip-audit/issues clean). No bugs found.

