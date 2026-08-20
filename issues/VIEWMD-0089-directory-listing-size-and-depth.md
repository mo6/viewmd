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

- (implementing agent, self-review only -- NOT the independent review AGENTS.md's Definition of Done requires before merge, since it's the same agent that wrote the diff; a genuinely independent pass is still needed): Read the full diff end to end against the five requirements and both non-goals before this line was written, then re-read it a second time deliberately looking for bugs rather than confirming intent. Found and fixed two real issues in that second pass: (1) `_entry_count()` (new, shows a subdirectory row's item count) called `os.listdir()` on every subdirectory to compute that count, including at the *default* `depth=1` -- meaning a permission-denied subdirectory would now crash the entire listing even though depth-1 never used to need read access to a subdirectory's own contents, violating requirement 3 ("MUST NOT change output for the default case beyond the added size column") in spirit by adding a new crash mode to the unchanged default path; fixed by catching `OSError` there and showing a blank size for that row instead, with a regression test (`test_render_directory_listing_unreadable_subdirectory_shows_blank_size_not_a_crash`). (2) `--depth`'s cap-warning was originally resolved unconditionally near the top of `main()`, before branching on whether the `path` argument is even a bare directory listing at all -- so `viewmd somefile.md --depth 999` printed the "`--depth 999` capped to 10" warning to stderr even though `--depth` has no effect there at all (violates the Non-goals: "single documents and multi-file concatenation are unaffected" -- a spurious warning is itself an effect); fixed by moving `_resolve_depth()`'s call into the directory-listing branch only, with a regression test asserting empty stderr for that case. Verified the CLI end-to-end by hand (not just tests, per AGENTS.md's VIEWMD-0043 lesson): built a real nested directory tree and ran `--depth` omitted/2/3/999 against it, confirming indentation, subdirectories-first ordering at each level, size-column formatting, and the capping warning all behave as intended. Two scoping decisions the issue left open, both documented in code comments: the size column sits between Title and Modified (not appended at the end); a subdirectory row's size column shows its own immediate-child entry count (`"N items"`/`"1 item"`), computed the same way at every depth level regardless of how deep `--depth` actually descends; only top-level (`level == 0`) rows stay click-navigable in the interactive pager -- a deeper row renders as plain (still-escaped) text rather than widening `_resolve_dir_target`'s documented "always an immediate child" contract, so navigating to a level-2+ entry requires clicking into its parent first (documented in README.md). `--depth` was made config-file-settable (`depth = N`, mirroring `width`/`toc`), capped at `MAX_DEPTH = 10` (chosen value, not specified by the issue) with a stderr warning rather than a hard error when exceeded, and deliberately given no effect on multi-file concatenation, matching the issue's own Non-goals text literally.
