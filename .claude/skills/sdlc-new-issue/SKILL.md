---
name: sdlc-new-issue
description: Draft a new viewmd issue and get it through the Definition of Ready. Use whenever a change (feature, bug fix, refactor) is about to start and no issues/VIEWMD-NNNN file exists for it yet -- AGENTS.md requires every change to have one.
---

Draft one `issues/VIEWMD-NNNN-*.md` file and get it explicitly accepted, per `AGENTS.md`'s "every
change gets an issue first" rule and `issues/AGILE.md`'s Definition of Ready. Do not write any
implementation code before this is done.

1. Run `./tools.sh issues --check` first. Its exit and the current highest id under `issues/` and
   `issues/archive/` tell you the next free `VIEWMD-NNNN`.
2. Copy `issues/TEMPLATE.md` to `issues/VIEWMD-NNNN-<short-slug>.md`, `status: proposed`. Fill in
   Summary, Motivation, a plain numbered MUST/SHOULD/MUST NOT Requirements list, Non-goals, Design
   notes, and Acceptance/verification from the conversation. Leave `accepted_by`/`accepted_at`/
   `effort` for the next step -- `effort` is required from `in-progress` onward, so decide it now
   (low/medium/high) but it can be filled at either step.
3. Show the drafted issue to the maintainer and ask outright whether it's accepted -- never infer
   acceptance from silence or from the maintainer not objecting to something you're already doing.
4. Only on an explicit yes: get the maintainer's git identity from `.gitconfig`
   (`git config user.name`/`git config user.email` -- never a guessed or session-supplied identity),
   fill `accepted_by`/`accepted_at` with it and today's date, and move `status` to `in-progress`.
5. Regenerate the index: `./tools.sh issues`.
6. Commit the issue file + `issues/README.md` together on `develop`, message
   `Accept VIEWMD-NNNN, move to in-progress` (matches the existing history's pattern, e.g. commit
   `c54a02e`) -- only after an explicit "yes, commit this" from the maintainer, same as any commit.

Next step is the `sdlc-start-issue` skill, to create the implementation worktree.
