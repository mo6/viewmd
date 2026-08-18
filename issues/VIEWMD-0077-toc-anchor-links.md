---
id: VIEWMD-0077
title: Make the static table-of-contents block's entries clickable same-document anchor links
status: proposed
area: [render, pager]
effort: medium
created: 2026-08-17
updated: 2026-08-17
accepted_by:
accepted_at:
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

Directly follows [VIEWMD-0076](VIEWMD-0076-mouse-click-navigation.md), reusing its click-decoding (`_read_event`'s `click` event) and hit-testing (`_link_at`) as-is -- only the href-interpretation step is new. The scheme should follow `viewmd/wikilinks.py`'s own `wikilink:Target` precedent: something like `viewmd-toc:<n>` where `<n>` is the entry's position in `heading_outline()`'s own ordering, which both `viewmd/render.py`'s `_toc_lines()` (the static block) and `viewmd/interactive_pager.py`'s `_locate_headings()` (the popup) already independently derive from the same `heading_outline()` call -- worth double-checking the two stay in the same order (they should, both are a single top-to-bottom walk of the same outline), since a mismatch would silently jump to the wrong heading rather than erroring visibly.

`_toc_lines()` currently builds a plain `rich.text.Text` per entry (`viewmd/render.py:414-428`) with no href-carrying mechanism in play -- check how `viewmd/wikilinks.py`'s rewrite reaches Rich's own OSC8 emission (it goes through Markdown link syntax, not `Text` directly) to find the right way to attach a real href to a `Text` object instead, since the static ToC doesn't go through Markdown parsing at all.

## Acceptance / verification

- `./run-tests.sh` green, including: a test that the static ToC's rendered output carries an OSC8 link per entry pointing at the new scheme, with the *same* visible text/styling as before this issue (a byte-for-byte diff of everything except the OSC8 escape bytes themselves); a test that `_link_at` correctly decodes the new scheme from a rendered ToC row; a test that the interactive pager's click dispatch resolves the new scheme to the right heading's `top` and does *not* attempt file resolution against it.
- Manual check: the maintainer clicks an entry in a document's static (in-body) table of contents and confirms the view scrolls to that heading, the same as clicking the same heading's entry in the `t` popup already does.

## Peer review

