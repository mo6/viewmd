---
id: VIEWMD-0010
title: Require an explicit, recorded maintainer peer-review line before landing
status: in-progress
area: [docs]
effort: low
created: 2026-08-02
updated: 2026-08-02
accepted_by: George Moses
accepted_at: 2026-08-02
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Require an explicit, recorded maintainer peer-review line before landing

## Summary

Today's Definition of Done ([issues/AGILE.md](AGILE.md)) requires *a* peer review recorded in
the issue's Peer review section (in practice, always the reviewing agent's own pass) plus a
separate, unrecorded "commit and close this out?" yes/no from the maintainer. That yes/no is a
landing decision, not a substantive review with its own recorded verdict. The Definition of Done
should require, as a minimum, two distinct recorded peer-review lines before an issue can land:
the reviewing agent's pass, and the maintainer's own sign-off -- in that order, both appended to
the issue the same way, never overwritten.

## Motivation / problem

Raised by the maintainer while landing VIEWMD-0009: wants an explicit peer-review step by the
maintainer defined in the SDLC, not folded into the informal "commit and close this out?"
question. Separating "did the maintainer review this" from "does the maintainer want to land it
now" makes the review trail actually show maintainer review happened, issue by issue, rather
than only ever showing an agent's self-review.

## Requirements

1. MUST update [issues/AGILE.md](AGILE.md)'s Definition of Done so step 3 (peer review recorded
   in the issue) explicitly requires at minimum two lines: the reviewing agent's pass, and the
   maintainer's own sign-off, in that order, before step 4 (commit and close this out?) can be
   asked.
2. MUST update [issues/TEMPLATE.md](TEMPLATE.md)'s Peer review section instructions to state the
   same minimum explicitly (currently says "one line per reviewer, agent or human," which reads
   as optional-either; it should read as both, at minimum).
3. MUST NOT require the maintainer's sign-off line to be written by the maintainer's own hand --
   an agent may transcribe the maintainer's stated verdict into the issue (e.g. "maintainer
   reviewed the diff and confirmed X, Y, Z work as expected") as long as it is attributed to the
   maintainer as reviewer and reflects what the maintainer actually said, not the agent's own
   opinion restated.

## Non-goals

- Retroactively adding a maintainer peer-review line to already-archived issues (VIEWMD-0001
  through VIEWMD-0009). This applies going forward only.
- Any change to who may implement an issue (agent, Cursor, etc.) or to the Definition of Ready;
  this only changes the Definition of Done's review step.

## Design notes / links

Extends [issues/AGILE.md](AGILE.md) and [issues/TEMPLATE.md](TEMPLATE.md), both process
documents with no code involved.

## Acceptance / verification

- `./run-tests.sh` green (no code changes expected to break anything; the `issues` step still
  passes since this issue doesn't change front-matter shape).
- Manual: read the updated Definition of Done and Peer review template section and confirm they
  state the two-line minimum (agent, then maintainer) plainly.
- The next issue landed after this one demonstrates the new shape: its Peer review section shows
  both an agent line and a maintainer line before it's archived.

## Peer review

- **Claude (Sonnet 5)** (agent), 2026-08-02: PASS. `./run-tests.sh` green (54 tests, ruff clean,
  pip-audit clean, issues index current -- this issue changes only `issues/AGILE.md` and
  `issues/TEMPLATE.md` prose, no code). Confirmed both files now state the two-reviewer minimum
  (agent, then maintainer, in that order) plainly, and that a bare "commit and close this out?"
  yes is explicitly called out as insufficient on its own. Applying the new rule to this issue's
  own landing rather than deferring it, since it's able to.
- **George Moses** (maintainer), 2026-08-02: confirmed as correct -- the two-reviewer requirement
  (agent, then maintainer, in that order) reads correctly in both `issues/AGILE.md` and
  `issues/TEMPLATE.md`.
