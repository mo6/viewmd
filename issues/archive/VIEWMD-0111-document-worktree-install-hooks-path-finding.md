---
id: VIEWMD-0111
title: Document VIEWMD-0110's key finding in AGENTS.md
status: implemented          # proposed | in-progress | implemented | superseded | rejected
area: [docs]                  # free-form tags, e.g. render, pager, cli, tools, docs
effort: low                    # low | medium | high; required from in-progress onward
created: 2026-08-26
updated: 2026-08-26
accepted_by: George Moses               # who explicitly accepted this issue (Definition of Ready, AGILE.md);
                          # blank while status: proposed, required from in-progress onward
accepted_at: 2026-08-26               # YYYY-MM-DD the acceptance above was given; set together with accepted_by
commits: [a6ed818]               # short SHAs, filled on implementation
related: [VIEWMD-0110]
supersedes: []            # VIEWMD ids this replaces, if any
changelog: "[1.54.2]"                # CHANGELOG.md anchor, filled on release
reason:                   # optional; why a rejected issue was turned down
---

# Document VIEWMD-0110's key finding in AGENTS.md

## Summary

Add a "key findings" paragraph to `AGENTS.md` recording the lesson from VIEWMD-0110: a hardcoded
relative path in a maintainer-tooling script (`tools/worktree.sh`) silently drifted from the real
location of the file it referenced, and the failure mode masked itself as a full command crash
rather than a specific fixable typo.

## Motivation / problem

`AGENTS.md`'s existing body already accumulates this kind of finding after other issues (see its
several VIEWMD-NNNN-attributed paragraphs); VIEWMD-0110 fixed a real bug worth recording the same
way, so future work touching `tools/*.sh` benefits from the same caution.

## Requirements

1. MUST add one paragraph to `AGENTS.md`, in the same house style as its other "key findings"
   paragraphs, describing the VIEWMD-0110 bug, how it was discovered, and the general lesson
   (a hardcoded relative path can drift from where a file actually lives; a live run, not a diff
   read, is what catches it).

## Non-goals

- No change to any other file; this is a single-file docs update.

## Design notes / links

- See `AGENTS.md`'s existing paragraphs attributed to VIEWMD-0092/0093/0104/0106 etc. for the
  established style to match.

## Acceptance / verification

- Manual: read the added paragraph in `AGENTS.md` and confirm it accurately describes VIEWMD-0110.
- `./run-tests.sh` stays green (no code touched, but the gate is still run per policy).

## Peer review

Left blank until the change is implemented and tested. Filled in as part of the Definition of
Done's landing gate ([AGILE.md](AGILE.md)): **at minimum two lines, in order** -- the reviewing
agent's own pass, then the maintainer's own sign-off -- each appended (never overwritten) as the
review happens. The maintainer's line may be transcribed by an agent from what the maintainer
actually said, attributed to the maintainer as reviewer, but it must be a real recorded verdict,
not inferred from a bare "commit and close this out?" yes.

- **<reviewer name>** (agent|maintainer), YYYY-MM-DD: verdict, and a one-line pointer to any
  findings (fixed inline, or left as a follow-up issue).
