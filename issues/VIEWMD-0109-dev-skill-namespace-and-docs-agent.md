---
id: VIEWMD-0109
title: Namespace SDLC skills under dev:, add a documentation agent
status: in-progress          # proposed | in-progress | implemented | superseded | rejected
area: [tools, docs]                  # free-form tags, e.g. render, pager, cli, tools, docs
effort: low                    # low | medium | high; required from in-progress onward
created: 2026-08-26
updated: 2026-08-26
accepted_by: George Moses <gmo6nl@gmail.com>               # who explicitly accepted this issue (Definition of Ready, AGILE.md);
                          # blank while status: proposed, required from in-progress onward
accepted_at: 2026-08-26               # YYYY-MM-DD the acceptance above was given; set together with accepted_by
commits: []               # short SHAs, filled on implementation
related: [VIEWMD-0108]
supersedes: []            # VIEWMD ids this replaces, if any
changelog:                # CHANGELOG.md anchor, filled on release
reason:                   # optional; why a rejected issue was turned down
---

# Namespace SDLC skills under dev:, add a documentation agent

## Summary

Move the four issue-lifecycle skills (`new-issue`, `start-issue`, `land-issue`, `release`) under a
`dev:` namespace so they group together in skill listings, and add a new `documentation` agent that
checks whether a change's user-facing docs (`README.md`, `docs/example.md`) need updating, since
they should be updated alongside the code and not just recorded in `CHANGELOG.md`.

## Motivation / problem

VIEWMD-0108 added the SDLC skills/agent encoding but the changes it shipped were reflected only in
`CHANGELOG.md`, not in `README.md` or `docs/example.md`. There's currently no step in the lifecycle
that prompts an agent to check user-facing documentation for drift. Separately, as more
Claude Code skills accumulate in `.claude/skills/`, an unprefixed flat list is harder to scan;
grouping the process/SDLC skills under one namespace (`dev:new-issue`, `dev:start-issue`,
`dev:land-issue`, `dev:release`) keeps them visually distinct from task-specific skills.

## Requirements

1. MUST move `.claude/skills/{new-issue,start-issue,land-issue,release}` to
   `.claude/skills/dev/{new-issue,start-issue,land-issue,release}` so the Skill tool lists them as
   `dev:new-issue`, `dev:start-issue`, `dev:land-issue`, `dev:release` (directory-scoped namespacing,
   per the Skill tool's own `apps/web:deploy` convention).
2. MUST update cross-references between these skills' `SKILL.md` bodies (e.g. "use the `new-issue`
   skill") and `AGENTS.md`'s description of them to the new `dev:` names.
3. MUST add a new `.claude/agents/documentation.md` agent whose job is: given a finished issue's
   diff (or a `CHANGELOG.md` entry), determine whether `README.md` needs updating to describe new
   or changed user-facing behavior, and whether `docs/example.md` needs a new/updated example for
   a new feature; make those edits directly when needed.
4. MUST wire the `documentation` agent into the `land-issue` skill's flow, run after tests pass and
   before/alongside the peer-review step, so documentation drift is caught as part of the
   Definition of Done rather than left to be noticed later.
5. SHOULD NOT change any of the four skills' actual process steps (Definition of Ready/Done gates,
   worktree mechanics, commit patterns) -- this issue is a naming/grouping and docs-coverage change,
   not a process rewrite.
6. MUST NOT rename the `peer-reviewer` agent or move it under any namespace -- it stays
   `.claude/agents/peer-reviewer.md`, unaffected by this issue.

## Non-goals

- Reworking the Definition of Ready/Done gates themselves.
- Auto-generating changelog entries or versioning.
- Retroactively fixing VIEWMD-0108's own missing README changes (a separate, follow-up concern if
  still needed after this lands).

## Design notes / links

- `AGENTS.md`'s "issue lifecycle ... encoded as Claude Code skills" paragraph documents the current
  skill set and needs its skill names updated in place.
- Skill tool's own convention: "Directory-scoped skills are listed with a path prefix
  (`apps/web:deploy`)" -- moving skills under `.claude/skills/dev/` is what produces the `dev:`
  prefix, no special config needed.

## Acceptance / verification

- `./run-tests.sh` stays green (this change touches no Python code, but `issues --check` and any
  doc-lint the suite runs must still pass).
- Manually confirm the Skill tool's available-skills listing shows `dev:new-issue`, `dev:start-issue`,
  `dev:land-issue`, `dev:release` after the move.
- Manually confirm `.claude/agents/documentation.md` exists, describes README/docs/example.md
  drift-checking, and is referenced from `dev:land-issue`'s `SKILL.md`.

## Peer review

Left blank until the change is implemented and tested. Filled in as part of the Definition of
Done's landing gate ([AGILE.md](AGILE.md)): **at minimum two lines, in order** -- the reviewing
agent's own pass, then the maintainer's own sign-off -- each appended (never overwritten) as the
review happens. The maintainer's line may be transcribed by an agent from what the maintainer
actually said, attributed to the maintainer as reviewer, but it must be a real recorded verdict,
not inferred from a bare "commit and close this out?" yes.

- **peer-reviewer** (agent), 2026-08-26: APPROVED, all six requirements verified against the diff
  and file contents, ./run-tests.sh green (1282 passed), no issues found beyond a non-blocking note
  that the implementation is still uncommitted working-tree state pending the land-issue flow's own
  step-6 commit.
- **George Moses** (maintainer), 2026-08-26: commit and close this out.
