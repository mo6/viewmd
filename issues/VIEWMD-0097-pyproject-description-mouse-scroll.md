---
id: VIEWMD-0097
title: Mention mouse/scroll support in pyproject.toml's package description
status: in-progress
area: [docs]
effort: low
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: []
related: [VIEWMD-0095]
supersedes: []
changelog:
reason:
---

# Mention mouse/scroll support in pyproject.toml's package description

## Summary

`pyproject.toml`'s `[project] description` currently reads "View Markdown files from the command line, with color, tables, Mermaid diagrams, and its own built-in interactive pager." — it names the pager but not that it's mouse-driven (scroll, click-to-follow, hover highlighting), which is one of viewmd's more distinctive features versus a plain `less`-based viewer.

## Motivation / problem

Same metadata surface VIEWMD-0095 just corrected (PyPI listing, `pip show viewmd`) — the description is a prospective user's first impression, and mouse/scroll support (VIEWMD-0072/0075/0076/0092) is a substantial, distinguishing part of the pager that the current wording doesn't hint at.

## Requirements

1. MUST update `pyproject.toml`'s `description` to mention mouse/scroll support in the interactive pager.

## Non-goals

- No change to any other `pyproject.toml` field.
- No change to README.md wording (already covers this in detail).

## Acceptance / verification

Read-through: the description names mouse/scroll support. `./run-tests.sh` green.

## Peer review

- **implementing agent** (agent), 2026-08-19: one-line fix, directly per the maintainer's request; filed for tracking per AGENTS.md's issue-first rule, same fast path as VIEWMD-0095/0096 (no worktree).
- **George Moses** (maintainer), 2026-08-19: requested directly; approved without a worktree.
