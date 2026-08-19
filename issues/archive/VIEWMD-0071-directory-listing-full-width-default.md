---
id: VIEWMD-0071
title: Directory listings default to full terminal width
status: implemented
area: [cli, render]
effort: low
created: 2026-08-17
updated: 2026-08-17
accepted_by: George Moses
accepted_at: 2026-08-17
commits: [0a09dad]
related: [VIEWMD-0003]
supersedes: []
changelog: "[1.32.0]"
reason:
---

# Directory listings default to full terminal width

## Summary

When no `--width` is given, a directory listing (`render_directory_listing`) should render at the
full detected terminal width, instead of the ordinary `min(DEFAULT_MAX_WIDTH, terminal_width)`
prose cap used for Markdown documents.

## Motivation / problem

The directory listing is a table of entries (name, heading/title, size, etc.), not prose. Capping
it to `DEFAULT_MAX_WIDTH` (100 columns, VIEWMD-0003) truncates or wraps columns unnecessarily on
wide terminals, when the terminal has the space to show the whole table. Markdown documents
benefit from a readable prose width cap; a directory listing does not.

## Requirements

1. MUST: when `viewmd <dir>` (or a bare directory argument in a multi-path invocation) is rendered
   with no `--width` flag and no `width` set in the config file, the directory listing renders at
   the full detected terminal width (`shutil.get_terminal_size().columns`), not
   `min(DEFAULT_MAX_WIDTH, terminal_width)`.
2. MUST NOT change this default-width behavior for rendering an actual Markdown document
   (a plain file, stdin, or a directory's `INDEX_FILENAME` note) -- those keep the existing
   `min(DEFAULT_MAX_WIDTH, terminal_width)` default.
3. MUST: an explicit `--width <n>`, `--width full`, or a config-file `width` setting still applies
   to a directory listing exactly as it does today -- this issue only changes the *default* used
   when none of those is given.

## Non-goals

- Not changing how `--width full` or an explicit numeric `--width` behaves for anything.
- Not changing the width behavior for rendered Markdown documents.

## Design notes / links

Builds on the `--width`/`DEFAULT_MAX_WIDTH` design in VIEWMD-0003. The resolution point is
`_resolve_width` in `viewmd/__main__.py`, currently width-source-agnostic; this issue makes width
resolution aware of whether the target is a directory listing or a document.

## Acceptance / verification

- New/updated unit test(s) in `tests/` covering `_resolve_width` (or its caller) for the
  directory-listing case: no `--width` given -> full terminal width used, regardless of
  `DEFAULT_MAX_WIDTH`.
- Existing width-related tests continue to pass unchanged for the document-rendering path.
- `./run-tests.sh` green.
- Manual check: `viewmd some-wide-dir/` in a terminal wider than 100 columns shows the listing
  table using the full width; `viewmd some-wide-dir/ --width 60` still renders at 60 columns.

## Peer review

- **Claude Sonnet 5** (agent), 2026-08-17: implemented and self-reviewed. `_resolve_width` gained
  an optional `default_max_width` (defaults to `DEFAULT_MAX_WIDTH`, unchanged for documents);
  `main()` now computes a second `directory_width` using `default_max_width=terminal_width`, used
  only for the bare-directory-listing branch in both the single-path and multi-path (`_render_path`)
  code paths. Verified manually: `--width` explicit and config-file values still override; the
  full terminal width is used only when neither is given. Added
  `test_directory_listing_defaults_to_full_terminal_width` and
  `test_directory_listing_explicit_width_overrides_the_full_default` to `tests/test_main.py`.
  `./run-tests.sh` green (1020 passed, ruff clean, pip-audit clean, issues index regenerated).
- **George Moses** (maintainer), 2026-08-17: signed off; commit and close out.
