---
id: VIEWMD-0095
title: pyproject.toml's package description still says "paging into less"
status: in-progress
area: [docs]
effort: low
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: []
related: []
supersedes: []
changelog:
reason:
---

# pyproject.toml's package description still says "paging into less"

## Summary

`pyproject.toml`'s `[project] description` field reads "View Markdown files from the command line, with color, tables, Mermaid diagrams, and paging into less." — but VIEWMD-0072 removed the external `less`/`$PAGER` pager entirely; viewmd owns its own interactive pager (`viewmd/interactive_pager.py`) and never spawns a subprocess for paging. This is the metadata shown on PyPI (once VIEWMD-0069 publishes it) and by `pip show viewmd`, so it's the first thing a prospective user reads about the tool, and it's wrong.

## Motivation / problem

README.md (line 79) and `docs/PLAN.md` both correctly describe the current, self-contained pager ("viewmd never spawns an external pager process: no `less` by default, and no `$PAGER` override either"), but `pyproject.toml`'s own description was never updated when VIEWMD-0072 landed, leaving a factually incorrect claim in the package's own metadata.

## Requirements

1. MUST update `pyproject.toml`'s `description` field to no longer claim paging into `less`, describing the actual self-contained interactive pager instead (or omitting the paging mechanism detail entirely if the description is meant to stay high-level).
2. MUST grep the repo for any other stale `pyproject.toml`-adjacent metadata (e.g. `README.md`'s own top-of-file blurb, if any, though it already reads correctly per the Motivation section) referencing `less` as the default pager, to catch any sibling copy of the same stale claim.

## Non-goals

- No change to README.md's own wording, which already correctly describes the self-contained pager.
- No change to any other `pyproject.toml` field (classifiers, dependencies, etc.).

## Design notes / links

See VIEWMD-0072 (external-pager removal) for the change this description fell out of sync with.

## Acceptance / verification

`grep -n less pyproject.toml` shows no reference to `less` as viewmd's pager. `./run-tests.sh` green (no test currently pins this string, but the gate should still pass cleanly after the edit).

## Peer review

- **implementing agent** (agent), 2026-08-19: one-line fix, `pyproject.toml`'s `description` no longer mentions `less`; checked `docs/PLAN.md`'s own reference to `less` and confirmed it's historical narrative describing what VIEWMD-0072 changed away from, not a stale current-state claim, so left untouched per the issue's Non-goals. `./run-tests.sh` green (1100 passed, ruff/pip-audit/issues clean). Implemented directly on `develop` at the maintainer's explicit request, no worktree/branch for this one-line change.
- **George Moses** (maintainer), 2026-08-19: requested doing this without a worktree; approved.

