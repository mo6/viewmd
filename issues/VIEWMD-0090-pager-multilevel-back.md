---
id: VIEWMD-0090
title: Multi-level navigation history in the interactive pager (beyond one-step B)
status: in-progress
area: [pager]
effort: medium
created: 2026-08-19
updated: 2026-08-20
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-20
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

- **Claude Sonnet 5** (agent, implementer self-review -- not the independent pass the Definition of Done still requires before "commit and close this out?"), 2026-08-20: Implemented in `viewmd/interactive_pager.py`'s `_run()`. Notable finding before writing any code: the pre-existing `nav_stack` (VIEWMD-0076) was already a plain `list` popped via `.pop()`, so requirements 1/2 (a full multi-hop back stack, `B`,`B` walking A→B→C back to A) were *already* satisfied by the existing code -- the README's "go back to the file you navigated from" wording undersold what was actually there. The only real gaps were requirement 3 (no forward complement existed at all) and requirement 6 (no discoverable trail position). Added a mirror-image `fwd_stack`: `B` pops `nav_stack` and pushes the document being left onto `fwd_stack`; `F` is the exact reverse. A fresh link-navigation clears `fwd_stack` (browser-style forward-history invalidation) -- not explicitly required by the issue but a design decision I made to avoid `F` resurrecting a document the reader has since branched away from; covered by its own test. `_keybind_help`'s `has_back: bool` became `back_count`/`forward_count: int`, so the echo-area hint reads e.g. `B: back (2)` / `F: fwd (1)` -- satisfies requirement 6's SHOULD via a live count in the status line; the `?` help screen's own `B`/`F` rows describe the mechanism in words but don't carry a live count (static table, no per-frame state) -- a scope judgment call, flagged for the maintainer rather than decided unilaterally.
  Self-review found and fixed three real bugs before landing, not just a description of the diff: (1) initial acceptance test wrote all synthetic input in one `os.write` before starting `run()` -- with two navigating clicks queued at once, VIEWMD-0094's `_drain_paired_sgr_release` (unrelated pre-existing code, out of this issue's scope to touch) greedily drained the *second* click's own release bytes during the *first* click's drain call, leaving a stray release sequence that the next `_read_event` misparsed as a spurious `Event('key', '')` and an extra redraw -- fixed by feeding the test's input in timed chunks from a background thread instead (a test-harness fix, not a pager fix; documented in `_run_pager_with_input`'s own docstring). (2) The first version of the click-coordinate math for the acceptance test didn't add `_scrollbar_reserved()`'s column offset, so both scripted clicks silently missed the link and the test was passing for the wrong reason (never actually left document A) until frame-by-frame tracing caught it. (3) An off-by-one in the test's own frame-index arithmetic (miscounted the number of navigating clicks contributing to the running total). None of the three were bugs in the shipped `B`/`F` implementation itself -- all were in the new test's own harness/math -- but each would have made the acceptance test either fail confusingly or, worse, pass while testing the wrong thing.
  `./run-tests.sh`: pytest (1148 passed) and ruff (including security rules) both green. `issues --check` fails, but only on VIEWMD-0089/VIEWMD-0091 -- two unrelated issues already `status: in-progress` with a missing `effort:` field as of this worktree's own branch point (`2a5f298`, confirmed via `git log`), not touched by this diff and out of this issue's scope to fix.
