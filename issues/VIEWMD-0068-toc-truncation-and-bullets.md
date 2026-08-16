---
id: VIEWMD-0068
title: Cap the ToC by truncating overflowing entries, and render it as a bulleted list
status: in-progress
area: [render]
effort: low
created: 2026-08-16
updated: 2026-08-16
accepted_by: George Moses
accepted_at: 2026-08-16
commits: []
related: [VIEWMD-0062]
supersedes: []
changelog:
reason:
---

# Cap the ToC by truncating overflowing entries, and render it as a bulleted list

## Summary

Two follow-up fixes to [VIEWMD-0062](VIEWMD-0062-table-of-contents.md)'s table of contents, both reported by the maintainer against `CHANGELOG.md`'s own real output: (1) `_fit_toc_outline`'s 20-entry cap only reduces the ToC by dropping to a shallower heading level (h1-h3 -> h1-h2 -> h1-only); for a flat document -- one `h1` title plus many `h2` sections and no `h3`s, exactly `CHANGELOG.md`'s shape -- every depth-reduction step is either a no-op or would empty the list entirely, so the existing "never render nothing" fallback shows every entry unbounded (`CHANGELOG.md` currently renders all 50). This issue makes the cap an actual entry-count limit: truncate to the first 20 entries in document order and append a trailing `... N more` note when depth-reduction alone couldn't get under the cap. (2) The ToC currently renders as bare indented, heading-styled text with no list marker at all, unlike every other bullet list viewmd renders (Rich's ` • ` marker); this issue adds that marker so the ToC reads as an actual list.

## Motivation / problem

Both gaps were found by the maintainer looking at `viewmd CHANGELOG.md`: a 50-line, unbounded ToC in front of a changelog entirely defeats the "quick outline" purpose VIEWMD-0062 was for, and the missing bullet made the ToC visually indistinguishable from an indented body paragraph rather than reading as a list of jump targets. Both are fixes to already-shipped VIEWMD-0062 behavior (`v1.29.0`), not new scope.

## Requirements

1. MUST cap the rendered ToC at exactly `_TOC_MAX_ENTRIES` (20) entries: after choosing the shallowest heading-level cut that still fits (VIEWMD-0062's existing h1-h3 -> h1-h2 -> h1-only stepping, unchanged), if the result *still* exceeds 20 entries, truncate to the first 20 in document order rather than showing all of them.
2. MUST append a trailing, non-heading-styled line after a truncated ToC reading `... N more` (`N` = the count of omitted entries), so the reader knows the outline was cut rather than assuming the document has no more headings.
3. MUST NOT add the `... N more` line when the ToC was not truncated (i.e. the chosen depth-level cut already fit within 20 entries) -- matching VIEWMD-0062's existing untruncated cases exactly.
4. MUST render each ToC entry as a bulleted list item, matching the marker and indentation-per-level Rich already uses for the body's own Markdown bullet lists (` • `), instead of today's bare indented heading-styled text with no marker.
5. MUST NOT change the heading-level styling (`markdown.h1`/`h2`/`h3`) already applied to each entry's text -- only the list marker/indentation mechanics change, not the text's own weight/color.
6. MUST NOT change any other VIEWMD-0062 behavior -- ToC placement (after front matter, before body), the `--toc`/`--no-toc` flag and `toc` config key, the "fewer than two headings -> no ToC" rule, and `h4`+ exclusion are all unaffected.

## Non-goals

- Changing `_TOC_MAX_ENTRIES` itself (still 20) -- this issue changes what happens *at* the cap, not the cap's value.
- A configurable truncation count or "show more" interaction -- v1's ToC stays a static, non-interactive outline (per VIEWMD-0062's own non-goals); truncation is a fixed `... N more` note, not a paged/expandable list. An interactive way to see the rest is squarely [VIEWMD-0007](VIEWMD-0007-link-navigation.md)'s future ToC popup, not this issue.
- Numbering ToC entries -- still out of scope, unchanged from VIEWMD-0062.

## Design notes / links

Both fixes are in `viewmd/render.py`. `_fit_toc_outline` (currently returns the deepest level whose entry count already fits, or the least-bad overflowing level if no shallower cut is possible) needs a final truncation step: if `len(selected) > _TOC_MAX_ENTRIES` after the existing level-stepping loop, slice to `selected[:_TOC_MAX_ENTRIES]` and have the caller (`_print_toc`) know how many were dropped so it can print the `... N more` line -- likely means `_fit_toc_outline` returning `(outline, omitted_count)` rather than just `outline`, or a second small helper. `_toc_lines`/`_print_toc` currently build each entry as `Text(_TOC_INDENT * (level - 1))` plus heading-styled text with no marker at all; adding a bullet marker before the indent-adjusted text is the minimal change, matching Rich's own list-rendering convention (` • ` glyph, deeper indentation per nesting level) used everywhere else viewmd renders a Markdown bullet list, rather than inventing a new marker style just for the ToC. Existing fixture/unit tests (`tests/test_render.py`, e.g. `test_toc_renders_under_the_leading_h1_without_repeating_it`, `test_toc_keeps_every_remaining_h1_even_past_20_entries`, `test_toc_keeps_overflowing_h3s_when_there_is_no_shallower_outline`) assert the current no-marker, no-truncation format and will need updating to match -- the latter two tests specifically assert the exact "keep everything, no truncation" behavior this issue replaces with truncation.

## Acceptance / verification

- `./run-tests.sh` green, including updated coverage for: a flat one-h1-plus-many-h2 document (matching `CHANGELOG.md`'s shape) truncating to 20 entries plus a `... N more` line (requirements 1-2), a ToC that already fits within 20 after depth-stepping showing no `... N more` line (requirement 3), every ToC entry carrying the same list marker/indentation as an equivalent body bullet list (requirement 4) while keeping its heading-level text styling (requirement 5), and every other VIEWMD-0062 behavior (placement, flag/config precedence, the two-heading-minimum rule, h4+ exclusion) unchanged (requirement 6).
- Manual check: `./viewmd.sh CHANGELOG.md --no-pager | head -25` and confirm the ToC now shows 20 bulleted entries followed by `... 30 more`, then compare against a shorter multi-level document (e.g. this project's own README.md) to confirm the bullet marker renders there too without truncation.

## Peer review

- **Independent review agent** (agent), 2026-08-16: pass-with-nits on `5e36e71` vs develop. MUST 1–6 hold; `./run-tests.sh -k toc` (27) green; `./viewmd.sh CHANGELOG.md --no-pager --color never --width 80` shows 20 bulleted h2s then `... 30 more`. Heading styles stay markdown.h1/h2/h3 without inheriting bullet bold. Nit: README still said remaining `#` headings are always kept past 20 — fixed before landing.
- **George Moses** (maintainer), 2026-08-16: "accept and close this" — approved to land.
