---
id: VIEWMD-0075
title: Support horizontal mouse-wheel/trackpad scroll in the internal pager
status: implemented
area: [pager]
effort: low
created: 2026-08-17
updated: 2026-08-17
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-17
commits: [8b4321b]
related: [VIEWMD-0007, VIEWMD-0067, VIEWMD-0070, VIEWMD-0072]
supersedes: []
changelog: "[1.35.0]"
reason:
---

# Support horizontal mouse-wheel/trackpad scroll in the internal pager

## Summary

Recognize SGR mouse-report buttons 66/67 (native horizontal wheel tilt / trackpad two-finger sideways swipe, where a terminal sends it) *and* buttons 68/69 (Shift held while scrolling the ordinary vertical wheel -- the fallback convention on terminals that never send 66/67 at all) in `viewmd/interactive_pager.py`'s input parser, and map both to the same `left_col` adjustment already driven by the `h`/`l`/Left/Right keys, so a horizontal scroll gesture pans content wider than the terminal the same way a vertical wheel gesture already scrolls it up/down.

## Motivation / problem

`_read_event()` (`viewmd/interactive_pager.py:446-483`) parses SGR mouse reports (`\x1b[<Cb;Cx;CyM`) but only recognizes `Cb` 64/65 (vertical wheel up/down), returning `Event("key", "")` (a no-op) for every other button code -- including 66/67, which some xterm-compatible terminals (iTerm2, Kitty) send for horizontal wheel tilt and for a trackpad's horizontal two-finger swipe when mouse reporting is active. The pager already supports horizontal scrolling of content wider than the terminal (`left_col`, stepped by `h_step = 8` via `h`/`l`/arrow keys, `viewmd/interactive_pager.py:1124-1128`) but a reader with a horizontal-scroll-capable mouse or trackpad currently has no gestural way to reach it, only the keyboard.

Verified during implementation (raw-byte probe against a live terminal, not just written from the spec): macOS's built-in Terminal.app never sends 66/67 at all -- a genuine two-finger horizontal trackpad swipe produces nothing distinguishable from ordinary vertical wheel noise. It does, however, report the Shift modifier bit on the ordinary vertical wheel (SGR adds 4 for a held Shift, so 64/65 become 68/69), confirmed the same way. Shift+wheel-as-horizontal-scroll is the same fallback convention other GUI apps (browsers, Excel) use for exactly this gap, so both paths are in scope here rather than only the native one -- a Terminal.app reader would otherwise get no horizontal mouse/trackpad support at all from this issue.

## Requirements

1. MUST parse SGR mouse-report button codes 66 and 67 (native horizontal wheel) in `_read_event()` into two new `Event` kinds (`wheel_left`/`wheel_right`), alongside the existing `wheel_up`/`wheel_down` handling.
2. MUST also parse button codes 68 and 69 (Shift + vertical wheel) into the same `wheel_left`/`wheel_right` events, as the fallback for terminals (confirmed: macOS Terminal.app) that never send native 66/67.
3. MUST move `left_col` by `h_step` per `wheel_left`/`wheel_right` event in the normal (non-popup, non-search, non-help) pager state, clamped the same way `h`/`l` already clamp (`0` on the left, `max_content_width - term_w` on the right).
4. MUST NOT change vertical wheel behavior (`wheel_up`/`wheel_down`, buttons 64/65) or any existing keyboard scrolling.
5. SHOULD leave `wheel_left`/`wheel_right` inert (no-op, matching today's fallthrough) in the popup, search, and help states, the same way horizontal scroll keys have no meaning there today.

## Non-goals

- Configuring or reversing scroll direction/step size for the horizontal wheel -- matches the existing vertical wheel and `h`/`l` keys, which are also fixed.
- Any change to the external-`less` delegated path -- there isn't one left to change; VIEWMD-0072 already moved every paged case onto the internal pager this issue modifies.
- Touchpad-specific gesture tuning (momentum, inertia) -- out of scope; this only decodes the same terminal-level SGR events the vertical wheel already relies on.

## Design notes / links

Terminal emulators that support native horizontal wheel/trackpad-swipe reporting encode it as SGR mouse buttons 66 (tilt/swipe left) and 67 (tilt/swipe right); a terminal without that support instead reports an ordinary vertical wheel event (64/65) with the Shift modifier bit set, which SGR encodes by adding 4 to the button code (68/69) -- both are decoded to the same `wheel_left`/`wheel_right` events since either way the reader's intent (pan horizontally) is the same. The same `\x1b[?1000h\x1b[?1006h` mode already enabled by `_MOUSE_ON` (`viewmd/interactive_pager.py:55`) for vertical wheel reporting covers all of these, so no new terminal-mode setup is needed, only decoding the extra button codes already arriving on the wire. See `viewmd/interactive_pager.py:467-484` for the existing 64/65 parse extended with 66/67/68/69, and `:1128-1133` for the `left_col` step logic reused.

Confirmed empirically, not just from the SGR spec: a standalone raw-byte probe script (`\x1b[?1000h\x1b[?1006h` enabled, dumping every `os.read()` on a raw tty) run directly by the maintainer against macOS Terminal.app showed a genuine two-finger horizontal trackpad swipe producing nothing but ordinary 64/65 vertical-wheel noise -- no 66/67 ever appears on that terminal -- while holding Shift during an ordinary vertical scroll reliably produced 68/69. This is why requirement 2 (the Shift fallback) is in scope alongside requirement 1 (native 66/67), rather than only the latter: without it, a Terminal.app reader would get no horizontal mouse/trackpad support from this issue at all, only iTerm2/Kitty users would.

## Acceptance / verification

- `./run-tests.sh` green, including tests asserting `_read_event()` returns the new wheel-left/wheel-right event kinds for SGR sequences with button codes 66/67 (native) and 68/69 (Shift+vertical fallback), and that button codes 64/65 and non-mouse input are unaffected.
- No dedicated test for the main loop's `left_col` movement itself: `tests/test_interactive_pager.py` has no harness that drives `_run()`'s input loop for any key (the existing `h`/`l` branches aren't covered that way either), so `wheel_left`/`wheel_right` are held to the same bar -- the `_read_event()` parsing tests above plus `wheel_left`/`wheel_right` reusing the identical, already-relied-upon `h_step`/clamp expression the `h`/`l` branches use (`viewmd/interactive_pager.py:1128-1132`) is accepted as sufficient without new loop-driving test infrastructure.
- Manual check: on macOS Terminal.app, Shift+scroll-wheel pans the view left/right in `./viewmd.sh docs/mermaid-flowchart.md`. Confirmed by the maintainer, 2026-08-17. Native 66/67 (iTerm2/Kitty-style horizontal swipe) verified by code/protocol inspection only -- no such terminal was available to test live in this session; re-verify live on one if/when convenient.

## Peer review

- **code-review skill** (agent, independent), 2026-08-17: Reviewed the diff against all requirements across correctness, reuse/simplification, altitude, and conventions angles. No CONFIRMED or PLAUSIBLE correctness findings. Confirmed `wheel_left`/`wheel_right` correctly fall through as no-ops in popup/search/help states (requirement 4) and reuse the existing `h_step`/`max_content_width`/`left_col` clamp logic (requirement 2) rather than duplicating it. Flagged that the acceptance criteria's main-loop `left_col` test had no existing harness to extend (the `h`/`l` branches aren't loop-tested either); resolved by relaxing that acceptance line rather than building new test infrastructure, per maintainer's explicit choice.
- **code-review skill** (agent, independent), 2026-08-17: Second pass, run after the Shift+vertical-wheel fallback (button codes 68/69) was added on top of the first review. Verified SGR button/modifier math (64/65 vertical, +4 for Shift = 68/69, 66/67 native horizontal, all correct per xterm convention), correct reuse of the existing `h_step`/clamp expression, correct no-op fallthrough in popup/search/help states, no other call sites of `Event`/wheel kinds needing updates, ruff clean, and the new/targeted tests pass. No correctness, cleanup, altitude, or convention issues found.
- **George Moses** (maintainer), 2026-08-17: Confirmed native 66/67 was the wrong assumption for this terminal -- ran a standalone raw-byte probe against macOS Terminal.app showing a genuine horizontal trackpad swipe never sends 66/67, only Shift+wheel (68/69) is distinguishable. After the fallback was added, confirmed live in `./viewmd.sh docs/mermaid-flowchart.md` on Terminal.app that Shift+scroll-wheel now pans the view correctly. Accepted.
