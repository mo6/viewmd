---
id: VIEWMD-0002
title: Resolve symlinks in viewmd.sh so a symlinked launcher finds the real venv
status: implemented
area: [cli]
effort: low
created: 2026-08-02
updated: 2026-08-02
accepted_by: George Moses
accepted_at: 2026-08-02
commits: [e41459d]
related: []
supersedes: []
changelog: "[0.1.1]"
reason:
---

# Resolve symlinks in viewmd.sh so a symlinked launcher finds the real venv

## Summary

`viewmd.sh` locates the project's `.venv` via `dirname "${BASH_SOURCE[0]}"`, which resolves to a
symlink's own location rather than its target when the script is invoked through a symlink (e.g.
`~/.local/bin/viewmd -> /path/to/viewmd/viewmd.sh`). Running the symlinked command from any
directory then fails with a bogus "no virtualenv" error pointing at `~/.local/bin/.venv`.

## Motivation / problem

Reported by the maintainer: linked `viewmd.sh` to `~/.local/bin/viewmd` for convenient global
use, and running it from outside the project directory fails to find the venv.

## Requirements

1. MUST resolve `${BASH_SOURCE[0]}` through any symlink chain to the real script path before
   computing the project root, so a symlinked launcher works identically to the unlinked script,
   from any working directory.

## Non-goals

- Packaging/distributing viewmd as an installable console script outside the repo's own venv
  (that's what `pip install -e .` + `PATH` already gives; this issue is only about the `.sh`
  launcher's symlink handling).

## Design notes / links

Same fix pattern applies to `tools.sh`, which has the identical `dirname "${BASH_SOURCE[0]}"`
line, even though it hasn't been reported symlinked yet — fixing it now avoids the same bug
surfacing there later for a one-line-cost.

## Acceptance / verification

- Manual: `ln -sf $(pwd)/viewmd.sh /tmp/viewmd-link && cd / && /tmp/viewmd-link --version`
  succeeds (currently fails with "no virtualenv at /tmp/.venv").
- `./run-tests.sh` stays green.

## Peer review

- **Claude (Sonnet 5)** (agent), 2026-08-02: PASS. `./run-tests.sh` green. Verified manually:
  `ln -sf $(pwd)/viewmd.sh /tmp/viewmd-link && (cd / && /tmp/viewmd-link --version)` now succeeds
  (was the exact reported failure before the fix); same repro against a symlinked `tools.sh`
  succeeds (`tools-link issues --check` from `/`).
