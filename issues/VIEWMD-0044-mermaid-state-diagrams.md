---
id: VIEWMD-0044
title: Render Mermaid state diagrams
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

# Render Mermaid state diagrams

## Summary

Add a Mermaid diagram type -- `stateDiagram-v2` -- alongside the existing flowchart, sequence, and
ER renderers (`viewmd/mermaid/{flowchart,sequence,er}/`) and the diagram types proposed in
[VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md) through
[VIEWMD-0042](VIEWMD-0042-mermaid-gitgraph-diagrams.md). A state diagram
(https://mermaid.js.org/syntax/stateDiagram.html) is a directed graph of named states connected by
labeled transitions, with special start/end pseudostates (`[*]`), choice pseudostates
(`state x <<choice>>`), and composite (nested) states. Structurally this is the closest of the
eight gap diagram types to what viewmd's flowchart renderer already does -- boxes connected by
routed edges, with a subgraph-like nesting case -- more than it is a new kind of chart.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `stateDiagram-v2`
fence today -- it falls through every `_is_*_diagram` sniff. State diagrams are one of Mermaid's
core diagram types and, unlike the diagram types proposed in VIEWMD-0043/0045-0050, reuse most of
`viewmd/mermaid/flowchart/`'s and `viewmd/mermaid/grid/canvas.py`'s existing box, edge-routing, and
subgraph machinery rather than needing a new layout engine -- the specific new vocabulary is just
the start/end/choice pseudostate glyphs and composite-state box nesting.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `stateDiagram-v2` (viewmd already treats
   the legacy `stateDiagram` keyword as out of scope -- see Non-goals) via
   `viewmd/mermaid/statediagram/parser.py:sniff`, following the `sniff`/`parse`/`render` module
   shape already used by the other diagram packages, and wire it into
   `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
2. MUST parse a plain transition line `A --> B` and an optional `: label` trailing it, rendering it
   as a labeled directed edge between two boxes, reusing `viewmd/mermaid/flowchart`'s edge-routing
   approach.
3. MUST parse the start pseudostate `[*] --> A` and end pseudostate `A --> [*]` and render each as
   its own small circular box: a filled bullet (`●`) inside a circle for start, a bullet inside a
   ringed circle (`◉`) for end -- per the reference example below.
4. MUST parse `state <name> <<choice>>` and render the named state as a diamond (reusing the
   flowchart diamond shape from `viewmd/mermaid/flowchart/`), with its outgoing transitions'
   labels rendered beside each branch, per the reference example below.
5. MUST parse a composite (nested) state block, `state "<Name>" { ... }` or `state <Name> { ... }`,
   containing its own transitions, and render it as an outer box labeled with the composite
   state's name, containing the nested states/transitions laid out inside it -- structurally the
   same nesting viewmd's flowchart subgraphs already support.
6. MUST render a plain named state as a rounded box with its name centered, matching the box style
   already used for flowchart rounded-rectangle nodes.
7. MUST leave a `stateDiagram-v2` fence whose content fails to parse untouched (fall back to
   showing the raw fence), same fallback discipline as the other Mermaid renderers'
   MUST-NOT-crash requirement.
8. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- The legacy `stateDiagram` keyword (pre-v2 syntax) -- only `stateDiagram-v2` is in scope, matching
  Mermaid's own current documentation emphasis.
- Fork/join pseudostates (`<<fork>>`, `<<join>>`) and concurrent (`--` divided) composite-state
  regions -- deferred to a follow-up issue; only `<<choice>>` (requirement 4) is in scope for v1.
- Notes (`note left of A: text`) and `%%{init}%%` theming.
- Composite states nested more than one level deep -- one level of `state "X" { ... }` nesting
  (requirement 5) is in scope; a composite state containing another composite state is deferred.
- Matching any upstream reference implementation byte-for-byte -- the local `mermaid-ascii` Go
  oracle used for differential-testing flowchart/sequence/ER has no state-diagram support, so
  fixtures here are hand-authored/visually-verified, same posture as VIEWMD-0032 onward. termaid's
  own rendering (below) is a useful cross-check, not an oracle to match exactly.

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a
`_is_state_diagram`/`_parse_state_diagram`/`_render_state_diagram` import trio and a new `if`
branch, mirroring the `er` branch (parse-then-render, catching a module-local `ParseError` into
`MermaidError`). New module lives at `viewmd/mermaid/statediagram/` (`parser.py`, `renderer.py`),
sibling to the other diagram packages. Because this diagram type is graph-shaped like a flowchart,
it's worth checking early whether `viewmd/mermaid/flowchart/`'s node-box, edge-routing, and
subgraph-nesting code can be called into directly (translating a parsed state diagram into the
flowchart package's internal graph representation) rather than reimplementing routing from
scratch -- this is the one gap diagram type where that kind of reuse looks plausible up front.

### Reference examples (termaid's actual output, `tests/fixtures/statediagram/`)

Plain transitions:

```
--- source ---
stateDiagram-v2
    State1 --> State2
    State2 --> State3
    State3 --> State1
--- rendered ---
╭──────────╮
│  State1  │◄─╮
╰─────┬────╯  │
      ▼       │
╭──────────╮  │
│  State2  │  │
╰─────┬────╯  │
      ▼       │
╭──────────╮  │
│  State3  ├──╯
╰──────────╯
```

Start/end pseudostates and a labeled transition:

```
--- source ---
stateDiagram-v2
    [*] --> Active
    Active --> Done : complete
    Done --> [*]
--- rendered ---
╭─────◯────╮
│    ●     │
╰─────◯────╯
      ▼
╭──────────╮
│  Active  │
╰─────┬────╯
      │complete
      ▼
╭──────────╮
│   Done   │
╰─────┬────╯
      ▼
╭─────◯────╮
│    ◉     │
╰─────◯────╯
```

Choice pseudostate (diamond, two labeled branches):

```
--- source ---
stateDiagram-v2
    state check <<choice>>
    [*] --> First
    First --> check
    check --> Second : yes
    check --> Third : no
--- rendered ---
╭─────◯────╮
│    ●     │
╰─────◯────╯
      ▼
╭──────────╮
│  First   │
╰─────┬────╯
      ▼
┌─────◇────┐
│  check   │
└─────◇────┘
      ├───────────────╮no
   yes│               │
      ▼               ▼
╭──────────╮    ╭──────────╮
│  Second  │    │  Third   │
╰──────────╯    ╰──────────╯
```

Composite (nested) state, containing its own internal transition, with an outer transition into
and out of it:

```
--- source ---
stateDiagram-v2
    [*] --> Running
    state "Running" {
        Idle --> Processing
        Processing --> Idle
    }
    Running --> [*]
--- rendered (abridged; blank lines trimmed for this reference) ---
                      ┌──────────────────────────────────────┐
                      │ Running                               │
╭───────◯──────╮      │ ╭──────────────╮    ╭──────────────╮ │
│      ●       │      │ │     Idle     ├◄──►┤  Processing  │ │
╰───────◯──────╯      │ ╰──────────────╯    ╰──────────────╯ │
        │             └──────────────────────────────────────┘
        ▼
╭──────────────╮
│   Running    │
╰───────┬──────╯
        ▼
╭───────◯──────╮
│      ◉       │
╰───────◯──────╯
```

Note termaid renders the composite's inner block as its own box (labeled `Running`) separate from
the outer `Running` state box that receives/sends the `[*]` transitions -- viewmd's own exact
layout choice here (e.g. whether the outer transition should attach directly to the composite box
rather than duplicating it) is left open for implementation, not dictated by this reference.

## Acceptance / verification

- Unit tests for the parser: plain transitions with and without a label, `[*] -->`/`--> [*]`
  pseudostates, `state <name> <<choice>>`, and a composite `state "X" { ... }` block containing its
  own transitions.
- A rendered fixture for each of the four reference examples above, hand-verified (per Non-goals,
  no oracle to differential-test against; termaid's own output is a cross-check, not a target to
  match exactly).
- A malformed `stateDiagram-v2` fence (e.g. an unclosed composite-state brace) falls back to
  showing the raw fence rather than crashing viewmd.
- `./run-tests.sh` green.

## Peer review

