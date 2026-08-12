---
id: VIEWMD-0045
title: Render Mermaid mindmap diagrams
status: in-progress
area: [render, mermaid]
effort: high
created: 2026-08-09
updated: 2026-08-12
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-12
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Render Mermaid mindmap diagrams

## Summary

Add a Mermaid diagram type -- `mindmap` -- alongside the existing flowchart, sequence, and ER
renderers (`viewmd/mermaid/{flowchart,sequence,er}/`) and the diagram types proposed in
[VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md) through
[VIEWMD-0042](VIEWMD-0042-mermaid-gitgraph-diagrams.md). A Mermaid mindmap
(https://mermaid.js.org/syntax/mindmap.html) is an indentation-defined tree radiating from a root
node, conventionally drawn fanning out in multiple directions from the center rather than as a
top-down or left-right graph. This is a new layout shape none of viewmd's existing Mermaid
renderers produce today.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `mindmap` fence today
-- it falls through every `_is_*_diagram` sniff. Of the eight diagram types termaid supports that
viewmd does not yet track (state, architecture, pie, treemap, mindmap, quadrant, xychart, packet),
this is one of the largest in termaid's own implementation
(`src/termaid/{parser,renderer,model}/mindmap.py`, ~400 lines combined) because the tree-drawing
primitive -- branch connectors fanning left and right from a shared root, not a single direction --
doesn't exist anywhere in viewmd today; `viewmd/mermaid/flowchart/`'s routing always flows in one
overall direction (`LR`/`RL`/`TD`/`BT`).

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `mindmap` (`viewmd/mermaid/mindmap/parser.py:sniff`,
   following the `sniff`/`parse`/`render` module shape already used by the other diagram packages)
   and wire it into `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
2. MUST parse an indentation-based tree: the least-indented non-blank line after `mindmap` is the
   root, and each more-indented line that follows is a child of the nearest preceding line at a
   lesser indentation depth, recursively.
3. MUST strip Mermaid's node-shape markers from a label -- `(Round)`, `[Square]`, `((Circle))`,
   `{{Hexagon}}`, `)Cloud(` -- down to their bare text, matching Mermaid's own convention that
   these markers only select a visual shape, not literal characters in the label. (This issue does
   not require reproducing the different shapes themselves -- see Non-goals.)
4. MUST tolerate `%%` comment lines (stripped from end of a label line, per Mermaid's own inline
   comment convention) and blank lines anywhere in the block, ignored during parsing.
5. MUST render the root label as the visual center of the tree, with its direct children fanning
   out from it via branch connectors (`─╭─`/`─├─`/`─╰─` style corner-junction glyphs, matching the
   box-drawing vocabulary `viewmd/mermaid/grid/canvas.py` already uses elsewhere), each child's own
   subtree nested recursively to its right.
6. MUST distribute children across both sides of the root once a single-direction fan-out would
   grow too tall for the terminal to show legibly (mirroring termaid's own "overflow to the left"
   behavior below) -- the exact threshold is a design decision for this issue, not dictated by any
   fixed rule.
7. MUST leave a `mindmap` fence whose content fails to parse (or an empty `mindmap` block with no
   root) untouched (fall back to showing the raw fence, or an explicitly empty render for the
   truly-empty case), same fallback discipline as the other Mermaid renderers'
   MUST-NOT-crash requirement.
8. MUST parse Mermaid's markdown-string label formatting -- `**bold**` and `*italic*` spans within
   a node label (applied after shape-marker stripping, requirement 3) -- rendering them with real
   ANSI bold/italic (`--color`-independent; this is text styling, not color) rather than leaving
   the `*`/`**` markers as literal characters in the drawn label.
9. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- Reproducing each Mermaid shape marker (`(round)`, `[square]`, `((circle))`, `{{hexagon}}`,
  `)cloud(`) as a distinct drawn shape -- requirement 3 only requires stripping the markers down to
  plain text, matching flowchart/ER's existing posture of using one box style per diagram type
  rather than per-node shape variation within a tree.
- Icons (`::icon()`) and CSS classes (`:::classname`).
- The `tidy-tree` layout variant (a `%%{init}%%`-configured alternate global layout algorithm,
  not a drawing-vocabulary addition) and any other `%%{init}%%` mindmap config -- out of scope for
  this issue's single fan-out layout.
- An exact match to termaid's specific left/right balancing heuristic (requirement 6) -- only that
  overflow to a second side happens at some reasonable threshold, not termaid's precise algorithm.
- Matching any upstream reference implementation byte-for-byte -- the local `mermaid-ascii` Go
  oracle used for differential-testing flowchart/sequence/ER has no mindmap support, so fixtures
  here are hand-authored/visually-verified, same posture as VIEWMD-0032 onward. termaid's own
  rendering (below) is a useful cross-check, not an oracle to match exactly.

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a
`_is_mindmap_diagram`/`_parse_mindmap`/`_render_mindmap` import trio and a new `if` branch,
mirroring the `er` branch (parse-then-render, catching a module-local `ParseError` into
`MermaidError`). New module lives at `viewmd/mermaid/mindmap/` (`parser.py`, `renderer.py`),
sibling to the other diagram packages. This is the one gap diagram type most likely to need a
genuinely new drawing primitive rather than reuse of `viewmd/mermaid/grid/canvas.py`'s existing
box/edge vocabulary -- termaid's own `renderer/mindmap.py` (~295 lines, the largest single file
among its `renderer/` modules after `xychart.py`) computes per-subtree height recursively, then
assigns each node a row range and draws corner/branch connectors bridging a parent's row to its
children's row range; that recursive-height-then-connect approach is a reasonable starting point.

For requirement 8 (bold/italic labels), `viewmd/mermaid/grid/canvas.py` already has `wrap_text_bold`
and the combined `wrap_text_styled(text, *, fg=None, bg=None, bold=False, underline=False)` used by
other Mermaid renderers for ANSI-wrapping label text -- reuse that pattern rather than inventing a
new one. There is currently no italic SGR wrapper (`\x1b[3m`) anywhere in the codebase; add one
alongside the existing bold/underline wrappers in `canvas.py` rather than hand-rolling escape codes
at the mindmap call site.

### Reference examples (termaid's actual output)

```
--- source ---
mindmap
  Project
    Design
      Wireframes
      Mockups
    Development
      Frontend
      Backend
    Testing
--- rendered ---
          ╭─ Design ──╭─ Wireframes
          │           ╰─ Mockups
Project ──├─ Development ──╭─ Frontend
          │                ╰─ Backend
          ╰─ Testing
```

Overflow to a second side once a subtree grows tall (termaid's own threshold, from
`tests/test_mindmap.py:test_overflow_to_left` -- nine children of one root):

```
--- source ---
mindmap
  Center
    C0
    C1
    C2
    C3
    C4
    C5
    C6
    C7
    C8
--- rendered (abridged) ---
termaid spills roughly the second half of the children to the LEFT of "Center" instead of
stacking all nine to the right, using `┐`/`┘`/`┤`-style connectors on that side instead of
`╭`/`╰`/`├` -- the exact split point (and whether viewmd's own implementation should split at the
same count) is left open for this issue, not dictated by this reference.
```

## Acceptance / verification

- Unit tests for the parser: a simple flat tree, nested depth, a single root with no children, an
  empty `mindmap` block, each of the four shape-marker forms stripped to plain text (requirement
  3), and `%%` comments / blank lines ignored.
- A rendered fixture reproducing the `Project`/`Design`/`Development`/`Testing` example above,
  hand-verified (per Non-goals, no oracle to differential-test against; termaid's own output is a
  cross-check, not a target to match exactly).
- A rendered fixture exercising the two-sided overflow case (requirement 6) with enough children
  that a single-direction fan-out would clearly be too tall, confirming a second side is used at
  all (not confirming an exact split point, which Non-goals leaves open).
- A malformed `mindmap` fence and a truly-empty `mindmap` block (no root at all) both render
  without crashing viewmd, per requirement 7.
- A label containing `**bold**`, `*italic*`, and both combined renders with the corresponding ANSI
  SGR codes and no literal `*`/`**` markers left in the drawn text (requirement 8); a `color=False`
  render still applies the bold/italic escapes (they're text styling, not color) while carrying no
  color escapes, matching the other renderers' `color=False` posture.
- `./run-tests.sh` green.

## Peer review

- 2026-08-12 (agent): PASS — left-fan suffix fix and outer-column alignment test hold; nested-left/overflow/project fixtures and full gate look good against VIEWMD-0045.
- 2026-08-12 (George Moses): Accepted; commit and close.

