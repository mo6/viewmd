---
id: VIEWMD-0103
title: Document that the interactive pager is Unix-only, and why it does not use curses
status: in-progress
area: [docs]
effort: low
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: []
related: [VIEWMD-0007, VIEWMD-0072]
supersedes: []
changelog:
reason:
---

# Document that the interactive pager is Unix-only, and why it does not use curses

## Summary

README.md's Interactive pager section never says the pager is Unix-only, so a Windows reader has no warning that `termios` / `/dev/tty` / `SIGWINCH` will fail at import or open. `docs/PLAN.md`'s pager section names the "no curses, no prompt_toolkit" choice but does not record *why*, so a later issue proposing a curses rewrite has nothing concrete to argue against.

## Motivation / problem

The interactive pager (`viewmd/interactive_pager.py`) is a hand-rolled TUI: `termios`/`tty` cbreak, `/dev/tty` for input, DECSET 1049 alternate screen, xterm mouse (1000/1003/1006), and a full-viewport home-and-reprint `draw()`. Native Windows CPython has none of `termios`, `/dev/tty`, or `SIGWINCH`. `PLAN.md` already states the architecture uses stdlib + Rich rather than curses, which was the VIEWMD-0007 POC's whole point, but the durable reasons (pre-rendered Rich ANSI including OSC-8 and 256-color SGR, xterm any-motion mouse, curses still not a Windows free lunch) are only in chat, not in the *why* doc that exists so those calls are not re-derived from scratch.

## Requirements

1. MUST add a sentence to README.md's Interactive pager section stating that the pager is Unix-only (macOS, Linux, BSD, WSL) and is not supported on native Windows.
2. MUST add a short write-up to `docs/PLAN.md`'s Interactive pager section explaining why the pager does not use curses (or prompt_toolkit): the content is already Rich ANSI, curses wants a cell grid and color pairs that would drop OSC-8 / fight 256-color / fight xterm mouse, and a curses port would not by itself make native Windows work.

## Non-goals

- No code changes, no Windows port, no curses experiment, no `--no-pager` Windows-support claim.
- No new `docs/` file; the curses rationale stays in `PLAN.md`.
- No performance-benchmark claims in either file.

## Design notes / links

Pager architecture already in [docs/PLAN.md](../docs/PLAN.md) ("Interactive pager: own the terminal directly"). Implementation in `viewmd/interactive_pager.py` (module docstring and `_ENTER_SCREEN` / `draw()` comments).

## Acceptance / verification

Read-through: README names native Windows as unsupported; PLAN.md's curses paragraph is a *why*, not a how-`draw()`-works walkthrough. `./run-tests.sh` green (`issues --check` picks up the new file).

## Peer review

- **implementing agent** (agent), 2026-08-19: README states Unix-only + native Windows unsupported with the actual `termios`/`/dev/tty` reason; PLAN.md adds a dedicated curses paragraph (Rich ANSI / OSC-8 / xterm mouse vs cell grid, and curses wouldn't buy Windows). `./run-tests.sh` green. Directly on `develop` per the maintainer's "quick implementation" after the worktree question.
- **George Moses** (maintainer), 2026-08-19: "commit and close" — accepted the README Windows note and PLAN.md curses rationale; approved landing on `develop` without a worktree.