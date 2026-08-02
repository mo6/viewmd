---
id: VIEWMD-0003
title: Cap render width to 100 columns by default; --width overrides or goes full-terminal
status: implemented
area: [cli, render]
effort: low
created: 2026-08-02
updated: 2026-08-02
accepted_by: George Moses
accepted_at: 2026-08-02
commits: [0121d6c]
related: []
supersedes: []
changelog: "[0.2.0]"
reason:
---

# Cap render width to 100 columns by default; --width overrides or goes full-terminal

## Summary

Rendered output currently always fills the detected terminal width, however wide that is. On a
wide terminal, long-line prose and wide tables become hard to read. Default rendering should cap
at 100 columns (a common prose line-length standard), narrower if the terminal itself is
narrower. `--width` becomes the one flag to override that: an explicit column count, or the
literal `full` to use the full detected terminal width regardless of the 100-column default.

## Motivation / problem

Reported by the maintainer: wants output line length maximized at a 100-character standard by
default, with an escape hatch to pick a specific width or the full terminal width.

## Requirements

1. MUST default the render width to `min(100, detected terminal width)` when `--width` is not
   given.
2. MUST support `--width N` (a positive integer) to render at exactly `N` columns, regardless of
   the 100-column default or the detected terminal width.
3. MUST support `--width full` to render at the full detected terminal width, uncapped by the
   100-column default.
4. MUST reject a non-positive or non-integer `--width` value (other than the literal `full`) with
   a clean argparse usage error, not a traceback.
5. SHOULD keep `--width`'s existing behavior of being independent of `--color`/`--no-pager` (no
   interaction between them).

## Non-goals

- Making 100 itself configurable via an env var or config file; a constant is enough for a
  single-user tool, changeable later if it's ever wanted.
- Per-element width overrides (e.g. tables wider than prose); Rich renders the whole document at
  one width, which this issue keeps.

## Design notes / links

Extends the existing `--width` flag from VIEWMD-0001 rather than adding a second flag, per the
maintainer's ask for "an optional argument" (singular). The resolution logic (`--width` unset vs.
`N` vs. `full`) is implemented as its own testable function in `viewmd/__main__.py`, not inlined
in `main()`, so it can be unit-tested without going through argparse or a real terminal.

## Acceptance / verification

- `./run-tests.sh` green; new unit tests cover the width-resolution function directly: no flag
  (capped at 100 or narrower), `--width 60`, `--width full`, `--width 0` / `--width -5` /
  `--width banana` all rejected cleanly.
- Manual: `COLUMNS=200 ./viewmd.sh README.md --no-pager --width full | head -1 | wc -c` shows a
  line at the full 200-column width; the same command without `--width full` shows a line capped
  at 100.

## Peer review

- **Claude (Sonnet 5)** (agent), 2026-08-02: PASS. `./run-tests.sh` green (24 tests, ruff clean,
  issues index current). Verified manually with `COLUMNS=200`: default output capped at exactly
  100 columns; `--width full` renders at the full 200; `--width 40` renders at exactly 40;
  `COLUMNS=60` (narrower than 100) renders at 60, confirming the `min()` default; `--width 0` and
  `--width banana` both rejected with a clean argparse usage error (exit 2), no traceback.
