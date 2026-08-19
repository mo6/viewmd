---
id: VIEWMD-0084
title: Support a project-local config file alongside the XDG global one
status: proposed
area: [config, cli]
effort:
created: 2026-08-19
updated: 2026-08-19
accepted_by:
accepted_at:
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Support a project-local config file alongside the XDG global one

## Summary

Add an optional `.viewmd` file, read from the current working directory (or the nearest ancestor directory that has one, similar to how `.gitignore`/`.editorconfig` are discovered), whose settings apply on top of the XDG global config but below explicit CLI flags — so a team can standardize `width`/`toc`/`color` for a shared vault or docs repo without every contributor editing their own `~/.config/viewmd/config`.

## Motivation / problem

Today the only persisted defaults come from one global, per-user file (`viewmd/config.py`). A repo or Obsidian vault with its own house style for viewing (e.g. `width = 80` to match a wrapped-prose convention) has no way to ship that preference alongside the content itself; every reader must be told to configure it by hand.

## Requirements

1. MUST look for `.viewmd` starting in the current working directory and walking up parent directories, stopping at the first one found (or the filesystem root, or `$HOME`, whichever comes first) — the same discovery order as `.gitignore`/`.editorconfig` tooling commonly uses.
2. MUST use the exact same `key = value` syntax and key set as the existing config file (reuse `parse_config`).
3. MUST apply precedence CLI flag > project-local `.viewmd` > XDG global config > built-in default, extending `coalesce()`'s existing chain in `viewmd/__main__.py` with one more tier.
4. MUST respect `VIEWMD_NO_CONFIG` and `--config PATH` exactly as today: `--config PATH` replaces *both* tiers with the single named file; `VIEWMD_NO_CONFIG` skips *both* discovery paths, not just the XDG one.
5. SHOULD NOT read a project-local file when stdin (`-`) is the only input — there is no "current directory" for the document that a project file would meaningfully apply to. (Whether cwd-based discovery still makes sense in the stdin case is a design call for implementation; document the chosen answer here before building.)

## Non-goals

- No new syntax for the project file (no per-language, per-glob, or nested-directory-scoped overrides — one flat file, same key set as today).
- No auto-generation/scaffolding command for `.viewmd` (no `viewmd --init-config`).

## Design notes / links

Builds directly on `viewmd/config.py`'s existing `Config`/`coalesce`/`parse_config`; this issue is additive to that module's precedence chain, not a rewrite of it.

## Acceptance / verification

New tests in `tests/test_config.py` covering: discovery walks up from a nested cwd to find `.viewmd`; project file overrides XDG global but loses to an explicit CLI flag; `VIEWMD_NO_CONFIG` suppresses both; `--config PATH` bypasses discovery entirely. `./run-tests.sh` green.

## Peer review

