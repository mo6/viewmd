---
id: VIEWMD-0058
title: Render GFM task list checkboxes
status: in-progress
area: [render]
effort: low
created: 2026-08-15
updated: 2026-08-15
accepted_by: George Moses
accepted_at: 2026-08-15
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Render GFM task list checkboxes

## Summary

Render a GitHub-flavored-Markdown task list item (`- [x] label` / `- [ ] label`) with a checkbox
glyph in place of the plain bullet, instead of today's fallthrough where the literal `[x]`/`[ ]`
text is shown after an ordinary bullet.

## Motivation / problem

`rich.markdown.Markdown` (`viewmd/render.py`'s base class) builds its parser as
`MarkdownIt().enable("strikethrough").enable("table")` (`rich/markdown.py:559`) -- plain
CommonMark plus two GFM extras, with no task-list rule enabled and no `mdit_py_plugins` dependency
pulled in. A list item's content is therefore just ordinary text starting with the literal
characters `[x] ` or `[ ] `, and `ListItem.render_bullet` (`rich/markdown.py:378-390`) renders it
exactly like any other bullet item:

```
 • [x] Write the draft
 • [x] Review it
 • [ ] Publish
```

There is no visual distinction between a done and a not-done item, and the raw `[x]`/`[ ]` syntax
leaks into the rendered output as text.

## Requirements

1. MUST detect a bullet-list item whose rendered text content begins with `[ ]`, `[x]`, or `[X]`
   followed by a space, and treat it as a task item rather than a plain bullet item.
2. MUST render a checked task item's marker as `✅` and an unchecked task item's marker as `⬜` in
   place of the default `•` bullet (`rich/markdown.py:383`'s `Segment(" • ", bullet_style)`), with
   the literal `[x]`/`[ ]`/`[X]` marker text stripped from the visible label.
3. MUST NOT crash on a task-marker-like string that isn't cleanly one of `[ ]`/`[x]`/`[X]` (e.g. a
   literal `[y]` in prose that happens to start a list item) -- fall back to rendering it as plain
   list-item text, the current behavior, rather than misdetecting it as a task item.
4. MUST render a checked item's label text dimmed and struck through (`rich`'s `strike=True` style
   combined with a dim style), leaving an unchecked item's label unstyled, matching the mockup
   agreed during scoping.
5. MUST leave a plain (non-task) list item's rendering completely unchanged.
6. MUST NOT add a new runtime dependency (e.g. `mdit_py_plugins`'s task-list plugin) -- detect the
   checkbox marker from the plain text `rich.markdown.Markdown` already parses, consistent with
   `AGENTS.md`'s frugal dependency posture (`rich`/`wcwidth` only).
7. MUST implement this as a `ViewmdListItem` element override wired into `ViewmdMarkdown.elements`
   (`viewmd/render.py:53-58`), following the same override pattern `ViewmdCodeBlock` already
   establishes for `fence`/`code_block`, rather than monkeypatching `rich.markdown.ListItem`
   directly.

## Non-goals

- Interactive/clickable checkboxes -- not meaningful in a static terminal pager render.
- Task items nested inside ordered lists, blockquotes, or table cells -- plain bullet-list task
  items only, matching every reference example.
- Any change to `color=never`/`--color=never` behavior beyond what `rich` already does when
  stripping styles -- the dim/strikethrough styling should degrade the same way any other styled
  text in the renderer already does under `no_color`.

## Design notes / links

Mockup (Unicode, agreed during scoping):

```
--- source ---
- [x] Write the draft
- [x] Review it
- [ ] Publish

--- rendered ---
 ✅ Write the draft   (dimmed + struck through)
 ✅ Review it         (dimmed + struck through)
 ⬜ Publish
```

Two alternate glyph pairs were considered and rejected in favor of the above: `☑`/`☐` (too small
at typical terminal font sizes) and `[✔]`/`[ ]` (closer to the ANSI-only aesthetic used elsewhere
in the renderer, but less visually distinct than the emoji pair, which won out).

## Acceptance / verification

- A unit test rendering the mockup's three-item list and asserting (via `strip_ansi`, matching
  `tests/test_render.py`'s existing convention) that `✅` appears twice, `⬜` appears once, and the
  literal `[x]`/`[ ]` text does not appear in the output.
- A unit test asserting the checked items' rendered ANSI includes a strike-through/dim style
  sequence (matching `tests/test_render.py:test_...`'s existing `ANSI_RE`-based style assertions)
  and the unchecked item's does not.
- A unit test confirming a plain (non-task) bullet list's rendering is byte-identical to today's
  output (regression guard for requirement 5).
- `./run-tests.sh` green.

## Peer review

- **Independent review agent** (agent), 2026-08-15: approve-with-nits. Requirements 1–7 met: `ViewmdListItem` elements override, no new dependency, `✅`/`⬜` replace `•`, markers stripped, checked labels are SGR `2;9`, plain-bullet golden matches pre-change `a3fd6db`. The three named acceptance tests exist and check what they claim. Nits (non-blocking): glyph test does not assert `•` is gone; no ordered-list `1. [x]` regression test (`render_number` is untouched); a checked item's later paragraphs in a loose list are not dimmed/struck. Ordered lists and table cells stay literal, matching the non-goals.
- **George Moses** (maintainer), 2026-08-15: "merge and close issue" — approved for landing.
