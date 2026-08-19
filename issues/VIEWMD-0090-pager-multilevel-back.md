---
id: VIEWMD-0090
title: Multi-level navigation history in the interactive pager (beyond one-step B)
status: proposed
area: [pager]
effort:
created: 2026-08-19
updated: 2026-08-19
accepted_by:
accepted_at:
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Multi-level navigation history in the interactive pager (beyond one-step B)

## Summary

Extend the interactive pager's link-following navigation (clicking a wikilink/Markdown link that resolves to a local `.md` file, per `viewmd/interactive_pager.py`) so `B` walks back through a full history stack rather than a single previous file, and add a forward complement so a back step can be redone.

## Motivation / problem

README documents `B` as "go back to the file you navigated from" — following the README's own wording, this reads as one step, not a stack. Clicking through several linked notes in a vault (note A → B → C) and wanting to return all the way to A means pressing `B` repeatedly while mentally tracking how many hops deep the session is; there's no visible confirmation of where each `B` press lands relative to the whole trail, and no way to go forward again after backing up too far.

## Requirements

1. MUST track a full history stack of visited documents (not just the immediately-previous one) for the lifetime of one pager session.
2. MUST make `B` pop one entry off that stack per press, correctly returning through multiple hops (A→B→C, then `B`,`B` returns to A).
3. MUST add a forward key (e.g. `F`) that re-descends the stack after one or more `B` presses, inert (no-op, same as `B` is today when there's nothing to go back to) when there is nothing to go forward to.
4. MUST preserve each visited document's scroll position on both back and forward navigation (matches current single-step `B` behavior, which already restores position — confirm and keep this, don't regress it).
5. MUST NOT change behavior for the non-link-following case (plain scrolling, search, ToC popup) at all.
6. SHOULD show current position in the trail somewhere discoverable (e.g. in the `?` help screen's `B`/`F` description, or a status-line hint), since a multi-level stack is easy to lose track of without any feedback.

## Non-goals

- No persistence of history across separate `viewmd` invocations (in-session only).
- No change to the existing single-document-only restriction on link-following (multi-file/directory-listing views still have no "current file" to navigate from, per the README's existing footnote).

## Design notes / links

Extends the existing back-navigation plumbing already present in `viewmd/interactive_pager.py` (the `B` key and whatever single-slot state backs it today) into a stack rather than replacing the mechanism.

## Acceptance / verification

New tests in `tests/test_interactive_pager.py`: a three-hop link-following sequence, back-back returns to the origin, forward-forward re-reaches the final hop, scroll position restored at each step. `./run-tests.sh` green.

## Peer review

