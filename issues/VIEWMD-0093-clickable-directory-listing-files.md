---
id: VIEWMD-0093
title: Make .md filenames clickable in the directory listing pager
status: in-progress
area: [pager, render]
effort: medium
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: []
related: [VIEWMD-0081]
supersedes: []
changelog:
reason:
---

# Make .md filenames clickable in the directory listing pager

## Summary

VIEWMD-0081 made subdirectory rows in the interactive directory-listing view clickable, navigating into that subdirectory's own listing, but explicitly left `.md` file rows out of scope. This issue closes that gap: clicking (or Enter-ing) a `.md` file row opens that file the same way clicking a wikilink/Markdown link opens a file elsewhere in the pager.

## Motivation / problem

`render_directory_listing()` (`viewmd/render.py`) still adds `.md` file rows as plain `escape(name)` text (line 687) with no `Style(link=...)`, unlike the subdirectory rows immediately above it (line 681-682) which got exactly this treatment under VIEWMD-0081. A reader browsing a directory listing can now descend into subdirectories by clicking, but hits a dead end on the actual files they're browsing for — the one thing a directory listing exists to let you open. It's the same "looks clickable, does nothing" gap VIEWMD-0081's motivation section described for subdirectories, now on the file side.

## Requirements

1. MUST render each `.md` file row in `render_directory_listing()` with a clickable target (`Style(link=...)`, OSC8 hyperlink where color/link support allows) pointing at that file's path, matching how subdirectory rows are already styled.
2. MUST make clicking (and pressing Enter/Return on the selected row, if the listing supports row selection) a file row open that file in the pager, replacing the current view — reusing `_resolve_link_target()` (`viewmd/interactive_pager.py`), which already only accepts `.md` targets, and the existing `doc_dir`/`open_path` wiring `run_directory_listing()` already carries for subdirectory navigation (VIEWMD-0081).
3. MUST push the directory listing onto the navigation stack (the same `nav_stack`/`B` convention VIEWMD-0081 wired for subdirectory navigation) so `B` returns to the listing after opening a file from it.
4. MUST NOT change subdirectory-row behavior (VIEWMD-0081) at all.
5. MUST NOT change the non-interactive rendering path (`render_directory_listing`'s plain output, `--no-pager`, piped output) — this is an interactive-pager-only navigation affordance, same restriction VIEWMD-0081 applied to itself.
6. SHOULD keep the existing file/directory visual distinction (trailing `/`, `dir`/`file` type column) unchanged — only the click affordance is new, not the row's appearance otherwise.

## Non-goals

- Any change to the multi-file pager (`run_multi_file`) or single-document pager (`run`).
- Adding new keyboard shortcuts beyond what's already established (Enter/click).
- Making non-`.md` files (images, other text files) clickable — out of scope, matches `_resolve_link_target`'s existing `.md`-only restriction.

## Design notes / links

Directly mirrors [VIEWMD-0081](archive/VIEWMD-0081-clickable-directory-listing-subdirs.md)'s implementation for subdirectories — same file (`render.py`'s `render_directory_listing`), same click-resolution machinery (`interactive_pager.py`'s `_run()` click handler, `_resolve_link_target`), just the file-row branch instead of the directory-row branch. `_resolve_link_target` already rejects anything not ending in `.md` (per VIEWMD-0081's design notes), so it should need no change — only the row now needs to carry a target for it to resolve.

## Acceptance / verification

New/updated tests wherever `run_directory_listing`/`render_directory_listing` are already tested (VIEWMD-0081's own test additions are the template): a `.md` file row carries a link target; clicking it opens that file in the pager; `B` returns to the directory listing afterward; subdirectory-row behavior is unchanged. Manual verification: `./viewmd.sh` a directory with both files and subdirectories, confirm clicking a file opens it and `B` returns to the listing, in a real terminal. `./run-tests.sh` green.

## Peer review

