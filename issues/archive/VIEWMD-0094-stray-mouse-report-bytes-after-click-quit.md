---
id: VIEWMD-0094
title: Clicking the 'q quit' keybinding row leaves stray SGR mouse-report bytes on the terminal after exit
status: implemented
area: [pager]
effort: low
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: [a955bf4]
related: [VIEWMD-0076, VIEWMD-0078]
supersedes: []
changelog: "[1.42.2]"
reason:
---

# Clicking the 'q quit' keybinding row leaves stray SGR mouse-report bytes on the terminal after exit

## Summary

Quitting the interactive pager by clicking the `q  quit` row in the `?` help screen (rather than pressing the `q` key directly) leaves visible garbage text on the terminal line after the pager exits — reported as `0;69;46m` left sitting at the shell prompt. Quitting via an actual keypress does not exhibit this.

## Motivation / problem

`_read_event()` (`viewmd/interactive_pager.py`) parses an SGR mouse report `\x1b[<Cb;Cx;CyM` (press) or `...m` (release) one at a time. Its own comment on the click-press branch states the design intentionally: "the release ('m') is ignored" — i.e. a physical click generates two reports back-to-back (press then release), `_read_event` returns an `Event("click", ...)` on the press report, and the paired release report is left unread in the fd, to be silently discarded as a harmless no-op `Event("key", "")` the *next* time `_read_event()` is called (its `btn == 0 and m.group(4) == "M"` check fails for a lowercase-`m` release, falling through to the empty-key return).

That assumption — "there will always be a next `_read_event()` call to mop it up" — breaks exactly when the click itself causes the pager to quit: clicking the help screen's `q  quit` row is hit-tested (`_popup_hit`), resolved to its bound `Event("key", "q")`, and fed through `_dispatch_base()`, which returns `True` and makes the main loop `break` immediately (see the help-screen click-invoke branch and `_dispatch_base`'s own `ev.value == "q"` short-circuit). The loop exits before ever calling `_read_event()` again, so the pending release-report bytes (`\x1b[<0;69;46m` for the reported case) are still sitting unread in the terminal's input buffer when `_EXIT_SCREEN` restores cooked/echoed mode. The shell then reads those leftover bytes off stdin as if they were freshly typed: its line editor evidently consumes/recognizes the `\x1b[<` CSI prefix as something invalid, discards it, and echoes the rest verbatim — leaving the visible `0;69;46m` tail on the terminal line, matching exactly what was reported.

## Requirements

1. MUST NOT leave any unread SGR mouse-report bytes in the terminal's input buffer when the pager exits, regardless of which key/click path triggered the quit.
2. MUST fix this specifically for the click-invoked-quit path (clicking `q  quit` in the help screen; also check the echo-area click-invoke path, which feeds synthesized events through the same `_dispatch_base()` and could in principle bind a quit-causing chip too) without regressing the existing keyboard-`q`-quit path, which is unaffected today.
3. MUST NOT change behavior for a click that does not cause a quit — the existing "release report is silently discarded by the next `_read_event()` call" behavior is fine to keep as the general mechanism; only the case where there is no next call needs fixing.
4. SHOULD prefer draining the paired release report proactively right after consuming a press report (inside `_read_event()` or its caller, with a short non-blocking read/select, consistent with how the existing bare-Esc-vs-escape-sequence disambiguation already uses `select.select(..., 0.05)`) over a narrower "only drain before quitting" special case, so the fix covers this bug class in general rather than one specific call site.
5. MUST NOT introduce a noticeable input-latency regression from the added drain (keep it bounded, non-blocking-with-timeout, matching the existing `select.select` pattern already used elsewhere in `_read_event`).

## Non-goals

- No change to the double-report design of SGR mouse mode itself (press vs. release) — this is a leftover-bytes bug, not a protocol change.
- No change to `_MOUSE_ON`/`_MOUSE_OFF`/`_EXIT_SCREEN`'s existing terminal-mode-restore sequence beyond what's needed to stop leaking pending bytes.

## Design notes / links

`_read_event()`'s click-press branch (`viewmd/interactive_pager.py`, the `if btn == 0 and m.group(4) == "M":` branch and its preceding "the release ('m') is ignored" comment) is where the release report is currently left unconsumed. The click-invoked-quit path runs through the help-screen click-invoke branch and `_dispatch_base()`'s `ev.value == "q"` check (VIEWMD-0076's click-invoke mechanism, extended by VIEWMD-0078 to the echo area). `_EXIT_SCREEN` (`_MOUSE_OFF + "\x1b[?25h\x1b[?1049l"`) is what restores cooked terminal mode; the leak happens because it runs before the release bytes are drained, not because of anything wrong with `_EXIT_SCREEN` itself.

## Acceptance / verification

New test in `tests/test_interactive_pager.py`: simulate an SGR click-press report immediately followed by its paired release report on the input fd, where the press resolves (via help-screen or echo-area click-invoke) to a quit; assert the release report's bytes are fully consumed before the pager returns, not left in the (simulated) fd. Manual verification: in a real terminal, open the pager, press `?`, click the `q  quit` row with the mouse, confirm the shell prompt line afterward is clean — no stray escape-sequence remnants. `./run-tests.sh` green.

## Peer review

- **independent review agent** (agent), 2026-08-19: four findings. (1) a release arriving after the 0.05s drain window can still leak on click-to-quit -- accepted as the residual of this issue's chosen drain-after-press design (requirements 4/5: the same `select(..., 0.05)` window as bare-Esc); the maintainer's live test of the reported path was clean. (2) ~50ms wait on a click whose release isn't already queued -- same, matching the issue's required existing-`select` pattern. (3) `_unread` leftover after a non-quit click stalled the main loop because `select` only watched the tty fd -- fixed inline (skip `select` while `_unread` is non-empty), with `test_non_quit_click_then_key_in_same_burst_is_not_stalled`. (4) original tests only covered press+release already concatenated -- the stall test covers a following key through `_run`.
- **George Moses** (maintainer), 2026-08-19: tested in a real terminal; click-q-quit leaves a clean prompt. "I've tested it: it works." Asked to commit, merge, and close.

