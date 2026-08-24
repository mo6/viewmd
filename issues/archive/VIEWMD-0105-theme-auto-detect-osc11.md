---
id: VIEWMD-0105
title: Add --theme auto, detecting light/dark via an OSC 11 background-color query
status: implemented
area: [render, config, cli]
effort: medium
created: 2026-08-21
updated: 2026-08-21
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-21
commits: [a92a6fe, a7d03d1]
related: [VIEWMD-0091]
supersedes: []
changelog: "[1.50.0]"
reason:
---

# Add --theme auto, detecting light/dark via an OSC 11 background-color query

## Summary

Add a third `--theme` value, `auto`, that queries the terminal's actual background color via an
OSC 11 escape sequence (`\x1b]11;?\x07`) and picks `light` or `dark` accordingly, falling back to
`dark` (today's existing default) when the terminal doesn't answer. `dark`/`light` stay exactly
as VIEWMD-0091 shipped them; `auto` is a new, opt-in third choice, not a new default, so this is
purely additive.

## Motivation / problem

VIEWMD-0091 shipped `--theme {dark,light}` but explicitly ruled out auto-detection (requirement
5: "MUST NOT attempt to auto-detect the terminal's actual background color... since terminal
background detection is unreliable across emulators"), written as an untested assumption at
design time. A manual probe (raw-mode `/dev/tty` write of `\x1b]11;?\x07`, read with a timeout)
was hand-verified by the maintainer against both a dark-mode and a light-mode real terminal
session and correctly resolved each: dark returned `rgb:213d/2743/33e7` (RGB ≈(33,39,52),
luminance 38.7 → dark), light returned `rgb:ffff/ffff/ffff` (RGB (255,255,255), luminance 255.0
→ light) — matching the AGENTS.md precedent from VIEWMD-0092 that a terminal-capability
assumption from memory is a hypothesis until checked against a real terminal, not a fact. Today a
user has to know their terminal's background and pass `--theme light` themselves every time (or
set it in their config file); `auto` removes that manual step for terminals that answer the
query, without forcing detection on everyone or changing the existing default.

## Requirements

1. MUST add `auto` to `THEME_CHOICES` (`viewmd/config.py`) alongside the existing `dark`/`light`,
   accepted by both `--theme auto` and a config file's `theme = auto`.
2. MUST NOT change the default: an omitted `--theme`/config `theme` key still resolves to `dark`,
   exactly as today. `auto` only activates when explicitly requested.
3. MUST query the terminal via OSC 11 (`\x1b]11;?\x07`) only when `--theme auto` (directly or via
   config) actually resolves to being used, and only when stdout is a tty (`--no-pager`/piped
   output has no interactive terminal to query, so it MUST fall back to `dark` immediately without
   attempting a query at all — matches the existing `--color auto` tty-detection precedent).
3a. The query MUST open and read from `/dev/tty` directly (not `sys.stdin`), matching this
   project's other tty-vs-stdin handling precedent (`interactive_pager.run()`'s own reasoning,
   `AGENTS.md`), since stdin may be a pipe.
4. MUST use a short, bounded read timeout (e.g. a few hundred milliseconds) waiting for the
   terminal's response, and MUST fall back to `dark` on timeout, a malformed/unparseable reply, or
   any `OSError` opening/reading `/dev/tty` -- a terminal or multiplexer (tmux/screen without OSC
   passthrough configured is a known real case) that never answers MUST NOT hang the CLI waiting
   for a reply that will never come, and MUST NOT crash the render.
5. MUST restore the tty's original termios settings (the raw mode entered to read the reply)
   before proceeding, in every code path including the timeout/fallback ones -- a crash or early
   return must not leave the user's shell in raw mode afterward.
6. MUST parse the reply's `rgb:RRRR/GGGG/BBBB` component (2 or 4 hex digits per channel,
   normalized to 0-255) and classify by relative luminance (`0.299r + 0.587g + 0.114b`, the same
   formula the maintainer's own verification probe used) -- >127 is `light`, otherwise `dark`. The
   exact luminance threshold is an implementation detail, not specified more precisely here.
7. MUST NOT add any measurable startup latency for `--theme dark`/`--theme light`/an omitted
   `--theme` -- the OSC 11 query only ever runs for `auto`.
8. SHOULD document the tmux/screen OSC-passthrough limitation in README (a known, not-fixed-here
   case where `auto` silently falls back to `dark`) rather than silently leaving it undiscoverable.

## Non-goals

- No live re-detection while the pager is running (a terminal theme switched mid-session is not
  picked up until the next invocation) -- this queries once, at startup, same as `--color auto`'s
  own one-shot tty check.
- No OSC 10 (foreground color) or any other terminal-state query -- background only.
- No change to `dark`/`light`'s own existing behavior, palettes, or requirement coverage from
  VIEWMD-0091 -- this issue only adds the third `auto` choice and its detection mechanism.
- No attempt to make `auto` the new default -- opt-in only, per requirement 2.

## Design notes / links

Precedent for the query/timeout/raw-mode mechanics: the maintainer's own hand-run verification
script (raw `/dev/tty` write + `select`-based timeout + termios restore), not re-derived from
scratch. Precedent for tty-vs-non-tty branching: `viewmd/__main__.py`'s existing `--color auto`
resolution and `viewmd.pager.should_page`. See VIEWMD-0091 (`issues/archive/`) for the palette
system this plugs into -- `auto` only decides which of `dark`/`light` `_resolve_theme`-equivalent
logic in `viewmd/__main__.py` picks, it does not touch `viewmd/render.py`'s palette tables at all.

## Acceptance / verification

New tests in `tests/test_main.py`/a new `tests/test_theme_detect.py` covering: `--theme auto`
falls back to `dark` when stdout is not a tty (no query attempted, asserted via a monkeypatched
`/dev/tty` open that would raise if called); a mocked OSC 11 reply resolves to `light`/`dark`
correctly at a few RGB boundary cases; a timeout/malformed-reply/`OSError` each fall back to
`dark` without raising; termios settings are restored after every path (mock `termios.tcsetattr`
and assert it's called with the original attrs even on the timeout path). A manual verification
note in the issue's own Peer review section is expected too, the same way VIEWMD-0091's `--theme
light` contrast needed a real-terminal check no automated test can substitute for -- `--theme
auto` in both a real dark-background and light-background terminal session, confirming it
actually renders with the corresponding palette end to end (not just that the query parses
correctly in isolation). `./run-tests.sh` green.

## Peer review

- (agent, implementer self-review, not a substitute for an independent pass per AGENTS.md) Added `"auto"` to `THEME_CHOICES` (`viewmd/config.py`) -- `_parse_theme` and the CLI `--theme` argparse `choices` both derive from that tuple, so both accept it with no further change needed; added `test_parse_config_accepts_theme_auto`. New module `viewmd/theme_detect.py` holds all the raw-tty/termios/select mechanics (kept out of `viewmd/render.py`/`viewmd/config.py` since nothing else in either file touches termios), exporting one public function, `detect_terminal_theme() -> str`. `viewmd/__main__.py`'s theme resolution: `theme = coalesce(args.theme, cfg.theme, "dark")` unchanged, followed by `if theme == "auto": from viewmd.theme_detect import detect_terminal_theme; theme = detect_terminal_theme()` -- the import is local to that branch so `--theme dark`/`--theme light`/an omitted `--theme` never even import the module, let alone call it (requirement 7). Mechanics closely mirror `interactive_pager.run()`'s own tty handling (`os.open("/dev/tty", ...)`, `termios.tcgetattr`/`tty.setraw`/`termios.tcsetattr(..., termios.TCSADRAIN, old_settings)` in a `finally`), opened `O_RDWR` (not `run()`'s `O_RDONLY`) since this also needs to write the OSC 11 query to the same fd it reads the reply from. `_read_reply` bounds total wait by a monotonic deadline (not a per-chunk timeout, so a slow trickle of bytes can't extend the wait past ~300ms), stopping early on a BEL/ST terminator or a `_MAX_REPLY_BYTES` cap. `_parse_osc11_reply`/`_normalize_channel` handle both the 2-digit and 4-digit hex-channel reply forms the issue's Motivation section documents (verified against the maintainer's own hand-verified examples: `rgb:213d/2743/33e7` -> `(33, 39, 52)`, luminance ~38.7 -> dark; `rgb:ffff/ffff/ffff` -> `(255, 255, 255)`, luminance 255.0 -> light -- both reproduced exactly by `_parse_osc11_reply`+`_classify_luminance` in `tests/test_theme_detect.py`). Found and fixed one bug during self-review before running the suite: `tty.setraw()` itself calls `termios.tcsetattr` internally and can raise `termios.error`, which is *not* an `OSError` subclass in this Python version (confirmed via `termios.error.__mro__`) -- the inner try's original `except OSError` would have let that propagate straight past the termios-restore `finally`, violating both "never raises" and "always restores termios"; widened to `except (OSError, termios.error)` and added `test_termios_error_from_setraw_falls_back_to_dark_and_restores_termios` to pin it. Tests: `tests/test_theme_detect.py` (parsing/classification as pure-function unit tests, then `detect_terminal_theme()` itself via mocks covering non-tty-skips-query, `OSError` opening `/dev/tty`, `termios.error` from `tcgetattr`, `termios.error` from `tty.setraw`, a valid reply resolving to each of light/dark, a `select`-timeout fallback, a malformed-reply fallback, and an `OSError` during read -- every mocked path asserts `termios.tcsetattr` was called with the original attrs, or, for the two paths before `tcgetattr` ever succeeds, that it was *not* called at all since there's nothing to restore); `tests/test_config.py` (`test_parse_config_accepts_theme_auto`); `tests/test_main.py` (four new end-to-end tests following the VIEWMD-0091/VIEWMD-0043 pattern of invoking `main()` itself rather than only unit-testing with `theme=` handed directly: `--theme auto`/config `theme = auto` reaching `main()`'s resolution and calling `viewmd.theme_detect.detect_terminal_theme` -- mocked at that level, not re-testing the low-level probe -- for both a light and a dark detection result, and a `--theme dark` invocation asserting the detection function is never even called, by making the mock raise `AssertionError` if invoked at all). README.md: `--theme {dark,light,auto}` usage example and prose (mechanism, one-shot-at-startup, fallback conditions), the config-key table row, and an explicit tmux/screen OSC-passthrough-limitation paragraph per requirement 8 SHOULD. Regenerated `completions/*` via `./tools.sh completions` (now lists `dark light auto`). `./run-tests.sh`: 1247 tests pass, ruff clean, pip-audit clean, completions up to date; `issues --check` fails only on a pre-existing gap (`VIEWMD-0104` id-sequence gap, stale README index) confirmed via `git stash` to predate this branch already on `develop`, unrelated to this change. Manual end-to-end verification via this worktree's own `.venv` (this is a non-interactive agent without a real controlling terminal, so this is as far as verification can go here -- see the outstanding item below): `--theme dark` emits `#58a6ff` (unchanged), `--theme light` emits `#0969da` (unchanged), both confirmed byte-identical in shape to the pre-existing VIEWMD-0091 tests' own fixture colors; `--theme auto` piped through `cat` (stdout not a tty) correctly falls back to dark's `#58a6ff` with no hang, exit 0; timed all three (`--theme dark`/`light`/`auto` against the same file, piped) at ~70-90ms each with no measurable difference, confirming `auto` against a non-tty stdout skips the query (and its ~300ms timeout budget) entirely rather than merely resolving fast. **Not independently verified, and not verifiable by a non-interactive agent**: the actual OSC 11 round-trip against a real terminal emulator -- everything above about `--theme auto`'s *detection* correctness is mocked-terminal-response testing, not a real query/reply exchange. Per the issue's own "Acceptance / verification" section (mirroring VIEWMD-0091's `--theme light` contrast check), still outstanding before this can be considered fully done: an actual `--theme auto` run in a real dark-background terminal session and a real light-background terminal session, confirming each resolves to and renders with the corresponding palette end to end -- the same kind of real-terminal check the maintainer already performed once by hand for this exact OSC 11 technique (documented in this issue's own Motivation section) but not yet re-run against the shipped, productionized code path.
- (agent, independent review) Reviewed `viewmd/theme_detect.py`, `viewmd/__main__.py`'s theme-resolution block, `viewmd/config.py`, all three new/changed test files, and README.md, then ran `./run-tests.sh` myself in this worktree (1247 passed, ruff clean, pip-audit clean, `issues --check`'s `VIEWMD-0104` gap/stale-index failure confirmed pre-existing by checking `develop`'s tree directly -- no `VIEWMD-0104` file exists there either, unrelated to this branch). Verified requirement 7 by reading code, not trusting the self-review's numbers: `theme = coalesce(...)` followed by `if theme == "auto": from viewmd.theme_detect import detect_terminal_theme; ...` (`viewmd/__main__.py:150-156`) means the import itself never executes for `dark`/`light`/omitted, confirmed by the existing `test_cli_theme_dark_never_calls_detect_terminal_theme` mocking the function to raise if called. Traced every exit path of `detect_terminal_theme()`: non-tty return, `OSError` on `os.open`, `termios.error` on `tcgetattr` (both pre-raw-mode, correctly skip `tcsetattr` since there's nothing to restore -- confirmed `termios.error.__mro__` does not include `OSError` in this Python, matching the self-review's claim), and the main `try/except (OSError, termios.error)/finally` around `setraw`/`write`/`_read_reply` which always restores via the `finally` before returning; found no path that skips the restore. `_read_reply`'s bounded-deadline loop, `_normalize_channel`'s 2-vs-4-digit scaling, and `_classify_luminance`'s `>127` threshold all check out against the maintainer's own hand-verified examples reproduced in `tests/test_theme_detect.py`, and the termios-restore assertions there are meaningful, not rubber-stamped: they assert `tcsetattr_calls == [(99, termios.TCSADRAIN, original_attrs)]` against the exact sentinel object returned by the mocked `tcgetattr`, so a bug that restored the wrong attrs (not just "called `tcsetattr` at all") would fail them. Two real, non-blocking test-coverage gaps found: (1) the module's own docstring and `_read_reply`'s docstring both explicitly claim the wait is bounded by a total deadline, not per-chunk, "so a slow trickle of bytes can't extend the wait past ~300ms" -- but every mocked-reply test in `tests/test_theme_detect.py` delivers the full reply in one `os.read` call; no test drives `_fake_select`/`_fake_read` through multiple chunks over simulated time, so a regression reintroducing a per-chunk (rather than deadline-based) timeout would pass the suite untouched. (2) `_MAX_REPLY_BYTES` (256) is never exercised by any test -- a garbled/pathological stream that never emits BEL/ST has no test coverage confirming the loop actually terminates at the cap rather than growing `buf` unbounded until `select` itself times out. Also noted, very low severity: `os.close(tty_fd)` is called unguarded in two places (the early return after `tcgetattr` raises `termios.error`, and the main `finally` block) -- if `os.close` itself were ever to raise `OSError` (essentially never happens on a valid, just-used fd in practice), it would propagate out of `detect_terminal_theme` and break the module's own stated "this function itself never raises" contract; not worth blocking on, just noting the guarantee isn't airtight against that theoretical case. No correctness bugs found beyond what the implementer's self-review already caught and fixed (the `termios.error`-from-`setraw` case). README's fallback-conditions and tmux/screen-passthrough prose (lines 87-99) matches the code's actual behavior exactly. Confident in "no additional correctness bugs" specifically because I traced every branch of `detect_terminal_theme`'s control flow by hand against the requirements rather than skimming; the two gaps above are coverage nitpicks about scenarios the implementation likely handles correctly (bounded-deadline `select` loop, byte-cap `break`) but that no test currently pins. Would not block merge on either gap alone, but they'd be quick, worthwhile additions if another round happens for any other reason. Ready to merge as-is from a correctness standpoint.
