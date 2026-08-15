---
id: VIEWMD-0059
title: Render Obsidian/GitHub-style admonition callouts
status: implemented
area: [render]
effort: medium
created: 2026-08-15
updated: 2026-08-15
accepted_by: George Moses
accepted_at: 2026-08-15
commits: [e16cfa3]
related: []
supersedes: []
changelog: "[1.22.0]"
reason:
---

# Render Obsidian/GitHub-style admonition callouts

## Summary

Render a blockquote whose first line is an Obsidian/GitHub-style `[!TYPE]` marker (`> [!NOTE]`,
`> [!WARNING]`, ...) as a bordered, colored callout card with the type's icon and label in its top
border, instead of today's plain magenta `▌` bar with the literal `[!NOTE]` text leaking into the
body.

## Motivation / problem

`rich.markdown.BlockQuote.__rich_console__` (`rich/markdown.py:204-214`) renders every blockquote
identically: a `▌ ` padding segment per line, styled `markdown.block_quote` (magenta by default),
with no awareness of the `[!TYPE]` marker convention Obsidian and GitHub both use. Today:

```
> [!NOTE]
> This is a note callout.

--- rendered ---
 ▌ [!NOTE] This is a note callout.
```

The marker is indistinguishable from body text, and every blockquote -- callout or plain quote --
looks the same.

## Requirements

1. MUST detect a blockquote whose first line begins with `[!TYPE]` (case-insensitive `TYPE` token
   in brackets, e.g. `[!note]`/`[!NOTE]`/`[!Note]` all match) and treat it as an admonition rather
   than a plain blockquote.
2. MUST recognize GitHub's canonical alert types -- `NOTE`, `TIP`, `IMPORTANT`, `WARNING`,
   `CAUTION` -- each with its own icon and border/label color (see mockup below). Any other
   `[!TYPE]` (e.g. Obsidian-only aliases like `hint`/`success`/`question`) MUST still render as a
   generic callout card -- the literal `TYPE` text uppercased as the label, a neutral default
   color, no specific icon -- rather than falling back to a plain undecorated blockquote or being
   rejected.
3. MUST render as a bordered card (`╭─╮│╰─╯`), reusing the round-shape corner glyphs
   `viewmd/mermaid/grid/canvas.py:479-480` already defines for Mermaid nodes -- but not
   `draw_box`/`Drawing` themselves, which size a box against a fixed Mermaid diagram grid, not
   against a `Console`'s current wrap width; this needs its own `__rich_console__` render path
   that wraps prose the way `BlockQuote` already does.
4. MUST embed the type's icon and label in the card's top border (e.g.
   `╭─ 📝 NOTE ─────────────────╮`), per the mockup below.
5. MUST wrap the card body to the console's current render width and size the card's own border to
   fill that width (not to the body's natural content length) -- distinct from a Mermaid diagram
   box, which is sized to its own content.
6. MUST measure the header line's rendered width (icon + label + border fill) with `wcwidth`
   (`viewmd`'s existing display-width dependency, already used for Mermaid/table grid math), not
   Python's `len()`, so a double-width emoji icon doesn't desync the border alignment. The
   `WARNING` icon specifically needs hand-verification against this repo's actual terminal
   rendering before locking in a glyph: `⚠️` is a base warning-sign codepoint plus a U+FE0F
   variation selector, and several terminals render the pair one column wider than `wcwidth` alone
   reports for it -- the mockup below was hand-adjusted for exactly this during scoping.
7. MUST color the border, icon, and label per type, leaving body text styled the same
   (unstyled/default) way today's plain blockquote body already is.
8. MUST preserve multi-line/multi-paragraph body content inside the card, each paragraph reflowing
   independently the same way a plain blockquote's paragraphs already do.
9. MUST leave a plain blockquote (no `[!TYPE]` marker on its first line) rendering exactly as it
   does today, byte-for-byte unaffected.
10. MUST implement this as a `ViewmdBlockQuote` element override wired into
    `ViewmdMarkdown.elements` (`viewmd/render.py:53-58`), following the same pattern
    `ViewmdCodeBlock` already establishes for `fence`/`code_block`, rather than monkeypatching
    `rich.markdown.BlockQuote` directly.
11. MUST NOT crash on a marker-like but malformed first line (e.g. `[!]`, an unterminated
    bracket) -- fall back to today's plain-blockquote rendering.

## Non-goals

- Obsidian's collapsible/foldable callout syntax (`> [!NOTE]-` / `> [!NOTE]+`) -- foldability has
  no meaning in a one-shot terminal render.
- Custom user-themed callout types beyond the generic fallback (Obsidian lets a theme register
  arbitrary types with CSS-defined colors; viewmd has no equivalent styling layer to plug into).
- An ASCII-only fallback for the box-drawing glyphs -- no prose element has an ASCII rendering mode
  today (only Mermaid diagrams' `--ascii` flag does); adding one here, if ever wanted, is its own
  issue spanning more than just callouts.
- Nested admonitions (a callout inside another callout, inside a list item, or inside a table
  cell) -- top-level blockquote callouts only, matching every reference example below.

## Design notes / links

Mockup (Option B, agreed during scoping -- colors described in brackets since this is a plain-text
mockup; exact hex/ANSI values are an implementation decision):

```
--- source ---
> [!NOTE]
> This is a note callout. It has two lines.

> [!WARNING]
> This operation cannot be undone.

> [!TIP]
> Consider caching this if it's expensive to recompute.

> [!HINT]
> An Obsidian-only alias, not in GitHub's canonical set.

--- rendered ---
 ╭─ 📝 NOTE ───────────────────────────────────────────╮   [blue]
 │ This is a note callout. It has two lines.           │
 ╰─────────────────────────────────────────────────────╯

 ╭─ ⚠️  WARNING ────────────────────────────────────────╮   [amber]
 │ This operation cannot be undone.                    │
 ╰─────────────────────────────────────────────────────╯

 ╭─ 💡 TIP ────────────────────────────────────────────╮   [green]
 │ Consider caching this if it's expensive to          │
 │ recompute.                                          │
 ╰─────────────────────────────────────────────────────╯

 ╭─ HINT ──────────────────────────────────────────────╮   [neutral/default, generic fallback]
 │ An Obsidian-only alias, not in GitHub's canonical   │
 │ set.                                                │
 ╰─────────────────────────────────────────────────────╯
```

`IMPORTANT` and `CAUTION` (GitHub's remaining two canonical types) need their own icon/color pair
too, left as an implementation decision alongside the others -- not exercised in the mockup above
to keep it short, but in scope per requirement 2.

## Acceptance / verification

- Unit tests for the parser/detector: each of the five canonical types (case-insensitive marker
  matching), an unrecognized `[!TYPE]` falling back to the generic card, a malformed marker (e.g.
  `[!]`) falling back to a plain blockquote, and a plain blockquote with no marker at all rendering
  unchanged (regression guard for requirement 9).
- A unit test asserting the header border's total rendered width (via `wcwidth`) matches the body
  border's width for every canonical type's icon, catching the double-width-glyph misalignment
  requirement 6 exists to prevent.
- A rendered fixture per canonical type plus one generic-fallback type, hand-verified against the
  mockup above.
- A fixture confirming the card's border width matches the console's render width, and another
  confirming a multi-paragraph body reflows each paragraph independently inside the card.
- `./run-tests.sh` green.

## Peer review

- Claude (2026-08-15): two findings on Cursor's initial implementation, both fixed. (1) The
  WARNING header omitted the mockup's hand-adjusted double space before the label (requirement 6)
  -- `_AdmonitionKind` now carries a per-icon `icon_pad`, WARNING set to 2, with a regression test
  (`test_warning_header_uses_hand_adjusted_double_space`) and `warning.out` regenerated. (2) The
  new admonition examples had been added by editing the generated `docs/example.md` directly
  instead of a `tools/demo-pages/*.md` source page -- moved into new
  `tools/demo-pages/15-admonitions.md` and `docs/example.md` regenerated via
  `./tools/build_example_md.sh`. `./run-tests.sh` green after both fixes.
