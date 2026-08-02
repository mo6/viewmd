---
id: VIEWMD-0008
title: Fix pyproject.toml license metadata to match the MIT LICENSE file
status: implemented
area: [tools]
effort: low
created: 2026-08-02
updated: 2026-08-02
accepted_by: George Moses
accepted_at: 2026-08-02
commits: [964efa9]
related: []
supersedes: []
changelog: "[1.0.1]"
reason:
---

# Fix pyproject.toml license metadata to match the MIT LICENSE file

## Summary

`pyproject.toml` declares `license = { text = "Proprietary" }`, but the maintainer added an MIT
`LICENSE` file directly on `main` (pulled into `develop`). The two now contradict each other.

## Motivation / problem

Package metadata read by tooling (`pip show`, PyPI if ever published, license scanners) would
report "Proprietary" while the actual license grant in the repo is MIT -- a real, user-facing
inconsistency, not cosmetic.

## Requirements

1. MUST set `pyproject.toml`'s `license` to reflect MIT, matching `LICENSE`.

## Non-goals

- Any change to `LICENSE` itself or its copyright holder/year.

## Design notes / links

n/a -- one-line metadata fix.

## Acceptance / verification

- `./run-tests.sh` green.
- Manual: `python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['license'])"` shows MIT, not Proprietary.

## Peer review

- **Claude (Sonnet 5)** (agent), 2026-08-02: PASS. `./run-tests.sh` green (54 tests). Verified
  `pyproject.toml`'s `license` field reads `{'text': 'MIT'}` via `tomllib`, matching `LICENSE`.
