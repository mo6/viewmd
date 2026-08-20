---
id: VIEWMD-0089
title: Show file size in directory listings and add an optional recursive depth
status: in-progress
area: [render, cli]
effort: medium
created: 2026-08-19
updated: 2026-08-20
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-20
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Show file size in directory listings and add an optional recursive depth

## Summary

Two related, independently-shippable improvements to the bare-directory-listing view (`render_directory_listing` in `viewmd/render.py`, VIEWMD-0065): add a file-size column alongside the existing name/last-modified columns, and add an opt-in `--depth N` flag to descend into subdirectories rather than the current fixed one-level listing.

## Motivation / problem

Today's directory listing (used when a directory `path` argument has no `_Index.md`/`index.md`/`_index.md`) shows a file's title and last-modified time, one level deep, no recursion — useful as a landing page but limited as an actual browsing tool: there's no way to see how large a file is before opening it, or to get an overview of a small vault's structure without opening each subdirectory in turn.

## Requirements

1. MUST add a size column to the existing directory-listing table, formatted human-readably (e.g. `1.2K`, `340B`), for Markdown files; subdirectory rows show an entry count or stay blank (decide one, document it) rather than a byte size.
2. MUST add `--depth N` (default: `1`, today's existing behavior) that, when `N > 1`, lists entries from subdirectories up to `N` levels deep, each row indented to show its depth, still subdirectories-first-then-files, alphabetical within each directory as today.
3. MUST NOT change output for the default (`--depth` omitted or `1`) case beyond the added size column — existing depth-1 tests should only need updating for the new column, not restructuring.
4. SHOULD cap or warn on unreasonably large `--depth` values traversing very large trees, consistent with the tool's terminal-rendering purpose rather than becoming a general-purpose `find`.
5. MUST leave the "directory with an index file renders that file instead" behavior (VIEWMD-0065/0074) completely untouched — this issue only affects the bare-listing fallback path.

## Non-goals

- No `--depth` support for anything other than the bare directory-listing view (single documents and multi-file concatenation are unaffected).
- No sorting options beyond the existing subdirectories-first-then-alphabetical order.

## Design notes / links

Builds on `viewmd/render.py`'s existing `render_directory_listing`; `--depth` follows the same `coalesce(CLI, config, default)` pattern as `--width`/`--toc` in `viewmd/__main__.py` if it should also be config-settable (decide during implementation).

## Acceptance / verification

New/updated tests in `tests/test_render.py` covering: size column formatting for a few byte-size boundaries; `--depth 2`/`--depth 3` output against a fixture directory tree; `--depth 1`/omitted matches pre-existing fixtures plus the new column. `./run-tests.sh` green.

## Peer review

