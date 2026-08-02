---
id: VIEWMD-0001
title: Render a Markdown file to ANSI in the terminal, auto-paged into less
status: in-progress
area: [render, pager, cli]
effort: medium
created: 2026-08-02
updated: 2026-08-02
accepted_by: gmo6nl@gmail.com
accepted_at: 2026-08-02
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Render a Markdown file to ANSI in the terminal, auto-paged into less

## Summary

`viewmd` renders a `.md` file's headers, emphasis, lists, blockquotes, tables, fenced code
blocks (with syntax highlighting, and with exact spacing preserved for undecorated ASCII art),
and horizontal rules to ANSI-colored terminal output, and pages that output into `less` the way
`git log`/`bat` do when stdout is a terminal.

## Motivation / problem

Reading a `.md` file today means either opening the raw source (no formatting) or a browser (no
pipe into `less`, no terminal workflow). There's no command that renders Markdown's structure —
especially tables and code blocks — directly to a terminal with a familiar `less`-style paging
experience.

## Requirements

1. MUST render, at minimum: headers, bold/italic/strikethrough, ordered and unordered lists,
   blockquotes, GFM tables, fenced code blocks (with Pygments syntax highlighting when a language
   tag is present), horizontal rules, and links.
2. MUST preserve a fenced code block's exact internal spacing/alignment (so hand-drawn ASCII art
   in a code fence renders unmodified).
3. MUST accept a file path as a positional argument, and MUST read from stdin when the path is
   `-` or omitted with stdin not a tty (so `cat notes.md | viewmd` works).
4. MUST auto-page into `$PAGER` (default `less -R -F -X`) when `sys.stdout.isatty()` is true, and
   MUST NOT page (print plain to stdout) otherwise.
5. MUST support `--no-pager` to force plain stdout output even in a terminal.
6. MUST support `--color {auto,always,never}` (default `auto`, following `NO_COLOR` env var and
   tty detection); `always` MUST emit ANSI color codes even when stdout is not a tty.
7. MUST support `--width N` to override terminal width detection.
8. MUST print `viewmd: <message>` to stderr and exit 1 on a missing file or a decode error,
   never a raw traceback.
9. SHOULD exit quietly (no traceback) if the user quits the pager before it finishes reading
   (`BrokenPipeError`).

## Non-goals

- Image-to-ASCII conversion of `![]()` references (see [docs/PLAN.md](../docs/PLAN.md)).
- HTML rendering of embedded raw HTML.
- Non-GFM Markdown extensions (footnotes, definition lists, custom containers).

## Design notes / links

Rendering engine choice (Rich's `Markdown`), the color/width-forcing design, and the pager
auto-detection design are all covered in [docs/PLAN.md](../docs/PLAN.md); this issue states the
resulting requirements, not the reasoning.

## Acceptance / verification

- `./run-tests.sh` green: `tests/test_render.py` covers requirements 1-2 (fixture `.md` strings
  for headers/tables/code blocks/ASCII-art spacing/colored-vs-plain output);
  `tests/test_pager.py` covers requirements 4-5 and 9 (the `should_page` truth table, `$PAGER`
  override).
- Manual: `./viewmd.sh README.md` in a real terminal pages into `less`, colored, `q` exits
  cleanly (requirement 4).
- Manual: `./viewmd.sh README.md --no-pager | cat` prints plain uncolored text, no pager
  (requirements 5-6).
- Manual: `./viewmd.sh README.md --color=always --no-pager | cat -v` shows ANSI escapes even
  piped (requirement 6).
- Manual: `cat README.md | ./viewmd.sh` renders from stdin (requirement 3).
- Manual: a `.md` fixture with a hand-drawn ASCII art code block renders with alignment intact,
  eyeballed in a real terminal (requirement 2).

## Peer review

- **Claude (Sonnet 5)** (agent), 2026-08-02: PASS. `./run-tests.sh` green (14 tests, ruff clean,
  issues index current). Verified manually: colored/plain rendering, GFM table cell content,
  ASCII-art code-fence spacing preserved, `--no-pager`, `--color=always` overriding a piped
  (non-tty) stdout, `NO_COLOR`, stdin input, missing-file error (exit 1, no traceback),
  `--version`. Not independently verifiable in this sandbox: real interactive-terminal
  auto-paging into `less` (the shell here never presents a true tty to the child process) —
  `should_page()`'s tty branch is covered by a mocked-isatty unit test but not a live pager
  invocation; flagged to the maintainer to confirm with `./viewmd.sh README.md` in a real
  terminal before considering this fully verified.
