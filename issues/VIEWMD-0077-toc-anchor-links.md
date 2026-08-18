---
id: VIEWMD-0077
title: Make the static table-of-contents block's entries clickable same-document anchor links
status: in-progress
area: [render, pager]
effort: medium
created: 2026-08-17
updated: 2026-08-18
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-18
commits: []
related: [VIEWMD-0062, VIEWMD-0076]
supersedes: []
changelog:
reason:
---

# Make the static table-of-contents block's entries clickable same-document anchor links

## Summary

VIEWMD-0062's static table-of-contents block (the bulleted, heading-styled outline `render_markdown` prints at the top of a document when `toc=True`) is plain styled text today, not a real link -- clicking an entry in it does nothing. This issue wraps each entry in a real (but inert-outside-viewmd) OSC8 hyperlink pointing at its own heading, and teaches the interactive pager's click handler (VIEWMD-0076) to recognize that link scheme and scroll straight to the heading, the same way clicking an entry in the interactive ToC *popup* (`t`) already does.

## Motivation / problem

Flagged by the maintainer while verifying VIEWMD-0076: "should the links in the toc work too?" -- reasonable to expect, since the interactive ToC popup's entries are now click-to-jump (VIEWMD-0076 requirement 7) and the static ToC block looks similar (same bulleted, indented, heading-styled layout, `viewmd/render.py`'s `_toc_lines()`). But the two are unrelated pieces of code today: the popup is built fresh each time from `HeadingLoc` data inside `viewmd/interactive_pager.py`, while the static block is plain `rich.text.Text` with heading-color styling and no href at all (`_toc_lines()`, `viewmd/render.py:414-428`) -- there is currently nothing for a click to land on there, confirmed by inspecting the renderer while answering the maintainer's question, not a bug in VIEWMD-0076's own click hit-testing.

## Requirements

1. MUST wrap each static ToC entry's rendered text in an OSC8 hyperlink (the same mechanism `viewmd/wikilinks.py` already uses for `[[wikilinks]]`) whose target identifies the specific heading it represents.
2. MUST NOT change the static ToC block's visible appearance in any output mode -- same bullet, indentation, and `markdown.h1`/`h2`/`h3` heading-color styling as today; the OSC8 wrapper is a non-visual escape sequence around the existing styled text, not a restyle to ordinary link (underline/blue) appearance.
3. MUST, in the interactive pager, resolve a click landing on such a link to the heading it represents and scroll to it (`top = heading.row`), the same behavior a click on the corresponding interactive ToC popup entry already produces (VIEWMD-0076 requirement 7) -- reusing `_link_at` (VIEWMD-0076) for the hit-testing, extended to recognize this new link scheme distinctly from a `wikilink:`/relative-path href.
4. MUST NOT attempt local-file resolution (`_resolve_link_target`, VIEWMD-0076) against this new scheme -- it never identifies a file, only a position within the current document.
5. MUST NOT change non-interactive behavior (`--no-pager`, piped/redirected output) beyond the OSC8 escape bytes themselves being present in colored output -- a terminal that renders OSC8 links (most modern ones) may show its own hover/ctrl-click affordance for this scheme outside viewmd, same as it already can for an ordinary Markdown link or a `wikilink:`-scheme one; viewmd itself does nothing with it outside the interactive pager, matching how `wikilink:` is already "inert... never opened" per `viewmd/wikilinks.py`'s own docstring.
6. MUST NOT apply to `run_directory_listing()`/`run_multi_file()` -- neither has the single document's own heading outline this needs (matching VIEWMD-0072's existing "no per-entry/per-file ToC" scope for both).

## Non-goals

- Any cross-file anchor link (e.g. `[text](other.md#heading)` jumping straight to a heading in a *different* file after navigating to it) -- out of scope; this issue is same-document only, and doesn't touch VIEWMD-0076's cross-file link-follow at all.
- General heading-anchor support for ordinary Markdown links or `[[wikilinks]]` written by hand in document body text (e.g. GitHub-style `[text](#some-heading)`) -- a materially larger feature (parsing/matching arbitrary anchor fragments against arbitrary heading text) than this issue's narrow scope: only VIEWMD-0062's own machine-generated static ToC block gets this treatment.
- Any change to the interactive ToC *popup*'s own click-to-jump behavior -- that's already implemented (VIEWMD-0076) and unaffected by this issue.
- Keyboard navigation of the static ToC block (Tab between entries, Enter to follow) -- out of scope, matching VIEWMD-0076's own "pointer-driven only" Non-goal.

## Design notes / links

Directly follows [VIEWMD-0076](VIEWMD-0076-mouse-click-navigation.md), reusing its click-decoding (`_read_event`'s `click` event) and hit-testing (`_link_at`) as-is -- only the href-interpretation step is new.

**The scheme resolves by heading *text*, not position -- deliberately not the `viewmd-toc:<n>` index originally sketched here.** `viewmd/render.py`'s `_toc_lines()` (the static block) is fed a *fitted* outline: `_fit_toc_outline()` can drop an entire heading level (h3s, sometimes h2s too) or truncate to `_TOC_MAX_ENTRIES` when the real outline is large -- so the static block's own entry list is not reliably the same list, in the same order, as `viewmd/interactive_pager.py`'s `_locate_headings()` builds from the *unfitted* `heading_outline()` for the popup and heading-jump features. An index into the fitted list would silently misalign with the pager's full `headings` list exactly in the cases `_fit_toc_outline` exists to handle (a document with many/deep headings) -- confirmed by reading both call sites, not just assumed. The href instead carries the clicked heading's own text (URL-encoded, `viewmd-toc:<quoted text>`), matched against `headings` by exact text -- precisely what `_locate_headings()` itself already does internally to build `HeadingLoc.row` in the first place, so a match is guaranteed to exist for any entry the static ToC could have rendered.

`_toc_lines()` attaches the link via `Text.stylize(Style(link=href), start, end)` over just the heading-text span (not the bullet), layered as a *second* span on top of the existing `markdown.h{level}` one rather than folded into the same `append(..., style=...)` call -- `Style(link=...)` alone carries no color/weight, so Rich's per-character span-combining leaves the heading's visible SGR output completely unchanged (requirement 2), confirmed by rendering with and without the link and diffing (`strip_ansi(colored) == plain`, now one of this issue's own tests).

## Acceptance / verification

- `./run-tests.sh` green, including: a test that the static ToC's rendered output carries an OSC8 link per entry pointing at the new scheme (`test_toc_entries_are_osc8_links_to_their_own_heading`); a test that the visible text/styling is byte-for-byte unchanged from before this issue, once the OSC8 bytes are stripped (`test_toc_entries_visible_text_unchanged_by_the_link_wrapper`); a test that the scheme is absent when `toc=False`; a test that `_link_at` correctly decodes the new scheme from a real rendered ToC row (`test_link_at_decodes_a_toc_anchor_href`); a test that two headings sharing the exact same text get distinct, rank-disambiguated hrefs (`test_toc_duplicate_heading_text_gets_distinct_ranked_hrefs`, added after the first review pass found this was unhandled). The interactive pager's actual click-dispatch branch (resolving the scheme to a heading's `top`, not attempting file resolution) is not loop-driven-tested, matching VIEWMD-0076's own precedent (no harness in `tests/test_interactive_pager.py` drives `_run()`'s input loop for any key/click today) -- covered by the manual check below instead.
- Manual check: the maintainer clicks an entry in a document's static (in-body) table of contents and confirms the view scrolls to that heading, the same as clicking the same heading's entry in the `t` popup already does. **Done**, 2026-08-18, against `issues/archive/VIEWMD-0072-internal-pager-everywhere.md`'s own static ToC -- confirmed working live both before and after the first review pass's fix.

## Peer review

- **code-review skill** (agent, independent), 2026-08-18: Found two real issues in the initial implementation: (1) resolving a ToC-anchor click by heading text alone always jumps to the *first* heading with that text, so a document with two identically-named headings (e.g. `## Overview` under two different sections) would silently land on the wrong one when the second entry's link was clicked; (2) `_TOC_ANCHOR_SCHEME` was duplicated verbatim between `viewmd/render.py` and `viewmd/interactive_pager.py` instead of imported, risking a silent, hard-to-notice mismatch if the two ever drifted. Both fixed: the href now carries a 0-indexed occurrence rank alongside the text (`viewmd-toc:<rank>:<quoted text>`), computed against the *un-fitted* outline so it stays correct even when `_fit_toc_outline` drops/truncates entries (`_toc_occurrence_ranks()`, `viewmd/render.py`); `interactive_pager.py` now imports `_TOC_ANCHOR_SCHEME` from `viewmd.render` rather than redefining it. New regression test for the duplicate-text case; `./run-tests.sh` green after the fixes; maintainer re-verified click-to-jump live.
- **code-review skill** (agent, independent), 2026-08-18: Second pass, against the fixed diff. Found one more real bug: the click handler's `target_text = urllib.parse.unquote(quoted_text)` double-decoded the href's text portion -- `_link_at()` already fully unquotes the whole href before returning it, so a heading whose text happened to contain a literal `%`-looking substring (e.g. `%41`) would decode to the wrong string (`A` instead of `%41`) and silently fail to match any heading. Fixed by dropping the second `unquote()` call, matching the established convention `_resolve_link_target()` (for `wikilink:`) already follows in the same file. New regression test (`test_link_at_decodes_a_toc_anchor_href_with_a_percent_looking_heading`); `./run-tests.sh` green; maintainer re-verified click-to-jump live once more.
- **code-review skill** (agent, independent), 2026-08-18: Third pass, against the fully fixed diff. Traced the full data flow end to end (`heading_outline()` -> `_toc_occurrence_ranks()`/`_fit_toc_outline()` -> `_toc_lines()`'s href construction -> Rich's `Style(link=...)`/`stylize()` -> `_link_at()`'s single `unquote()` -> the click handler's rank-based resolution), confirmed the duplicate-heading-text and percent-looking-text fixes both hold, confirmed no other `_toc_lines()`/`_print_toc()` call sites were broken by the signature change, and confirmed no CLAUDE.md/AGENTS.md convention violations. No findings.
- **George Moses** (maintainer), 2026-08-18: Smoke-tested clicking a static-ToC entry (`issues/archive/VIEWMD-0072-internal-pager-everywhere.md`) after each of the three review passes -- confirmed working live each time, including after the duplicate-heading-text and double-unquote fixes.

