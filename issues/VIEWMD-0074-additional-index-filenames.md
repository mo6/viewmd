---
id: VIEWMD-0074
title: Recognize index.md and _index.md as directory-index filenames alongside _Index.md
status: in-progress
area: [cli, render]
effort: low
created: 2026-08-17
updated: 2026-08-17
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-17
commits: []
related: [VIEWMD-0065]
supersedes: []
changelog:
reason:
---

# Recognize index.md and _index.md as directory-index filenames alongside _Index.md

## Summary

VIEWMD-0065 made viewing a directory look for a single, exact-case `_Index.md` note and render
it as that directory's landing page. Extend that lookup to also accept `index.md` and
`_index.md` (both lowercase, per common static-site-generator conventions), still checked with
an exact-case match, still with `_Index.md` a directory can contain only one of at a time in
practice — but define a fixed priority order for the (rare) case more than one is present.

## Motivation / problem

`_Index.md` matches the Obsidian-vault convention VIEWMD-0065 was written against, but two other
per-directory index conventions are extremely common in the Markdown ecosystem viewmd otherwise
targets: `index.md` (plain, used by many static site generators and READMEs-as-index setups) and
`_index.md` (Hugo's section-index convention). A directory using either of those today falls
through to viewmd's directory-listing view instead of rendering the note the directory's author
clearly intended as its landing page.

## Requirements

1. MUST check, in a directory argument, for each of `_Index.md`, `index.md`, and `_index.md`, in
   that fixed order, and render the first one found exactly as VIEWMD-0065 renders `_Index.md`
   today (front matter, wikilinks, Mermaid, etc. unchanged).
2. MUST keep each match case-sensitive and exact-name (via `os.listdir()` membership, not
   `os.path.isfile()` on the joined path), matching VIEWMD-0065 requirement 2's rationale about
   case-insensitive filesystems.
3. MUST apply the same three-name lookup, in the same order, everywhere `INDEX_FILENAME` is
   currently used: `viewmd/__main__.py`'s `_render_path` and `_resolve_document`, and the
   directory-listing exclusion note in `viewmd/render.py` (`render_directory_listing` must still
   not show whichever index file is used as its own listing entry).
4. MUST replace `viewmd.render.INDEX_FILENAME` (currently a single string) with an ordered
   collection of candidate names, keeping it a single named constant call sites import, per
   VIEWMD-0065 requirement 7's intent.
5. MUST NOT change behavior for a directory that has only `_Index.md` today — it still renders,
   unchanged, with no new ordering ambiguity.
6. SHOULD add a short note (docstring or comment) recording the priority rationale (existing
   convention first, then the two lowercase ones) so a future change to the order is a deliberate
   decision, not an accident.

## Non-goals

- No new CLI flag or config option to choose/disable which index name(s) are recognized — a
  fixed, expanded convention list only, same scope boundary VIEWMD-0065 drew for its single name.
- No change to `viewmd/wikilinks.py` directory-target resolution — out of scope per VIEWMD-0065's
  own non-goals, unchanged here.
- No warning/message when a directory contains more than one of the three candidate names — the
  fixed priority order silently picks one, matching how a single-match lookup already behaves.

## Design notes / links

- `viewmd/render.py:30` — `INDEX_FILENAME` constant to become an ordered tuple.
- `viewmd/__main__.py:166-177` (`_render_path`) and `:194-200` (`_resolve_document`) — the two
  call sites performing the `os.listdir()` membership check; both need the same first-match-wins
  loop over the new candidate list.
- `issues/archive/VIEWMD-0065-view-directory-index-or-listing.md` — original single-filename
  design this extends.

## Acceptance / verification

- New tests: a directory with only `index.md` renders it; a directory with only `_index.md`
  renders it; a directory with more than one candidate present renders the one earliest in
  priority order (`_Index.md` > `index.md` > `_index.md`); existing `_Index.md`-only tests in
  `tests/test_main.py` continue passing unchanged.
- `./run-tests.sh` green.
- Manual check: `./viewmd.sh <dir>` against directories using each of the three names.

## Peer review

- **code-review agent** (agent), 2026-08-17: no findings at medium effort. Confirmed
  `_find_index_path` is the single shared implementation used by both `_render_path` and
  `_resolve_document`, priority order is correctly first-match-wins over `INDEX_FILENAMES`, the
  exact-case `os.listdir()` membership check still prevents case-insensitive false positives, test
  coverage for the new filenames and priority order is sound (correctly avoids pairing `_Index.md`
  with `_index.md` in one test, since those collide as the same file on the default
  case-insensitive macOS filesystem), and docs/docstrings are consistent with the new behavior.
  `./run-tests.sh`: pytest/ruff/pip-audit all clean; the only failure is `issues --check` flagging
  a pre-existing id-sequence gap around VIEWMD-0072 from unrelated concurrent work, not this diff.
