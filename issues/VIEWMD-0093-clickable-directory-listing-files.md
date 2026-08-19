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

- **implementing agent** (agent), 2026-08-19: implemented per the issue -- `.md` file rows in `render_directory_listing()` now get a `Text` cell with `Style(link=urllib.parse.quote(name))` (a plain relative-path href, not the `_DIR_ANCHOR_SCHEME`-tagged form subdirectory rows use), so the click handler's existing `else` branch resolves it via `_resolve_link_target` instead of `_resolve_dir_target`. `run_directory_listing()`'s `open_path` now dispatches on `os.path.isdir(path)`: the directory branch is untouched from VIEWMD-0081, the new file branch reads the `.md` file and returns the same `(loader, display_name, doc_dir)` triple `run()`'s own `open_path` returns for a clicked in-document link (defaulting `full_front_matter=False`, `toc=True` since `run_directory_listing()` has no way to know the CLI's actual flag values -- matches `run()`'s own defaults, and this path is only reached when a directory listing was opened without them anyway). Nav-stack push/`B` back-navigation needed no change -- it was already shared, unconditional machinery in `_run()`'s click branch, not dir-specific. Tests added: `tests/test_render.py` (`.md` row carries a plain-path href, distinct from a `viewmd-dir:` one; no OSC8 link in `color=False` output) and `tests/test_interactive_pager.py` (`_link_at` decodes a file row's href with a space in the filename; `_resolve_link_target` resolves it; `run_directory_listing`'s `open_path` opens a real `.md` file with correct display name/doc_dir/heading count; `open_path` returns `None` for a target that no longer exists, mirroring `run()`'s own race handling). Also tightened a stale comment/assertion in VIEWMD-0081's own `test_render_directory_listing_links_subdirectory_rows` that had claimed ".md file rows carry no href yet" -- the assertion itself (`"viewmd-dir:a.md" not in colored`) was still true (file hrefs never use that scheme) so no behavior changed, only the comment. `./run-tests.sh` green (1089 passed, ruff/pip-audit/issues clean). Manually verified via direct `render_directory_listing()` calls that a file row now carries a plain-path OSC8 link alongside the subdirectory's `viewmd-dir:`-scheme one, and traced (rather than interactively drove) the click-dispatch/`open_path`/nav-stack code path end to end -- I did not drive a real tty/mouse-click session (`./viewmd.sh` in an actual terminal) the way the issue's own "Manual verification" line asks for, so that step is still open for the maintainer or a follow-up review to confirm.
- **George Moses** (maintainer), 2026-08-19: tested manually in a real terminal, confirmed working. Accepted to land.
