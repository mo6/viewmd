# Changelog

All notable changes to viewmd, newest first. Dates are the release date.

Ordinary semver (`MAJOR.MINOR.PATCH`).

## [1.0.1] — 2026-08-02

- **Fix: `pyproject.toml` license metadata said "Proprietary"** (VIEWMD-0008, tools): contradicted the MIT `LICENSE` file added on `main`. Now reads MIT, matching it.

## [1.0.0] — 2026-08-02

- **First stable release.** Everything from `0.1.0` through `0.5.0` below: render a Markdown file to ANSI in the terminal, auto-paged into `less`; `--no-pager`, `--color`, `--width`/`--width full`; a YAML front-matter block renders as a table (empty fields hidden by default, `--full-front-matter` to show them all) with a clear divider before the body; Obsidian-style `[[wikilinks]]` highlighted like standard Markdown links. No functional change from `0.5.0` — this tags the point the tool is considered stable for everyday use.

## [0.5.0] — 2026-08-02

- **Highlight Obsidian-style `[[wikilinks]]`** (VIEWMD-0006, render): `[[Target]]` and `[[Target|Display text]]` now render with the same highlight a standard Markdown link gets (blue + underline), brackets gone. Fenced code blocks (including ones indented under a list item) and inline code spans are left untouched, so wikilink-shaped text in real code renders as literal code.

## [0.4.0] — 2026-08-02

- **Hide empty front-matter fields by default; add `--full-front-matter`** (VIEWMD-0005, render/cli): a front-matter field with no value (or only whitespace) no longer shows up as a blank row in the table. `--full-front-matter` restores every parsed field, empty ones included.

## [0.3.0] — 2026-08-02

- **Render YAML front matter as a table, divided from the body** (VIEWMD-0004, render): a file opening with a `--- ... ---` block now renders that block as a key/value table (with `[a, b]`-style lists shown comma-joined) followed by a dim double-line divider, ahead of the rendered document body. A file with no front matter, an unterminated `---` block, or a block that parses to zero pairs renders exactly as before.

## [0.2.0] — 2026-08-02

- **Cap render width to 100 columns by default; `--width N` or `--width full` to override** (VIEWMD-0003, cli/render): a wide terminal no longer stretches prose and tables to the full window; the default render width is now `min(100, detected terminal width)`. `--width` still takes an exact column count, and now also accepts the literal `full` to render at the full detected terminal width, uncapped by the 100-column default.

## [0.1.1] — 2026-08-02

- **Fix: symlinked `viewmd.sh`/`tools.sh` couldn't find the project's venv** (VIEWMD-0002, bug, cli): `dirname "${BASH_SOURCE[0]}"` resolved to a symlink's own location rather than its target, so `ln -sf .../viewmd.sh ~/.local/bin/viewmd` failed with a bogus "no virtualenv" error when run from outside the project directory. Both scripts now walk the symlink chain by hand (`readlink`, no `-f` since macOS lacks it) before computing the project root.

## [0.1.0] — 2026-08-02

- **Initial release** (VIEWMD-0001): render a Markdown file to ANSI in the terminal, auto-paged into `less` when stdout is a terminal. Headers, emphasis, lists, blockquotes, GFM tables, and fenced code blocks (Pygments syntax highlighting, exact spacing preserved for ASCII art) via `rich.markdown.Markdown`. `--no-pager`, `--color {auto,always,never}` (respecting `NO_COLOR`), `--width`, and stdin input (`-` or omitted). Also ships the issue-first SDLC scaffolding (`AGENTS.md`, `issues/`, `tools/issues.py`) that governs how future changes land.
