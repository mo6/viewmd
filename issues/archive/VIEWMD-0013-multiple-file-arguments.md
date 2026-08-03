---
id: VIEWMD-0013
title: Accept multiple Markdown files as arguments
status: implemented
area: [cli, render, pager]
effort: medium
created: 2026-08-03
updated: 2026-08-03
accepted_by: George Moses
accepted_at: 2026-08-03
commits: [783fc6e]
related: []
supersedes: []
changelog: "[1.2.0]"
reason:
---

# Accept multiple Markdown files as arguments

## Summary

`viewmd` currently accepts at most one `path` argument (or stdin). This extends it to accept one or more paths, so shell globbing like `viewmd *.md` renders every matched file, one after another, in a single pager session.

## Motivation / problem

A user with a directory of Markdown files today has to invoke `viewmd` once per file. Tools like `bat` and `less` accept multiple files directly and let the shell do the globbing (`bat *.md`); `viewmd` should behave the same way instead of erroring out on the second positional argument.

## Requirements

1. MUST change the `path` positional argument to accept one or more values (`nargs="+"`), defaulting to `["-"]` when omitted, preserving today's stdin behavior for the no-argument case.
2. MUST reject passing `-` (stdin) together with any other path in the same invocation, with a `viewmd: cannot mix stdin ('-') with file arguments` message on stderr and exit code 1 -- stdin has no meaningful position among multiple named files.
3. MUST render each file's content in the order given on the command line, each still going through the existing front-matter/width/color handling unchanged.
4. MUST separate consecutive files with a visible divider (reusing the existing front-matter divider style) and, before each file's content, a heading line showing that file's path, so the combined output makes clear where one file ends and the next begins.
5. MUST concatenate all rendered files into a single pager invocation (one `less` session for the whole batch), not one pager launch per file.
6. MUST report a per-file read error (missing file, bad permissions, invalid UTF-8) on stderr in the same format as today (`viewmd: cannot read <path>: ...`) and continue rendering the remaining files, then exit 1 if any file failed and 0 if all succeeded.
7. SHOULD keep single-file invocation output byte-for-byte identical to today's (no added heading/divider when only one path is given), so existing scripts/tests relying on single-file output are unaffected.

## Non-goals

- No new flag to control the separator/heading format; the default styling is fixed for this issue.
- No recursive directory expansion (`viewmd docs/`) -- only the paths/globs the shell itself expands are handled.
- No change to `--no-pager`, `--color`, `--width`, or `--full-front-matter` semantics; each still applies uniformly across all files in the batch.

## Design notes / links

None; the divider styling should reuse whatever `render.py` already uses between front matter and body (see VIEWMD-0004) rather than inventing a second style.

## Acceptance / verification

- `./run-tests.sh` green, including new cases for: multiple valid files renders all in order with headings/dividers and one pager call; single file matches today's byte-for-byte output; mixing `-` with a real path errors with exit 1 and the specified message; one bad file among several still renders the good ones, prints the per-file error, and exits 1.
- Manual check: `viewmd *.md` in a directory with several Markdown files renders all of them in one `less` session, in filename-glob order.

## Peer review

- **Claude** (agent), 2026-08-03: implemented; `./run-tests.sh` green (69 pytest, ruff, pip-audit, issues gate), plus manual checks of multi-file rendering, single-file byte-for-byte output, `-`-mixing rejection, `*.md` glob expansion, and a missing file mid-batch. No findings.
- **George Moses** (maintainer), 2026-08-03: accepted, works fine; asked for the README to note that multiple files are concatenated into one pager session rather than viewed per-file like `less`'s `:n`/`:p` -- added to README.md.
