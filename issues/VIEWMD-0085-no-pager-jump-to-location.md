---
id: VIEWMD-0085
title: Add a non-interactive way to open a document at a heading or search match
status: proposed
area: [cli, render, pager]
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

# Add a non-interactive way to open a document at a heading or search match

## Summary

Add a `--heading NAME` flag that, when given, renders/pages the document starting from the first heading whose text matches `NAME` (case-insensitive substring match) instead of the top of the file — the scripting/`--no-pager` equivalent of typing `t` then picking a table-of-contents entry, or of `less +/pattern`.

## Motivation / problem

The interactive pager already has heading navigation (`t` for the ToC popup, `n`/`p` for next/previous heading) and `/` search, but all of it requires an interactive session. There is no way to script "open this doc at the section I care about" — e.g. `viewmd CHANGELOG.md --heading '1.40.0'` to jump straight to one release's notes — short of piping through `grep`/`sed` and losing viewmd's rendering.

## Requirements

1. MUST add `--heading NAME` (mutually exclusive with nothing existing; independent of `--no-pager`).
2. MUST match against the same heading text `heading_outline()` (`viewmd/render.py`) already extracts, case-insensitive substring match, first match wins in document order.
3. MUST, in `--no-pager` mode, print output starting at the matched heading's line through the end of the render (front matter/ToC/preceding sections omitted).
4. MUST, in interactive-pager mode, open with the viewport already scrolled to that heading (equivalent to what pressing Enter on that ToC entry does today).
5. MUST print a `viewmd: no heading matching <NAME>` error to stderr and exit non-zero if nothing matches, rather than silently falling back to the top.
6. MUST NOT apply to multi-file or bare-directory-listing invocations, which have no single heading outline (same restriction the ToC popup and `n`/`p` already have — see README's "single-document-only" footnote).

## Non-goals

- No regex or fuzzy matching — plain case-insensitive substring, matching how `/` search already behaves.
- No line-number equivalent (`less +42`) — headings are the addressable unit, since raw source line numbers aren't meaningful once Markdown is re-rendered to ANSI at a given width.

## Design notes / links

Reuses `viewmd/render.py`'s existing `heading_outline()`/`HeadingOutline` and the interactive pager's existing "jump to heading" plumbing (used today by ToC-popup Enter and `n`/`p`) rather than adding a new mechanism.

## Acceptance / verification

New tests: `--no-pager --heading` prints from the matched heading onward, byte-for-byte matching a manually-sliced expectation; unmatched name exits 1 with the stderr message; multi-file/directory-listing invocations reject `--heading` with a clear error. `./run-tests.sh` green.

## Peer review

