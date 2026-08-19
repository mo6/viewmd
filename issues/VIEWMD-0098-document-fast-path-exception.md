---
id: VIEWMD-0098
title: Document the narrow fast-path exception for small docs/metadata fixes
status: in-progress
area: [docs]
effort: low
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: []
related: [VIEWMD-0095, VIEWMD-0096, VIEWMD-0097]
supersedes: []
changelog:
reason:
---

# Document the narrow fast-path exception for small docs/metadata fixes

## Summary

VIEWMD-0095/0096/0097 each implemented a small, single-file docs/metadata fix directly on `develop` at the maintainer's explicit request, skipping the worktree AGENTS.md otherwise requires for every issue. That pattern had never been written down as a sanctioned exception, only repeated ad hoc three times in one session — this issue documents it in `AGENTS.md` itself so it's a legible, bounded part of the process rather than tribal knowledge.

## Motivation / problem

AGENTS.md's worktree rule is unconditional ("even when it's the only issue in flight"). Following it to the letter for a one-line `pyproject.toml` description fix is disproportionate ceremony, but deviating from it without writing down *why* and *when* it's acceptable risks the exception quietly widening into a habit applied to changes it was never meant to cover.

## Requirements

1. MUST add a paragraph to `AGENTS.md`, in the same voice/format as its existing process rules, documenting the fast-path exception: still requires a filed issue, still requires `accepted_by:`/`accepted_at:` and explicit landing approval (the same two gates every issue goes through), only skips the worktree/branch mechanics.
2. MUST state the exception is scoped to a single-file, few-line docs/metadata change and MUST NOT be self-judged from a size threshold or assumed to carry forward from a prior approval.
3. MUST cite VIEWMD-0095/0096/0097 as the precedent the rule generalizes.

## Non-goals

- No change to the worktree requirement for anything other than this narrow class of change.
- No automation/tooling enforcing the boundary — this is a documented judgment call, asked each time, the same way `accepted_by`/"commit and close this out?" already are.

## Acceptance / verification

Read-through: the new AGENTS.md paragraph is consistent with the surrounding worktree rule and the existing "lessons learned" paragraphs' voice. `./run-tests.sh` green.

## Peer review

- **implementing agent** (agent), 2026-08-19: added the paragraph directly per the maintainer's request, then filed this issue after the fact for tracking, per AGENTS.md's own issue-first rule — the same fast path it documents, applied to itself.
- **George Moses** (maintainer), 2026-08-19: requested directly ("document the fast path exception for (very) small changes in the development process"); approved without a worktree.
