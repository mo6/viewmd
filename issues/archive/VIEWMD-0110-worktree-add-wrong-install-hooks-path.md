---
id: VIEWMD-0110
title: Fix `./tools.sh worktree add` wrong path to install_hooks.sh
status: implemented          # proposed | in-progress | implemented | superseded | rejected
area: [tools]                  # free-form tags, e.g. render, pager, cli, tools, docs
effort: low                    # low | medium | high; required from in-progress onward
created: 2026-08-26
updated: 2026-08-26
accepted_by: George Moses               # who explicitly accepted this issue (Definition of Ready, AGILE.md);
                          # blank while status: proposed, required from in-progress onward
accepted_at: 2026-08-26               # YYYY-MM-DD the acceptance above was given; set together with accepted_by
commits: [e772bae]               # short SHAs, filled on implementation
related: [VIEWMD-0109]
supersedes: []            # VIEWMD ids this replaces, if any
changelog: "[1.54.1]"                # CHANGELOG.md anchor, filled on release
reason:                   # optional; why a rejected issue was turned down
---

# Fix `./tools.sh worktree add` wrong path to install_hooks.sh

## Summary

`tools/worktree.sh`'s `worktree add` subcommand calls `"$here/install_hooks.sh"` to install the
pre-push git hook after bootstrapping a new worktree's `.venv`, but that script actually lives at
`tools/install_hooks.sh`. The call fails with "No such file or directory", so the hook is silently
never installed for the new worktree.

## Motivation / problem

Discovered while running `./tools.sh worktree add VIEWMD-0109 feature` during VIEWMD-0109: the
worktree and `.venv` were created fine, but the script then errored out on the `install_hooks.sh`
call and exited non-zero before printing its "ready at ..." message, leaving the pre-push hook
uninstalled. `AGENTS.md` documents `install_hooks.sh` running "wired into every new worktree
automatically" as a backstop that pushes from that worktree are gated by `./run-tests.sh` -- with
this bug, that backstop silently does not fire, and nothing in the command's output makes that
obvious (it just looks like the worktree setup crashed, not like a specific known-fixable typo).
Worked around in VIEWMD-0109 by manually running `./tools/install_hooks.sh` from the new worktree
after the failure.

## Requirements

1. MUST fix `tools/worktree.sh`'s `worktree add` subcommand to call `"$here/tools/install_hooks.sh"`
   (the actual path) instead of `"$here/install_hooks.sh"`.
2. MUST verify by actually running `./tools.sh worktree add VIEWMD-NNNN <kind>` end-to-end (not just
   reading the diff) and confirming it prints "ready at ..." with no error, and that
   `git config core.hooksPath` is set afterward.
3. SHOULD add a regression test or at least a `./tools.sh worktree add`+remove smoke check to
   `run-tests.sh`'s `tools` coverage if one reasonably fits, so this class of bug (a hardcoded path
   drifting from where a script actually lives) doesn't require a live worktree creation to catch
   next time.

## Non-goals

- Any other change to worktree bootstrapping (venv creation, branch naming, etc.) -- this is a
  one-line path fix.

## Design notes / links

- `tools/worktree.sh` line 90 (as of VIEWMD-0109's landing) is the site of the bug; `here` is set at
  the top of the file to the repo root via `dirname "${BASH_SOURCE[0]}")/.."`.
- `tools/install_hooks.sh` sets `core.hooksPath` repo-wide (applies to every worktree, per its own
  echoed message), so the fix does not need to run per-worktree logic beyond calling the right path.

## Acceptance / verification

- `./run-tests.sh` stays green.
- Manual: `./tools.sh worktree add VIEWMD-TEST feature` (against a throwaway id, or by dry-running
  in a scratch clone) completes without error and installs the hook; clean up with
  `./tools.sh worktree remove`.

## Peer review

Left blank until the change is implemented and tested. Filled in as part of the Definition of
Done's landing gate ([AGILE.md](AGILE.md)): **at minimum two lines, in order** -- the reviewing
agent's own pass, then the maintainer's own sign-off -- each appended (never overwritten) as the
review happens. The maintainer's line may be transcribed by an agent from what the maintainer
actually said, attributed to the maintainer as reviewer, but it must be a real recorded verdict,
not inferred from a bare "commit and close this out?" yes.

- **<reviewer name>** (agent|maintainer), YYYY-MM-DD: verdict, and a one-line pointer to any
  findings (fixed inline, or left as a follow-up issue).
- **peer-reviewer** (agent), 2026-08-26: APPROVED. All 3 requirements verified against the diff,
  including running `./tools.sh worktree add`/`remove` end-to-end live (confirmed "ready at ..."
  with no error and `core.hooksPath` set afterward), `./run-tests.sh` green (1283 passed), no
  stale references to the old wrong path found elsewhere in the repo. No findings.
