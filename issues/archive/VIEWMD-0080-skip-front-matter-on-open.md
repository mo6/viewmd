---
id: VIEWMD-0080
title: Interactive pager opens past front matter, not on it
status: implemented
area: [pager]
effort: low
created: 2026-08-18
updated: 2026-08-19
accepted_by: George Moses
accepted_at: 2026-08-19
commits: [9f3cbf7]
related: []
supersedes: []
changelog: "[1.41.0]"
reason:
---

# Interactive pager opens past front matter, not on it

## Summary

When the interactive pager (`viewmd/interactive_pager.py`, `run()`) opens a document that has a
front-matter block, the initial viewport should start at the first line of the document body (the
title/content just below the front-matter divider), not at line 0 (the front-matter table itself).
The front matter is still reachable by scrolling up from that starting position -- with the arrow
keys, page-up, or the mouse wheel, all of which are unaffected -- and jumping to "top" with the `g`
key lands on the same body-start position as the initial view, not on the front matter; scrolling
up past that point is how a reader reaches it.

## Motivation / problem

Front matter is metadata *about* the document (id, status, dates, tags), not the document's own
opening content. Landing on it first means every front-mattered file opens with the reader's first
screenful being a metadata table instead of the title/text they actually opened the file to read --
they have to scroll down past it before seeing anything else, every single time. Treating "top" as
"just after the front matter" instead of "line 0" matches how a reader actually thinks about the
document (the front matter is prefacing material, not the start) while still keeping it one scroll
away for anyone who wants it -- nothing about the front matter's content, rendering, or
`full_front_matter` handling changes, only where the pager's `top` starts and where `g` returns to.

## Requirements

1. MUST start the initial viewport (`top` in `_run()`, VIEWMD-0072's shared scrolling engine) at
   the first line of the document body -- immediately after the front-matter table's divider rule
   -- for any document `run()` opens that has a non-empty front-matter block, instead of `top = 0`.
2. MUST leave `top = 0` (today's behavior, unchanged) as the initial viewport for a document with
   no front matter, an unterminated `---` block, or a front-matter block that parses to no pairs --
   i.e. exactly the cases `render_markdown` already renders with no front-matter table at all
   (`split_front_matter`/`drop_empty`, `viewmd/render.py` around lines 513-522).
3. MUST make the `g`/`^` jump-to-top keybinding (`viewmd/interactive_pager.py` ~line 1275-1276)
   land on that same body-start row when front matter is present, not on line 0 -- "top" means the
   same row everywhere in the pager (initial view, `g`, and the `G`-then-`g` sequence), not two
   different rows depending on entry point.
4. MUST still allow scrolling up from the body-start row to view the front matter -- up arrow, page
   up, mouse wheel up, and manually typing a smaller row target via search/ToC jump all continue to
   reach rows 0..(body-start - 1) exactly as they do for any other row range; nothing clamps
   scrolling at the body-start row.
5. MUST NOT change mouse-wheel scrolling behavior in any other way -- it already scrolls freely
   across the whole document (VIEWMD-0075) and continues to do so, both above and below the
   body-start row.
6. MUST NOT change `render_markdown`'s output, the non-interactive (`--no-pager`/piped) rendering
   path, or the mode line's line-count/percentage math (`_mode_line`, `len(lines)` still counts
   every rendered line including the front matter) -- this is purely where the viewport starts and
   where `g` returns to, not a change to what content exists or how it's counted.
7. MUST recompute the body-start row on every reload that can change line wrapping (initial load,
   the `w` full-width toggle, a resize) the same way `max_top`/heading rows are already recomputed
   in those places, so it stays correct at the document's current render width.

## Non-goals

- `run_directory_listing()` and `run_multi_file()` -- a directory listing has no front matter, and
  a multi-file concatenation can have one front-matter block *per entry* (VIEWMD-0072), which is a
  materially different "where does the reader want to land" question; out of scope here, left at
  `top = 0` as today. A follow-up issue can revisit multi-file if wanted.
- Any new keybinding, config option, or flag to control this -- ship one fixed default; the
  front matter is one scroll away regardless, so this isn't a destructive or hard-to-notice change.
- Changing where `G` (jump to end) lands, or any other navigation target.

## Design notes / links

`render_markdown` (`viewmd/render.py` ~lines 513-525) already draws the line: `split_front_matter`
gives the raw front-matter text, `parse_front_matter`/`drop_empty` decide whether it renders at
all, and if it does, the table print is immediately followed by `console.print(Rule(characters="═",
style="dim"))` before the body's own tokens are printed. The body-start row is simply "how many
rendered lines did the front-matter table + that divider occupy" -- the same quantity `_load()`
(`viewmd/interactive_pager.py` ~line 175) would need to report alongside `colored`/`plain`/
`headings` if it's computed by re-running the front-matter-table-and-divider print in isolation at
the same `width`/`color_kwargs` and counting output lines, mirroring how `_locate_headings` already
derives `HeadingLoc.row` positions from the same rendered `plain` lines rather than from the source
markdown. Whatever the mechanism, it needs to hold for every place `top` is (re)computed at load
time: the initial `top = 0` at `_run()`'s top (~line 1097), the `g`/`^` handler (~line 1275-1276),
and the width-toggle/resize reload paths that already re-clamp `top` against a freshly computed
`max_top` (~lines 1304-1328, 1414, 1422).

## Acceptance / verification

- New unit test(s) (wherever `_run()`'s scrolling/`top` logic is already covered, or a sibling to
  the `_mode_line`/`_locate_headings` tests) covering: a document with front matter opens with
  `top` at the body-start row, not 0; a document with no (or empty/unterminated) front matter still
  opens at `top == 0`; `g`/`^` returns to the same body-start row, not 0, when front matter is
  present; scrolling up from the initial position reaches row 0 (the front-matter table) normally.
- Manual verification: `./viewmd.sh` a file with front matter (e.g. one of `issues/*.md` itself),
  confirm the pager opens on the title/body, scroll up with arrow keys and with the mouse wheel to
  confirm the front-matter table is reachable, press `g` from partway through the document and
  confirm it lands on the body-start row (not the front-matter table), and confirm a file with no
  front matter still opens at the very first line.
- `./run-tests.sh` green.

## Peer review

- **code-review agent** (agent), 2026-08-19: accepted. Initial viewport and `g`/`^` both go through `_home_top(body_start, max_top)`; `_home_top` is not a scroll floor, so up-arrow, page-up, and wheel still reach row 0. Directory-listing and multi-file loaders pass `body_start=0`. `render_markdown` output and `_mode_line` totals are unchanged; `body_start` is recomputed on `w` and on full-width resize; click-to-follow through `run()` uses the same home row. Tests cover the acceptance cases; no mermaid fixtures touched. No findings.
- **George Moses** (maintainer), 2026-08-19: accepted, approved to land.
