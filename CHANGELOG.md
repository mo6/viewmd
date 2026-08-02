# Changelog

All notable changes to viewmd, newest first. Dates are the release date.

Ordinary semver (`MAJOR.MINOR.PATCH`).

## [0.1.0] — 2026-08-02

- **Initial release** (VIEWMD-0001): render a Markdown file to ANSI in the terminal, auto-paged into `less` when stdout is a terminal. Headers, emphasis, lists, blockquotes, GFM tables, and fenced code blocks (Pygments syntax highlighting, exact spacing preserved for ASCII art) via `rich.markdown.Markdown`. `--no-pager`, `--color {auto,always,never}` (respecting `NO_COLOR`), `--width`, and stdin input (`-` or omitted). Also ships the issue-first SDLC scaffolding (`AGENTS.md`, `issues/`, `tools/issues.py`) that governs how future changes land.
