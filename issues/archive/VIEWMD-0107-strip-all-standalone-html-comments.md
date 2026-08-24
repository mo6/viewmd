---
id: VIEWMD-0107
title: Strip all standalone HTML comments, not just viewmd:mark sentinels
status: implemented
area: [render, docs]
effort: low
created: 2026-08-23
updated: 2026-08-24
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-23
commits: [d4ad8c6]
related: [VIEWMD-0104, VIEWMD-0106]
supersedes: []
changelog: "[1.52.0]"
reason:
---

# Strip all standalone HTML comments, not just viewmd:mark sentinels

## Summary

VIEWMD-0104 fixed the blank-line-doubling bug (`rich.markdown.Markdown` treating an unrecognized HTML comment as its own block element, with `MarkdownElement.new_line` defaulting `True`) only for `viewmd:mark` sentinel comments, deliberately leaving every *other* standalone HTML comment to "keep their current handling" (VIEWMD-0104 requirement 9) -- i.e. still doubled. This issue generalizes that fix: any HTML comment that sits alone on its own line (or spans several, per CommonMark's HTML-comment block rule) is now stripped from the Markdown source the same way, before Rich ever parses it, regardless of whether it's a `viewmd:mark` sentinel or not. Also documents the `viewmd:mark` feature in `README.md` (it currently has zero mention there) and records the VIEWMD-0104/VIEWMD-0106 implementation lessons in `AGENTS.md`.

## Motivation / problem

An author who leaves an ordinary editorial/TODO-style HTML comment on its own line in a Markdown file -- a common convention borrowed from HTML/git-diff-friendly authoring, invisible in every other Markdown renderer -- currently gets an extra blank line inserted on both sides of it when viewed through viewmd, purely because Rich has no built-in handling for that token type. VIEWMD-0104 already diagnosed and fixed the exact mechanism for `viewmd:mark` comments specifically; there's no reason the fix should stay scoped to that one comment shape when the same bug affects every other standalone HTML comment identically. Also raised alongside this: the `viewmd:mark` feature (VIEWMD-0104, VIEWMD-0106) shipped with no `README.md` mention at all, and the two issues' own hard-won implementation lessons (container-reconstruction hazards, `.map` limitations) are currently only recorded in the issues' own text, not in `AGENTS.md` where this project's house style says durable lessons belong.

## Requirements

1. MUST strip any standalone HTML comment (a comment block whose opening `<!--` starts a line, per CommonMark's HTML-comment block rule -- single-line or spanning multiple lines, ending at the first line containing `-->`) from the Markdown source at the same preprocessing stage `viewmd:mark` sentinels are already stripped at, so the surrounding blank-line spacing matches the comment having simply been deleted, exactly as VIEWMD-0104 requirement 8 already guarantees for marks specifically.
2. MUST continue to recognize and act on `viewmd:mark` sentinels exactly as today (VIEWMD-0104/VIEWMD-0106 requirements unchanged) -- this issue only widens which comments get *stripped*, not the mark-matching/highlighting logic itself.
3. MUST NOT strip an HTML comment that is not alone on its own line -- inline HTML inside a paragraph's running text (e.g. `text <!-- x --> more text`) is untouched, matching today's behavior (Rich already handles `html_inline` tokens differently from `html_block` ones, and the doubling bug is specific to the latter).
4. SHOULD document the `viewmd:mark` sentinel-highlighting feature in `README.md` (currently entirely undocumented there), including this issue's generalized comment-stripping.
5. SHOULD record the key implementation lessons from VIEWMD-0104/VIEWMD-0106 in `AGENTS.md`, matching this project's existing pattern of durable hard-won-lesson entries (see e.g. the VIEWMD-0092 embedded-RESET lesson, the VIEWMD-0015 heap/floor-division lesson): specifically, (a) that a Rich `MarkdownElement` container only renders once its own closing token is reached, so a token slice that stops mid-container renders as nothing, and a *reconstructed* partial container must be careful about any whole-container framing (a table's border, an admonition's header/footer, an ordered list's item-count-derived numbering width) that a genuine partial render would draw differently than the real thing; and (b) that a block token's own `.map` cannot always be trusted to cover everything nested inside it (`list_item_open` covers only its first child).

## Non-goals

- Changing what `viewmd:mark` recognizes as a valid sentinel, or how marked regions are highlighted -- purely about which *other* comments get stripped now.
- A configuration flag to opt out of comment-stripping -- an HTML comment is already invisible in every other Markdown renderer; viewmd rendering it as literal blank-line noise was the bug, not a feature someone would want to keep.
- Fixing blockquote-prefixed comments (a `>`-prefixed line containing a comment) -- `viewmd:mark` sentinels already have this same limitation (undocumented, discovered but out of scope during VIEWMD-0106), and this issue doesn't widen or narrow that.

## Design notes / links

- See `issues/archive/VIEWMD-0104-highlight-marked-regions.md` requirement 8's own reasoning for why stripping at the preprocessing stage (not suppressing an already-parsed unknown block element) is what fixes the spacing.
- See `issues/archive/VIEWMD-0106-mark-region-nested-inside-a-list-item.md` for the container-reconstruction/`.map` lessons requirement 5 above asks to fold into `AGENTS.md`.

## Acceptance / verification

- A new test asserting a plain, non-mark HTML comment (single-line, and a multi-line one) renders with the same single-blank-line spacing as the same document with that comment simply deleted, mirroring the existing VIEWMD-0104 blank-line-spacing test for marks.
- A test asserting an inline HTML comment inside a paragraph's own text is untouched.
- The full existing `tests/test_highlight.py` suite passes unchanged (`viewmd:mark` behavior itself is not touched).
- `README.md` includes a section documenting `viewmd:mark` sentinel highlighting and the generalized comment-stripping.
- `AGENTS.md` gains an entry (or entries) recording the container-reconstruction and `.map`-coverage lessons.
- `./run-tests.sh` green.

## Peer review

- (agent, independent fresh review, no prior context) Approved with nits after rendering single-line, multi-line, fenced, and inline-embedded comment cases directly (not just reading the code) and confirming `viewmd:mark` behavior is genuinely unaffected (full `tests/test_highlight.py` suite, and `docs/mark-highlight-example.md`/`docs/mark-highlight-example-list-item.md` rendered by eye). Found two must-fix items: a stale code comment in `viewmd/highlight.py` still describing pre-VIEWMD-0107 behavior (claimed a non-mark multi-line comment was "left to rich's generic HTML-comment handling," which this issue's own generic-stripping branch now contradicts), and the acceptance checklist's "single-line, and a multi-line" render-spacing test only actually covered the single-line case. Also suggested (nice-to-have) a warning for an unterminated standalone comment, for symmetry with the existing unbalanced-`viewmd:mark`-start warning, since silently dropping the rest of the document with no trace was less discoverable than the previous (pre-fix) garbled-rendering behavior. Confirmed README/AGENTS.md additions are accurate against actual code behavior and the referenced archived issues.
- Fixed: corrected the stale code comment; added the missing multi-line render-spacing test (`test_multi_line_comment_blank_line_spacing_matches_comment_simply_deleted`); added the unterminated-comment warning plus a regression test (`test_strip_marks_unterminated_comment_warns_and_drops_the_rest`).
- **George Moses** (maintainer), 2026-08-24: tested and accepted.
