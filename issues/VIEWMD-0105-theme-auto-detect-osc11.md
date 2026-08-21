---
id: VIEWMD-0105
title: Add --theme auto, detecting light/dark via an OSC 11 background-color query
status: in-progress
area: [render, config, cli]
effort: medium
created: 2026-08-21
updated: 2026-08-21
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-21
commits: []
related: [VIEWMD-0091]
supersedes: []
changelog:
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
