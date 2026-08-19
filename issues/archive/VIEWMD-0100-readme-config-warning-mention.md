---
id: VIEWMD-0100
title: Mention the unrecognized-config-key warning in README.md
status: implemented
area: [docs]
effort: low
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: [f9c8605]
related: [VIEWMD-0083]
supersedes: []
changelog: "[1.46.2]"
reason:
---

# Mention the unrecognized-config-key warning in README.md

## Summary

README.md's "Configuration file" section still says "An unrecognized key is ignored (forward-compatible with future options)" with no further mention — stale since VIEWMD-0083 added a `viewmd: <path>:<line>: unrecognized config key <key>` stderr warning for exactly that case.

## Motivation / problem

Found while auditing README.md for staleness after landing VIEWMD-0083/0086/0087/0099 this session — a reader following the config docs would not know an unrecognized key now warns.

## Requirements

1. MUST update README.md's config-key paragraph to mention the stderr warning VIEWMD-0083 added, while still noting the key is otherwise ignored (non-fatal, forward-compatible).

## Non-goals

- No change to any other part of README.md.

## Acceptance / verification

Read-through: the paragraph matches `viewmd/config.py`'s actual behavior. `./run-tests.sh` green.

## Peer review

- **implementing agent** (agent), 2026-08-19: one-line-paragraph fix, directly per the maintainer's request; filed for tracking per AGENTS.md's issue-first rule, same fast path as VIEWMD-0095/0096/0097/0098 (no worktree).
- **George Moses** (maintainer), 2026-08-19: requested directly ("file it and land it fast-path"); approved without a worktree.
