---
id: VIEWMD-0106
title: viewmd:mark region nested inside a single list item is silently unhighlighted
status: implemented
area: [render]
effort: medium
created: 2026-08-23
updated: 2026-08-23
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-23
commits: [4cacc31]
related: [VIEWMD-0104]
supersedes: []
changelog: "[1.51.1]"
reason:
---

# viewmd:mark region nested inside a single list item is silently unhighlighted

## Summary

VIEWMD-0104's mark-region matching only recognizes a region whose start/end sentinels sit between *top-level* document blocks. A region that instead brackets a single new item appended to an existing bullet/ordered list -- sentinels between two `list_item`s of the *same* list, not between two top-level blocks -- currently renders with no background tint at all, silently. This is not a contrived edge case: it is gitgleam's actual generated output for the extremely common "one new bullet added to an existing list" diff shape (a real file exhibiting it, reported by the maintainer, is preserved as this issue's fixture).

## Motivation / problem

`viewmd/render.py`'s `_group_top_level`/`_mark_line_ranges` (VIEWMD-0104) group `markdown.parsed` into whole top-level blocks -- a whole `bullet_list_open ... bullet_list_close` counts as *one* group, with no visibility into its own `list_item` children. A mark region whose sentinels sit between two list items therefore matches no group at all (the containing list's own group *starts* well before the region, at its first item, so the existing "group start line falls inside the region" membership test never fires) and is silently dropped -- no warning, no crash, just no highlight, discovered only by the maintainer noticing a marked file rendered with nothing tinted.

Two things make this non-trivial to just "also group list items":
1. A prefix of tokens that stops in the *middle* of a list (before its closing token) renders as **nothing at all** -- `ListElement`/`TableElement`-style container elements only emit their rendered content once their own closing token is reached (`on_child_close` absorbs children silently otherwise, verified empirically against this project's pinned rich version). The boundary-measurement technique `_mark_line_ranges` already uses (successive real single-print token *prefixes*, diffed for line count -- see that function's own docstring) therefore cannot use a bare `tokens[:cut]` slice for a cut point that falls inside a list; the slice must be reconstructed with the list's own closing token re-attached so the partial list actually renders.
2. This must still be exactly as safe as VIEWMD-0104's own careful reasoning about `Markdown.__rich_console__`'s single flat `new_line` state -- verified empirically (not assumed) that a reconstructed, properly-closed partial container measured via one continuous prefix render from token 0 matches how the real full document would render that same partial content.

## Requirements

1. MUST recognize a marked region whose sentinels sit between two `list_item`s of the same bullet or ordered list (immediately preceding content, or a fresh region wrapping only the newly-added trailing item(s)), tinting that item's rendered lines the same way a top-level marked block is tinted today (VIEWMD-0104 requirements 3-5).
2. MUST support this at arbitrary nesting depth, not just one level -- e.g. a region nested inside a list item that is itself inside a blockquote -- using the same general mechanism, not a list-item-only special case.
3. MUST NOT regress any existing VIEWMD-0104 top-level-block behavior; the existing test suite (`tests/test_highlight.py`) and `docs/mark-highlight-example.md` fixture must still pass/render identically.
4. MUST fail safe the same way VIEWMD-0104 requirement 10 already does: if no group at any nesting level fully contains a region's line span, the region is simply left untinted (matching today's fallback), not a crash.
5. The reconstructed-partial-container measurement technique MUST be verified empirically against a genuinely continuous full-document render of the same content (per the Motivation section above), not merely assumed correct by analogy to the top-level case.

## Non-goals

- Marking part of a single list item's own inline content (still whole-block granularity only, per VIEWMD-0104's own Non-goals).
- A region that starts inside one container and ends inside a *different* sibling container (still "regions are flat," per VIEWMD-0104's own Non-goals) -- only genuine nesting inside one enclosing chain is in scope.

## Design notes / links

- See VIEWMD-0104 (`issues/archive/VIEWMD-0104-highlight-marked-regions.md`) for the full design context this extends: the sentinel-stripping/preprocessing stage is unaffected by this issue, only the token-to-rendered-line matching in `viewmd/render.py`.
- Reproduction fixture: `docs/mark-highlight-example-list-item.md` (to be added as part of this issue, derived from the maintainer's real report).

## Acceptance / verification

- A new test in `tests/test_highlight.py` covering a region wrapping only the last item of an existing multi-item bullet list, asserting the tinted lines match exactly that item's own rendered lines and nothing else.
- A second test nesting one level deeper (e.g. inside a blockquote), confirming requirement 2's "arbitrary depth" claim isn't just a one-level special case.
- `./run-tests.sh` green, including the full existing `tests/test_highlight.py` suite unchanged.
- Manual render of the reported file (preserved as `docs/mark-highlight-example-list-item.md`) confirms the previously-unhighlighted third bullet now shows its `added` background tint.

## Peer review

- (agent, independent fresh review, no prior context) Verified the core recursion/reconstruction mechanism by hand against bullet-list and 2-level-nested-sub-list cases, and confirmed VIEWMD-0104's own top-level behavior is unchanged (`docs/mark-highlight-example.md` rendered output diffed against a pre-branch `develop` checkout). Found one MUST-fix correctness bug: `_is_recursable_container` treated `ordered_list_open` as safe to partially reconstruct, but rich's `ListElement.render_number` sizes its numbering column from the item *count present in that specific render*, not the document's true total -- a "closed early" partial-ordered-list reconstruction can pick a different column width than the real full-list render whenever the two item counts cross a digit-count boundary, silently mismeasuring and, worse than the already-guarded table/admonition case, capable of tinting the *wrong* item's lines rather than just failing to tint one. Reproduced concretely with a hand-built 12-item ordered list. Also flagged a dead link in the new fixture doc (pointed at the not-yet-created archive path) and asked for empirical re-verification of `_group_line_span`'s stated motivation (a claim about `list_item_open`'s `.map` not extending over further nested content) -- re-tested against the actual failing 2-level-nested-list construction in this issue's own test suite and confirmed the claim holds for that construction specifically (removing the full-scan and reverting to first-token-only `.map` reproduces the original bug), even though the reviewer's own narrower probes didn't happen to trigger it.
- Fixed: `_is_recursable_container` no longer treats ordered lists as safe (falls back to VIEWMD-0104 requirement 10's "no highlight" instead of a wrong one, same as the table-row case); the now-invalid "ordered list item is tinted" test was replaced with a regression test reproducing the reviewer's exact repro and asserting no wrong tint. Fixed the dead link in the fixture doc.
