---
name: start-issue
description: Start implementing an already-accepted viewmd issue in its own worktree. Use once an issues/VIEWMD-NNNN file has status in-progress with accepted_by/accepted_at set, before writing any code for it.
---

Move from an accepted issue to an isolated worktree ready for implementation, per `AGENTS.md`'s
"every issue is implemented in its own sibling git worktree" rule.

1. Read the issue file (`issues/VIEWMD-NNNN-*.md`). Confirm the Definition of Ready
   (`issues/AGILE.md`) is actually satisfied: `effort` is set, `status: in-progress`, and both
   `accepted_by` and `accepted_at` are filled. If any of those is missing, stop and use the
   `dev:new-issue` skill's acceptance step first -- do not start a worktree for an issue that
   hasn't actually been accepted yet.
2. Pick the branch kind matching the issue (`bug`, `feature`, or `story`) and run:
   `./tools.sh worktree add VIEWMD-NNNN <kind>`. This creates `../<repo>-VIEWMD-NNNN` on
   `<kind>/VIEWMD-NNNN` cut from `develop`, bootstraps its own `.venv`, and installs the pre-push
   hook (`tools/install_hooks.sh`, wired into this bootstrap).
3. Switch the session into that worktree (`EnterWorktree` with the printed path, or `cd`) and
   confirm `./run-tests.sh` runs clean from a fresh checkout before starting on the actual change.

Implement against the issue's Requirements from there. When the change is complete and
`./run-tests.sh` is green, use the `dev:land-issue` skill.
