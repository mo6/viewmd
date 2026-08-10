---
id: VIEWMD-0034
title: Render Mermaid kanban diagrams
status: proposed
area: [render, mermaid]
effort: medium
created: 2026-08-06
updated: 2026-08-06
accepted_by:
accepted_at:
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Render Mermaid kanban diagrams

## Summary

Add a sixth Mermaid diagram type -- `kanban` -- alongside the existing flowchart, sequence, ER, and (pending) gantt/journey renderers (`viewmd/mermaid/{flowchart,sequence,er}/`, [VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md), [VIEWMD-0033](VIEWMD-0033-mermaid-user-journey-diagrams.md)). A kanban diagram (https://mermaid.ai/open-source/syntax/kanban.html) is a set of ordered columns, each holding a stack of task cards; cards MAY carry structured metadata (`ticket`, `assigned`, `priority`) via `@{ ... }` shorthand. This is a first version -- see Non-goals for what's deliberately left out.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `kanban` fence today -- it falls through every `_is_*_diagram` sniff. A kanban board is a fundamentally different shape from every diagram type `viewmd/mermaid/` currently supports: side-by-side columns of stacked cards, not a graph, a date-scaled timeline, or a scored sequence -- closer in spirit to a nested-boxes layout than anything existing to extend.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `kanban` (`viewmd/mermaid/kanban/parser.py:sniff`, following the `sniff`/`parse`/`render` module shape already used by the other diagram packages) and wire it into `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
2. MUST parse a top-level column declaration, either bare (`Todo`) or bracketed with an id (`id9[Ready for deploy]`), in declaration order, and every indented card line under it until the next column or end of diagram.
3. MUST parse a card line, either bare-bracketed (`[Create Documentation]`) or id-prefixed (`docs[Create Blog...]`), as that column's next card in declaration order.
4. MUST parse a card's optional `@{ ... }` metadata block (comma-separated `key: value` pairs, value optionally single-quoted) recognizing `ticket`, `assigned`, and `priority` keys; an unrecognized key MUST be ignored rather than causing a parse failure (forward-compatible with metadata keys this issue doesn't render).
5. MUST NOT require unique card/column ids -- real Mermaid kanban input can reuse an id (e.g. the reference example below reuses `id3` across two different columns); this issue's parser must not treat that as a conflict.
6. MUST render each column as its own box (`┌─┐│└┘`) containing a header row (the column's label, centered) and its cards stacked vertically, each card its own nested box within the column's box, in declaration order -- see the mock-up below for the specific layout.
7. MUST word-wrap a card's label to a fixed content width inside its box (long, unbroken labels like the reference example's `id6` MUST wrap across multiple lines, not overflow or get truncated).
8. MUST render a card's metadata (where present) as one line under its label: `priority` (if present) as a short bracketed token (e.g. `[High]` → `[H]`, exact abbreviation scheme is a design decision for this issue) followed by `ticket` (if present) left-aligned, and `assigned` (if present) right-aligned on the same line.
8a. MUST render each column's header with a background color, one fixed hue per column in declaration order from the categorical palette `blue, orange, aqua, yellow, magenta, green, violet, red` (cycling past 8 columns), using 24-bit ANSI (`\x1b[48;2;r;g;bm`), with header text in a contrasting ink (light text on the darker/more saturated of these hues). This is the same categorical-hue-in-fixed-order convention `viewmd/mermaid/grid/canvas.py:wrap_text_in_color` already uses for `classDef` foreground fills in flowcharts, extended here to a background fill (see Design notes -- no background-color helper exists yet).
8b. MUST render a card's `priority` token (requirement 8) in a color keyed to severity, using a fixed 4-step mapping: `Very Low`/`Low` → the "good" status color, `Medium` → "warning", `High` → "serious", `Very High` → "critical" (see the mock-up's legend for exact hex). This mapping intentionally collapses `Very Low` and `Low` onto a single status step -- see open question (e).
8c. MUST render a card's `ticket` value, where present, underlined and in a distinct "link" hue, and its `assigned` value, where present, in a muted/secondary ink distinct from the card label's primary-ink text -- see the mock-up's legend for exact hex and rationale (assignee deliberately doesn't get its own saturated hue; see open question (f)).
9. MUST leave a `kanban` fence whose content fails to parse untouched (fall back to showing the raw fence), same fallback discipline as the other Mermaid renderers' MUST-NOT-crash requirement.
10. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- Respecting `--color never`/`NO_COLOR` for this issue's new coloring (requirements 8a-8c) -- `viewmd/mermaid/__init__.py:render` doesn't currently accept a color/no-color parameter at all, even for the existing flowchart `classDef` foreground coloring it already emits (`viewmd/render.py`'s `ViewmdCodeBlock.__rich_console__` passes a Mermaid-rendered fence's lines through as raw `Segment`s, so any ANSI escapes baked into that string bypass the `Console`'s own `no_color`/`color_system` settings entirely). This is a pre-existing gap across every Mermaid renderer, not something specific to kanban -- fixing it means threading a color flag through `viewmd/mermaid/render()` uniformly, which deserves its own issue rather than kanban inventing a one-off mechanism. Until then, this issue's coloring behaves the same (always on) as the flowchart coloring it sits beside.
- `ticketBaseUrl` / clickable ticket links (config-block-driven; there's no terminal hyperlink convention established elsewhere in `viewmd/mermaid/` to extend) -- the ticket ID still renders as plain text (requirement 8), just not as a link.
- The `---\nconfig:\n  kanban: ...\n---` YAML front-matter block the reference example opens with -- viewmd's Markdown-fence-level Mermaid support has no established config-block parsing convention today; a `kanban` fence that includes one should still render (ignoring the block), not fail to parse.
- Any interactivity, `click` handlers, or Mermaid's theming/`%%{init}%%` directives.
- Terminal-width responsiveness -- a six-column board (the reference example) is wide even in plain text; no reflow/wrap-columns-to-terminal-width behavior is in scope for v1, matching the other Mermaid renderers' current fixed-width posture.
- Matching any upstream reference implementation byte-for-byte -- there is no non-Mermaid reference renderer for this diagram type, so fixtures are necessarily hand-authored/visually-verified, same posture as VIEWMD-0022/0032/0033.

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a `_is_kanban_diagram`/`_parse_kanban`/`_render_kanban` import trio and a sixth `if` branch, mirroring the `er` branch (parse-then-render, catching a module-local `ParseError` into `MermaidError`). New module lives at `viewmd/mermaid/kanban/` (`parser.py`, `renderer.py`), sibling to the other diagram packages. Card-label word-wrapping (requirement 7) has no existing shared helper in `viewmd/mermaid/textutil.py` today (it currently only covers newline-splitting and comment-stripping) -- this issue would be the first Mermaid renderer needing multi-line label wrapping inside a fixed-width box, so a wrap helper added here is a reasonable candidate to land in `textutil.py` rather than being kanban-only, if a future issue needs the same behavior.

**Color values** (requirements 8a-8c) are the validated default palette from Anthropic's `dataviz` skill (`references/palette.md`), reused here rather than invented fresh: the 8-hue categorical order (`blue #2a78d6/#3987e5, orange #eb6834/#d95926, aqua #1baf7a/#199e70, yellow #eda100/#c98500, magenta #e87ba4/#d55181, green #008300/#008300, violet #4a3aa7/#9085e9, red #e34948/#e66767` -- light/dark) for column header backgrounds, and the fixed 4-step status palette (`good #0ca30c, warning #fab219, serious #ec835a, critical #d03b3b` -- same hex both modes) for the priority mapping in 8b, chosen over inventing a kanban-specific ramp since severity is exactly the "status" job that palette already covers. `viewmd/mermaid/grid/canvas.py:wrap_text_in_color` only wraps *foreground* truecolor (`\x1b[38;2;...m`) today; requirement 8a's column-header background needs a background counterpart (`\x1b[48;2;...m`) that doesn't exist yet -- a `wrap_text_in_bg_color` (or a `bg` parameter added to the existing function) is new work this issue introduces to `canvas.py`, not a pre-existing capability being reused.

### Mock-up (pending maintainer review)

Renders the maintainer-supplied reference example (config front-matter and `ticketBaseUrl` omitted from what's rendered, per Non-goals):

```
kanban
  Todo
    [Create Documentation]
    docs[Create Blog about the new diagram]
  [In progress]
    id6[Create renderer so that it works in all cases. We also add some extra text here for testing purposes. And some more just for the extra flare.]
  id9[Ready for deploy]
    id8[Design grammar]@{ assigned: 'knsv' }
  id10[Ready for test]
    id4[Create parsing tests]@{ ticket: MC-2038, assigned: 'K.Sveidqvist', priority: 'High' }
    id66[last item]@{ priority: 'Very Low', assigned: 'knsv' }
  id11[Done]
    id5[define getData]
    id2[Title of diagram is more than 100 chars when user duplicates diagram with 100 char]@{ ticket: MC-2036, priority: 'Very High'}
    id3[Update DB function]@{ ticket: MC-2037, assigned: knsv, priority: 'High' }
  id12[Can't reproduce]
    id3[Weird flickering in Firefox]
```

Modelled on real Mermaid's own rendering (the maintainer supplied a screenshot: colored column containers each with a header, colored nested card boxes, a colored left-edge stripe per card keyed to its `priority`, and ticket/assignee text at a card's bottom), with the maintainer's follow-up ask to actually color the priority/ticket/assignee fields and the column headers, not just distinguish them with text tokens. Adapted to box-drawing/ASCII: `┌─┐│└┘` throughout for both column and card boxes, a card's word-wrapped label first, then (if any metadata is present) one line below it with a `[H]`/`[VH]`/`[L]`/`[VL]` priority token, the ticket ID next to it, and the assignee right-aligned -- generated column-exactly (box widths, word-wrap, and metadata-line layout all computed from the data, not hand-aligned). **A plain-text `.md` issue file can't actually display ANSI color** (no terminal is interpreting the escape codes here, unlike the real rendered output this issue describes), so the diagram below stands in for the colored render two ways: each column header is annotated with the hue it would render as (`Todo — blue bg`, etc., per requirement 8a), and a legend beneath spells out exactly which hex renders which field (requirements 8b/8c) -- in the real rendered output neither annotation exists, the color itself carries that information:

```
┌──────────────────────────────────┐ ┌──────────────────────────────────┐ ┌──────────────────────────────────┐ ┌──────────────────────────────────┐ ┌──────────────────────────────────┐ ┌──────────────────────────────────┐
│          Todo — blue bg          │ │     In progress — orange bg      │ │    Ready for deploy — aqua bg    │ │    Ready for test — yellow bg    │ │        Done — magenta bg         │ │    Can't reproduce — green bg    │
├──────────────────────────────────┤ ├──────────────────────────────────┤ ├──────────────────────────────────┤ ├──────────────────────────────────┤ ├──────────────────────────────────┤ ├──────────────────────────────────┤
│  ┌────────────────────────────┐  │ │  ┌────────────────────────────┐  │ │  ┌────────────────────────────┐  │ │  ┌────────────────────────────┐  │ │  ┌────────────────────────────┐  │ │  ┌────────────────────────────┐  │
│  │ Create Documentation       │  │ │  │ Create renderer so that it │  │ │  │ Design grammar             │  │ │  │ Create parsing tests       │  │ │  │ define getData             │  │ │  │ Weird flickering in        │  │
│  └────────────────────────────┘  │ │  │ works in all cases. We     │  │ │  │                       knsv │  │ │  │ [H] MC-2038   K.Sveidqvist │  │ │  └────────────────────────────┘  │ │  │ Firefox                    │  │
│                                  │ │  │ also add some extra text   │  │ │  └────────────────────────────┘  │ │  └────────────────────────────┘  │ │                                  │ │  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │ │  │ here for testing purposes. │  │ │                                  │ │                                  │ │  ┌────────────────────────────┐  │ │                                  │
│  │ Create Blog about the new  │  │ │  │ And some more just for the │  │ └──────────────────────────────────┘ │  ┌────────────────────────────┐  │ │  │ Title of diagram is more   │  │ └──────────────────────────────────┘
│  │ diagram                    │  │ │  │ extra flare.               │  │                                      │  │ last item                  │  │ │  │ than 100 chars when user   │  │
│  └────────────────────────────┘  │ │  └────────────────────────────┘  │                                      │  │ [VL]                  knsv │  │ │  │ duplicates diagram with    │  │
│                                  │ │                                  │                                      │  └────────────────────────────┘  │ │  │ 100 char                   │  │
└──────────────────────────────────┘ └──────────────────────────────────┘                                      │                                  │ │  │ [VH] MC-2036               │  │
                                                                                                               └──────────────────────────────────┘ │  └────────────────────────────┘  │
                                                                                                                                                    │                                  │
                                                                                                                                                    │  ┌────────────────────────────┐  │
                                                                                                                                                    │  │ Update DB function         │  │
                                                                                                                                                    │  │ [H] MC-2037           knsv │  │
                                                                                                                                                    │  └────────────────────────────┘  │
                                                                                                                                                    │                                  │
                                                                                                                                                    └──────────────────────────────────┘
```

**Color legend** (what the header-tag annotations and the plain-looking metadata line above stand in for):

| Element | Color role | Hex (light / dark) | Style |
|---|---|---|---|
| Column header background, in declaration order | categorical slots 1-6 | blue `#2a78d6`/`#3987e5`, orange `#eb6834`/`#d95926`, aqua `#1baf7a`/`#199e70`, yellow `#eda100`/`#c98500`, magenta `#e87ba4`/`#d55181`, green `#008300`/`#008300` | background fill, contrasting header text |
| Priority `[VL]`/`[L]` | status "good" | `#0ca30c` | foreground |
| Priority `[H]` | status "serious" | `#ec835a` | foreground |
| Priority `[VH]` | status "critical" | `#d03b3b` | foreground |
| Priority `[M]` (not in this example; `Medium`, if present) | status "warning" | `#fab219` | foreground |
| `ticket` (e.g. `MC-2038`) | "link" hue | `#2a78d6`/`#3987e5` (categorical slot 1, reused) | foreground, underlined |
| `assigned` (e.g. `K.Sveidqvist`) | secondary ink | `#52514e`/`#c3c2b7` | foreground, no underline |

Open questions for maintainer sign-off: (a) whether uniform card width across every column (as above, all six columns the same width) is right, or whether each column should size to its own widest card/label independently -- uniform width keeps the grid tidy but wastes horizontal space on narrow columns like "Ready for deploy"; (b) the exact priority abbreviation scheme (`[H]`/`[VH]`/`[L]`/`[VL]` above) -- worth spelling out in full (`[High]`) instead, trading compactness for clarity; (c) whether a card missing every metadata field (no ticket/assigned/priority, e.g. `Create Documentation`) should keep the blank line's worth of vertical space the metadata line would have taken (for a uniform card height within a column) or omit it entirely as shown above (variable card height, matching the screenshot); (d) how the bottom-of-column blank padding row (visible above under each column's last card) should behave when columns end up wildly different heights, as in this example ("Todo"/"Can't reproduce" are short, "Done" is tall) -- pad every column to the tallest one's height (as shown) or let each column's box hug its own content; (e) whether collapsing `Very Low`/`Low` onto one status color (both render as "good") loses too much distinction, given the reference example actually uses `Very Low` -- the status palette only has 4 steps for 5 conventional priority levels, so *something* has to double up; (f) whether `assigned` should get its own saturated hue after all (the design here deliberately keeps it muted, on the principle that plain informational text shouldn't carry a series-style color when nothing is being compared against it) or whether the maintainer wants stronger visual pop for who's assigned.

## Acceptance / verification

- Unit tests for the parser: bare and id-prefixed column declarations, bare and id-prefixed card declarations, `@{ ... }` metadata parsing (all three recognized keys, an unrecognized key ignored, unquoted vs. single-quoted values), and duplicate ids across columns not raising.
- A rendered fixture (hand-verified, no upstream binary to diff against per Non-goals) reproducing the maintainer's reference example above per the mock-up.
- A fixture covering a card with no metadata at all, and one with each of the four priority levels.
- A fixture asserting the emitted ANSI escapes: column header background per requirement 8a (cycling the categorical palette past 8 columns), the priority-to-status-color mapping in 8b, and the ticket/assignee foreground+underline treatment in 8c.
- A fixture covering a `kanban` fence with a leading `---\nconfig:\n...\n---` front-matter block, confirming it's ignored rather than breaking the parse (Non-goals).
- A malformed `kanban` fence (e.g. a card line with an unterminated `@{` block) falls back to showing the raw fence rather than crashing viewmd.
- `./run-tests.sh` green.

## Peer review

