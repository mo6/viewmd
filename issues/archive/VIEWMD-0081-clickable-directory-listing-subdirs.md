---
id: VIEWMD-0081
title: Make subdirectories clickable in the directory listing pager
status: implemented
area: [pager, render]
effort: medium
created: 2026-08-18
updated: 2026-08-18
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-18
commits: [8f85df3]
related: [VIEWMD-0076]
supersedes: []
changelog: "[1.40.0]"
reason:
---

# Make subdirectories clickable in the directory listing pager

## Summary

In the interactive directory listing view, `.md` file rows are visually distinguished from
subdirectory rows, but neither is actually clickable today, and there is no way to navigate into
a subdirectory at all. This issue makes subdirectory rows clickable (and Enter-able), navigating
the pager into that subdirectory's own listing, matching the "click a link to open it" affordance
the user already expects from the rest of the pager.

## Motivation / problem

`render_directory_listing()` (`viewmd/render.py:645-679`) lists both `.md` files and
subdirectories as plain table rows -- neither carries an OSC8 hyperlink, and
`run_directory_listing()` (`viewmd/interactive_pager.py:986-1005`) calls the shared `_run()`
engine without `doc_dir`/`open_path`, so `_run()`'s click-to-follow handler
(`interactive_pager.py:1397`) is a no-op for every row in this view. `run()`'s own docstring
(`interactive_pager.py:947-951`) already calls this out as a known gap. Practically, a user
browsing a directory listing has no way to descend into a subdirectory except backing out to the
shell and re-invoking viewmd with a new path -- every other clickable-looking thing in viewmd
(links, ToC entries, VIEWMD-0076/0077) responds to a click, so a subdirectory row that looks like
a row in a file browser but does nothing is a surprising dead end.

## Requirements

1. MUST render each subdirectory row in `render_directory_listing()` with a clickable target
   (OSC8 hyperlink where color/link support allows, consistent with how `.md` file rows will
   also need a target per requirement 3) pointing at that subdirectory's path.
2. MUST make clicking (and pressing Enter/Return on the selected row, if the listing supports
   row selection) a subdirectory row navigate the pager to a new directory listing rooted at that
   subdirectory, replacing the current view -- i.e. `run_directory_listing()` must gain the
   equivalent of `doc_dir`/`open_path` wiring that `run()` already has for single files, but
   resolving to "open a new directory listing" rather than "open a file".
3. MUST provide a way back up to the parent directory from a subdirectory's listing (e.g. a
   `..` row at the top, or the existing `B` back-key convention used elsewhere in the pager) so
   navigation is not one-way.
4. MUST NOT change how `.md` file rows behave if they are already independently clickable by the
   time this ships (see VIEWMD-0076 for click-to-follow); if `.md` file rows are still non-
   clickable in the directory listing when this is implemented, wiring their click-to-open is
   out of scope for this issue -- file this issue's scope as subdirectories only.
5. MUST NOT change the non-interactive rendering path (`render_directory_listing`'s plain output,
   `--no-pager`, piped output) -- this is an interactive-pager-only navigation affordance.
6. SHOULD keep the existing distinction between file rows and directory rows (the trailing `/`,
   the `dir`/`file` type column) so a clicked subdirectory is still visually identifiable as a
   directory before it's clicked.

## Non-goals

- Wiring click-to-open for `.md` file rows in the directory listing, if not already done by the
  time this lands (see requirement 4).
- Any change to the multi-file pager (`run_multi_file`) or single-document pager (`run`).
- Adding new keyboard shortcuts beyond what parent-navigation (requirement 3) requires.

## Design notes / links

`render_directory_listing()` (`viewmd/render.py:645-679`) builds the Rich `Table`; subdirectory
rows are added at `render.py:668` (`table.add_row(escape(name) + "/", "dir", "", "")`) with no
`Style(link=...)` applied -- compare to the ToC's `_TOC_ANCHOR_SCHEME` use of `Style(link=...)`
at `render.py:465` for the pattern to follow, adapted to point at a directory path instead of a
same-document anchor. `run_directory_listing()` (`interactive_pager.py:986-1005`) currently omits
`doc_dir`/`open_path` when calling `_run()`; `_run()`'s click handler
(`interactive_pager.py:1397`, `elif href is not None and doc_dir is not None and open_path is not
None:`) and `_resolve_link_target()` (`interactive_pager.py:454-485`) are the existing
machinery for resolving a clicked href to a target and opening it -- `_resolve_link_target`
currently rejects anything that doesn't end in `.md` (line 483), so it will need a directory-
aware branch (or a sibling resolver) rather than reuse as-is.

## Acceptance / verification

- New unit/integration tests (wherever `run_directory_listing`/`render_directory_listing` are
  already tested) covering: a subdirectory row carries a link target; clicking it opens a new
  listing for that subdirectory; a `..`/back affordance returns to the parent listing; `.md` file
  row behavior is unchanged by this change.
- Manual verification: `./viewmd.sh` a directory tree with nested subdirectories, confirm
  clicking a subdirectory row descends into it and the parent-navigation affordance returns back
  up, in a real terminal.
- `./run-tests.sh` green.

## Peer review

- **code-review agent** (agent), 2026-08-18: one finding, a stale comment on the `'B'` back-key
  branch (`viewmd/interactive_pager.py`) still claiming `run_directory_listing()` never pushes
  onto `nav_stack` -- no longer true once a subdirectory-row click pushes there. Fixed inline.
