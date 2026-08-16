---
id: VIEWMD-0065
title: Viewing a directory looks up an index file, else shows a directory listing
status: implemented
area: [cli, render]
effort: medium
created: 2026-08-16
updated: 2026-08-16
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-16
commits: [083ba54]
related: []
supersedes: []
changelog: "[1.25.0]"
reason:
---

# Viewing a directory looks up an index file, else shows a directory listing

## Summary

When a `path` argument passed to `viewmd` is a directory rather than a Markdown file, look for an index file (e.g. `_Index.md`) inside that directory and view it if present; otherwise render a table-of-contents view of the directory's entries with metadata instead of failing.

## Motivation / problem

Today, passing a directory path fails: `open()` raises `IsADirectoryError` (a subclass of `OSError`), which `_read_input` in `viewmd/__main__.py` lets propagate up to the existing `OSError` handler, printing `viewmd: cannot read <path>: Is a directory` and exiting 1. Wiki-style vaults (Obsidian and similar) commonly use a per-folder index note (conventionally named `_Index.md` or similar) as the folder's landing page; `viewmd`'s own wikilink resolution (`viewmd/wikilinks.py`) already navigates a note tree, so viewing a folder should behave analogously to opening its index note, or otherwise give the user a useful listing instead of an error.

## Requirements

1. MUST detect when a `path` argument is a directory (`os.path.isdir`) before attempting to open it as a file, for both the single-path and multi-path rendering branches of `viewmd/__main__.py`.
2. MUST look inside that directory for an index file named `_Index.md` (case-sensitive match on this exact name) and, if found, render it exactly as if that file's path had been passed directly (front matter, wikilinks, Mermaid, etc. all behave identically to a direct file view).
3. MUST, when no `_Index.md` exists in the directory, render a table-of-contents view of the directory's immediate entries instead of erroring:
   - MUST list Markdown files (matching viewmd's existing extension handling) and subdirectories.
   - MUST show, per entry, a name and relevant metadata: for Markdown files, at minimum a title (from front matter `title:` if present, else the first `#` heading, else the filename) and last-modified time; for subdirectories, at minimum the name and an indication it is a directory.
   - SHOULD sort entries in a stable, predictable order (e.g. directories first, then files, each alphabetically).
4. MUST NOT descend recursively into subdirectories when building the listing — one level deep only.
5. MUST continue to treat a directory argument as an error case gracefully (no raw traceback) if the directory cannot be read (e.g. permission denied), matching the existing `OSError` handling style (`viewmd: cannot read <path>: <reason>`).
6. MUST apply this behavior consistently whether the directory is the sole `path` argument or one of several `path` arguments (multi-file mode, `render_file_heading`/`render_divider` still apply around it).
7. SHOULD make the index filename (`_Index.md`) a single named constant so a future issue can make it configurable without touching call sites.

## Non-goals

- No new CLI flag for choosing an alternate index filename or disabling this behavior — a fixed convention only, for this issue.
- No recursive/nested table-of-contents (a tree view of the whole vault) — only the immediate directory's entries.
- No change to how wikilinks resolve targets that happen to be directories (`viewmd/wikilinks.py`) — this issue is scoped to `viewmd`'s CLI `path` argument handling only; whether wikilink resolution should gain the same directory fallback is a separate question for its own issue if wanted.
- No sorting/filtering options (`--sort`, hidden-file visibility, etc.) beyond the single stable default order.

## Design notes / links

- `viewmd/__main__.py`'s `_read_input` and the two rendering branches (`len(paths) == 1` and the multi-path loop) are the two integration points.
- `viewmd/frontmatter.py` already parses `title:`-style front-matter keys and is the natural source for a listed file's title metadata.

## Acceptance / verification

- New tests covering: a directory with `_Index.md` renders that file's content; a directory without one renders a listing with correct entries/metadata; an unreadable directory still errors gracefully; multi-path mode with a mix of files and directories.
- `./run-tests.sh` green.
- Manual check: `./viewmd.sh docs/` (or a similar directory with and without a `_Index.md`) against both states.

## Peer review

- **code-review agent** (agent), 2026-08-16: 3 findings at medium effort, all confirmed and fixed inline -- missing `escape()` on directory-listing table cells (Rich markup injection via a filename/title), `os.path.isfile()`-based index lookup matching case-insensitively on macOS/Windows filesystems instead of the required exact-case match, and `_markdown_title`'s heading fallback misreading a `#`-prefixed line inside a fenced code block as the document title. Regression tests added for all three.
- **George Moses** (maintainer), 2026-08-16: "commit and close" -- approved to land.
