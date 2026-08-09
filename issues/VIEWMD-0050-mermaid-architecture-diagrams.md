---
id: VIEWMD-0050
title: Render Mermaid architecture diagrams
status: proposed
area: [render, mermaid]
effort: medium
created: 2026-08-09
updated: 2026-08-09
accepted_by:
accepted_at:
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Render Mermaid architecture diagrams

## Summary

Add a Mermaid diagram type -- `architecture-beta` -- alongside the existing flowchart, sequence,
and ER renderers (`viewmd/mermaid/{flowchart,sequence,er}/`) and the diagram types proposed in
[VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md) through
[VIEWMD-0042](VIEWMD-0042-mermaid-gitgraph-diagrams.md). A Mermaid architecture diagram
(https://mermaid.js.org/syntax/architecture.html) lays out services and groups on a 2D grid,
connected by edges declared with an explicit compass-direction hint at each end (`a:R --> L:b`),
rather than being auto-routed the way a flowchart's `A --> B` is.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `architecture-beta`
fence today -- it falls through every `_is_*_diagram` sniff. Notably, termaid's own implementation
(`src/termaid/__init__.py`) does not give architecture diagrams a
dedicated renderer at all: it parses `architecture-beta` into a small grid-position graph
(`src/termaid/parser/architecture.py`, `_compute_grid_positions`) and then hands that graph to the
*same* generic box/edge renderer (`output/text.py:render_text`) used for plain flowcharts. viewmd's
flowchart renderer (`viewmd/mermaid/flowchart/`) already draws boxes, subgraph-style groups, and
routed edges -- the new work here is mainly the direction-hinted grid-position parser, not a new
drawing engine.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `architecture-beta`
   (`viewmd/mermaid/architecture/parser.py:sniff`, following the `sniff`/`parse`/`render` module
   shape already used by the other diagram packages) and wire it into
   `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
2. MUST parse a `service <id>(<icon>)[<Label>]` declaration and an `in <group>` suffix assigning it
   to a previously-declared group.
3. MUST parse a `group <id>(<icon>)[<Label>]` declaration, including an `in <parent-group>` suffix
   for nested groups (a group inside another group).
4. MUST parse an edge line `<id>:<Dir> <arrow> <Dir>:<id>`, where each `<Dir>` is one of `L`/`R`/
   `T`/`B` (left/right/top/bottom) indicating which side of each box the edge attaches to, and
   `<arrow>` is `-->`/`--` (arrowhead present or absent at the target end, per requirement 5).
5. MUST compute each service/group's row/column grid position from the declared edge direction
   hints -- two services connected `a:R --> L:b` MUST be placed with `b` to the right of `a`;
   `a:B --> T:b` MUST place `b` below `a` -- generalizing across a chain of such hints into a
   consistent 2D grid (an id with no edges at all MAY be placed anywhere reasonable, e.g. appended
   to the grid).
6. MUST render each service as a labeled box; icon prefixes (the `(<icon>)` portion) are parsed
   (requirement 2/3) but rendering an actual glyph per icon name is left as an implementation
   choice -- a generic box is an acceptable v1 (see Non-goals).
7. MUST render each group as an outer labeled box containing its member services'/nested groups'
   boxes, reusing `viewmd/mermaid/flowchart/`'s existing subgraph-nesting box-drawing.
8. MUST render an edge as a routed line between the two boxes' specified sides, with an arrowhead
   at the target end only when the edge used `-->` (not `--`), reusing
   `viewmd/mermaid/flowchart/`'s existing edge-routing.
9. MUST leave an `architecture-beta` fence whose content fails to parse untouched (fall back to
   showing the raw fence), same fallback discipline as the other Mermaid renderers'
   MUST-NOT-crash requirement.
10. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- A per-icon-name glyph table (`cloud`, `server`, `database`, `disk`, etc. each rendering as a
  distinct emoji/symbol, as termaid does -- see reference example, where `(server)` and
  `(database)` render as `🖥`/`🗄`) -- requirement 6 only requires parsing the icon name, not
  drawing it distinctly; a follow-up issue can add a glyph table once this issue's grid-layout core
  lands, mirroring how VIEWMD-0022 added flowchart node shapes as a later, separate pass from the
  original flowchart renderer.
- Junction nodes (invisible routing-only points Mermaid's spec allows for bending an edge without a
  visible box) -- deferred to a follow-up issue.
- Edges with no direction hint at all on one or both ends (Mermaid allows omitting a `:Dir`, letting
  the renderer infer a side) -- requirement 4 requires both ends' hints to be explicit for v1.
- Matching any upstream reference implementation byte-for-byte -- the local `mermaid-ascii` Go
  oracle used for differential-testing flowchart/sequence/ER has no architecture-diagram support,
  so fixtures here are hand-authored/visually-verified, same posture as VIEWMD-0032 onward.
  termaid's own rendering (below) is a useful cross-check, not an oracle to match exactly.

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a
`_is_architecture_diagram`/`_parse_architecture`/`_render_architecture` import trio and a new `if`
branch, mirroring the `er` branch (parse-then-render, catching a module-local `ParseError` into
`MermaidError`). New module lives at `viewmd/mermaid/architecture/` (`parser.py`, `renderer.py`),
sibling to the other diagram packages. Per Motivation, this is the second gap diagram type (after
[VIEWMD-0044](VIEWMD-0044-mermaid-state-diagrams.md), state diagrams) that is graph-shaped enough
to plausibly translate straight into `viewmd/mermaid/flowchart/`'s internal box/group/edge
representation and reuse its renderer directly, rather than writing a new drawing engine -- the
grid-position algorithm (requirement 5) is the one genuinely new piece, and termaid's own
`_compute_grid_positions` (`src/termaid/parser/architecture.py`, exercised directly by
`tests/test_architecture.py:TestGridPositions`) is a reasonable model: walk the declared edges,
placing each new id relative to an already-placed neighbor per its direction hint, then resolve
column/row indices from the resulting relative-position graph.

### Reference example (termaid's actual output)

```
--- source ---
architecture-beta
    group cloud(cloud)[Cloud Infra]
    service web(server)[Web App] in cloud
    service db(database)[Data Store] in cloud
    web:R --> L:db
--- rendered ---
 ┌─────────────────────────────────────────┐
 │ Cloud Infra                             │
 │ ┌──────────────┐    ┌─────────────────┐ │
 │ │  🖥 Web App   ├───►│  🗄 Data Store   │ │
 │ └──────────────┘    └─────────────────┘ │
 └─────────────────────────────────────────┘
```

The `🖥`/`🗄` icon glyphs are out of this issue's scope (Non-goals) -- viewmd's v1 render of the
same source is expected to show plain labeled boxes (`Web App`, `Data Store`) inside the `Cloud
Infra` group box, connected left-to-right, without the icon prefixes.

## Acceptance / verification

- Unit tests for the parser: a `service`/`group` declaration with an icon and label, `in <group>`
  membership (including nested groups), an edge with each of the four direction-hint combinations
  (`R`-`L`, `B`-`T`, etc.), and the grid-position algorithm itself -- a left/right chain places
  ids in increasing column order, a top/bottom chain places ids in increasing row order, and a
  cross layout (one center id with neighbors on all four sides) places each neighbor on the correct
  side of the center, mirroring termaid's own `TestGridPositions` cases.
- A rendered fixture reproducing the `Cloud Infra`/`Web App`/`Data Store` example above (boxes,
  group nesting, and the routed edge; icon glyphs excluded per Non-goals), hand-verified (per
  Non-goals, no oracle to differential-test against; termaid's own output is a cross-check, not a
  target to match exactly).
- A rendered fixture for a nested group (a group declared `in` another group).
- A malformed `architecture-beta` fence (e.g. an edge referencing an undeclared service id) falls
  back to showing the raw fence rather than crashing viewmd.
- `./run-tests.sh` green.

## Peer review

