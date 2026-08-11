---
id: VIEWMD-0051
title: Bootstrap script for parallel per-issue git worktree sessions
status: in-progress
area: [tools, docs]
effort: low
created: 2026-08-11
updated: 2026-08-11
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-11
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Bootstrap script for parallel per-issue git worktree sessions

## Summary

Add a `tools/worktree.sh` helper (run via `./tools.sh worktree ...`) that creates a sibling `git worktree` for a given `VIEWMD-NNNN` issue, cut from `develop` on the correctly-named branch, with its own `.venv` installed — so multiple issues can be worked in parallel, each in its own directory, each with its own coding-agent session (Claude Code, Cursor, or both) pointed at it, without the sessions stepping on each other's checked-out files or virtualenvs. Document the workflow in `AGENTS.md`.

## Motivation / problem

`AGENTS.md` already establishes one branch per issue (`bug|feature|story/VIEWMD-NNNN`, cut from `develop`), but today that branch is checked out in the single primary working directory, so only one issue can be actively worked at a time — a second agent session in the same directory would see the first one's uncommitted changes and could not check out a different branch without disrupting it. `git worktree` solves the directory-sharing problem, but each worktree still needs its own `.venv` (an editable `pip install -e .` is path-bound to the directory it was installed from, so a `.venv` from one worktree does not work from another), and creating one by hand is enough steps (worktree add, venv create, editable install, dev extras) that it invites drift or shortcuts under time pressure.

## Requirements

1. MUST provide `tools/worktree.sh` runnable as `./tools.sh worktree add VIEWMD-NNNN [bug|feature|story]` that creates `../viewmd-VIEWMD-NNNN` as a `git worktree` on a new branch `<kind>/VIEWMD-NNNN` (default kind `feature` if omitted), branched from `develop` (matching `AGENTS.md`'s existing branch-naming and base-branch rules), and fails with a clear message if the target directory or branch already exists.
2. MUST have the same subcommand create `.venv` inside the new worktree and run `pip install -e '.[dev]'` in it, so `./run-tests.sh` and `./tools.sh` work standalone from the new worktree directory immediately after creation.
3. MUST provide `./tools.sh worktree list` that wraps `git worktree list` filtered/annotated with which `VIEWMD-NNNN` each corresponds to (parsed from branch name), so it's easy to see what's in flight across all worktrees at a glance.
4. MUST provide `./tools.sh worktree remove VIEWMD-NNNN` that runs `git worktree remove` for the corresponding directory, refusing (matching `git worktree remove`'s own default behavior) if there are uncommitted changes, and printing the branch name so the caller can separately decide whether to delete it.
5. MUST NOT delete the branch on `worktree remove` — branch deletion stays a separate, explicit `git branch -d` step so an agent or maintainer can't lose unmerged work by conflating "stop working here" with "throw this away."
6. SHOULD detect and skip venv bootstrap (step 2) if a `.venv` already exists at the target path, so `worktree add` is safe to re-run after a partial failure.
7. MUST document the workflow in `AGENTS.md`: when to use a worktree (working >1 issue at once), how to point a Claude Code session at one (`EnterWorktree` with `path:` for an existing worktree, or plain `cd`), how to point a Cursor window at one (open the sibling directory as its own window), and the constraint that each worktree still goes through the same Definition of Ready/Done gates independently — a worktree changes *where* an issue is worked, not the process it's worked under.

## Non-goals

- Not adding any cross-worktree locking, coordination, or shared-state mechanism for two agents editing the same file in different worktrees — that conflict surfaces the normal way, at merge time into `develop`, and is out of scope here.
- Not automating branch or worktree cleanup after a merge — `worktree remove` (requirement 4) is a manual, explicit step, matching the rest of `AGENTS.md`'s landing process (nothing lands or gets cleaned up "on its own initiative").
- Not covering CI or any shared/remote parallel-execution setup — this is local-only, single-maintainer tooling.
- Not changing anything about the Definition of Ready/Done gates themselves (`issues/AGILE.md`) — a worktree is purely a filesystem/process convenience.

## Design notes / links

`AGENTS.md`'s existing branch-naming and `develop`-as-base rules govern the branch this script creates; this issue only automates checking those rules' preconditions (fresh worktree dir, fresh branch, based on current `develop`). See `tools.sh`'s own header comment for the calling convention (`.py`/`.sh` under `tools/`, invoked as `./tools.sh <tool> [args...]`) that `worktree.sh` should follow.

## Acceptance / verification

- `./tools.sh worktree add VIEWMD-9999 feature` (against a scratch/throwaway id) creates `../viewmd-VIEWMD-9999` on branch `feature/VIEWMD-9999` based on `develop`, with a working `.venv` — verified by running `./run-tests.sh` from inside it and seeing pytest/ruff/pip-audit/issues-check all execute (pass/fail content aside).
- `./tools.sh worktree add` re-run against an already-existing target directory/branch fails with a clear error rather than silently overwriting or duplicating.
- `./tools.sh worktree list` output correctly reflects the created worktree and its issue id.
- `./tools.sh worktree remove VIEWMD-9999` removes the directory, leaves the branch intact (confirmed via `git branch --list feature/VIEWMD-9999`), and refuses if uncommitted changes are present (verified by dirtying the worktree first).
- `AGENTS.md` reads cleanly with the new section in place, cross-checked by a peer review pass that it doesn't contradict the existing Definition of Ready/Done text.

## Peer review

- **general-purpose review agent** (agent), 2026-08-11: pass-with-notes. Verified requirements
  1-6 by smoke-testing `add`/`list`/`remove` with throwaway ids from the primary checkout
  (duplicate-branch/malformed-id rejection, `.venv` bootstrap and skip-if-present, `list`
  annotation, dirty-worktree removal refusal, branch left intact on `remove`). Found one real bug
  via the "run from inside a worktree" edge case it was asked to check: `repo_name`/`siblings_dir`
  were derived from `${BASH_SOURCE[0]}`'s own location, so invoking `worktree add` from inside an
  already-created linked worktree (rather than the main checkout) silently drifted the
  `../<repo>-VIEWMD-NNNN` naming convention (e.g. producing `../viewmd-VIEWMD-8888-VIEWMD-8889`
  instead of `../viewmd-VIEWMD-8889`). Fixed inline: `repo_name`/`siblings_dir` are now derived
  from the main worktree's path via `git rev-parse --git-common-dir`, independently re-verified by
  copying the fixed script into a linked worktree and creating a further worktree from inside it
  (landed at the correctly-anchored sibling path). Two non-blocking notes left as-is: the
  4-digit-id regex (`^VIEWMD-[0-9]{4}$`) will need widening once ids pass `VIEWMD-9999`, and
  `remove` has no guard against an ambiguous match if both a `bug/` and `feature/` branch existed
  for the same id (out of scope per the project's one-branch-per-issue convention). Minor notes
  aside, style matches `tools/build_example_md.sh`'s conventions and the AGENTS.md prose
  accurately describes the script's actual (post-fix) behavior.
- **George Moses** (maintainer), 2026-08-11: approved after reviewing the diff and the agent's
  review findings above — commit and close out.

