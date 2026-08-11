---
id: VIEWMD-0042
title: Render Mermaid gitGraph diagrams
status: implemented
area: [render, mermaid]
effort: high
created: 2026-08-09
updated: 2026-08-11
accepted_by: George Moses
accepted_at: 2026-08-09
commits: [3e53818, eb05087, 4593579, 7ff1019]
related: []
supersedes: []
changelog: "[1.18.0]"
reason:
---

# Render Mermaid gitGraph diagrams

## Summary

Add an eighth Mermaid diagram type -- `gitGraph` -- alongside the existing flowchart, sequence,
ER, and (proposed) gantt/journey/kanban/timeline/block-beta/class renderers. A gitGraph
(https://mermaid.js.org/syntax/gitgraph.html) lays branches out as horizontal lanes and commits
as points along a shared left-to-right timeline, connected by vertical segments wherever a
`branch`, `checkout`, `merge`, or `cherry-pick` crosses lanes. This issue covers the **default
(left-right) orientation only** -- see Non-goals and the "TB orientation" design note below for
why `gitGraph TB:` is scoped out of v1.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `gitGraph` fence
today -- it falls through every `_is_*_diagram` sniff. Unlike a flowchart, a gitGraph's layout
isn't a routed graph search: lane assignment and timeline position both fall out directly from
replaying the `commit`/`branch`/`checkout`/`merge`/`cherry-pick` statements in source order, so it
needs its own parse/layout path but a much simpler one than flowchart's A* router -- closer in
spirit to sequence diagram's fixed lifelines (`viewmd/mermaid/sequence/`) than to flowchart's
edge-routing.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `gitGraph` (`viewmd/mermaid/gitgraph/parser.py:sniff`,
   following the `sniff`/`parse`/`render` module shape already used by the other diagram
   packages) and wire it into `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
2. MUST parse `commit id: "<id>"`, appending a commit to the current branch at the next timeline
   column. A bare `commit` with no `id:` attribute MUST also be accepted, auto-generating a random
   4-hex-digit id (re-rolled on collision against every id already assigned, explicit or
   generated) -- matching Mermaid's own behavior
   (https://mermaid.js.org/syntax/gitgraph.html), requested after the initial implementation
   (maintainer feedback, 2026-08-11).
3. MUST parse `branch <name>`, creating a new lane that starts at the current branch's current
   column and switches the current branch to `<name>`.
4. MUST parse `checkout <name>`, switching the current branch to an already-declared lane without
   adding a column.
5. MUST parse `merge <name> id: "<id>"` (and `merge <name>` with no explicit id), adding a commit
   to the current branch and drawing a vertical connector back to `<name>`'s lane at that column,
   per the second reference example below.
6. MUST parse `cherry-pick id: "<id>"`, adding a commit to the current branch that vertically
   connects to the source commit's lane and column, labeled `<id>-cherry`, per the first reference
   example below.
7. MUST parse an optional `tag: "<label>"` suffix on `commit`, rendering the tag in `[brackets]`
   on its own line above the commit, per the fourth reference example below.
8. MUST render one horizontal lane per branch, in order of first appearance (`main` always first),
   each lane prefixed with its branch name and drawn as `──●──` segments with commit ids centered
   beneath each `●`, per all four LR reference examples below.
9. MUST render a vertical connector (`│`, merging into `┼`/`├`/`┤` via the existing junction table
   in `viewmd/mermaid/grid/canvas.py` where it crosses a lane it doesn't terminate on) at the exact
   column a `branch`, `merge`, or `cherry-pick` occurs, spanning every lane row between the two
   branches it connects, per all four LR reference examples below.
10. MUST leave a `gitGraph` fence whose content fails to parse untouched (fall back to showing the
    raw fence), same fallback discipline as the other Mermaid renderers' MUST-NOT-crash
    requirement. This explicitly includes an orientation directive other than the implicit default
    (`gitGraph TB:`, `gitGraph BT:`, `gitGraph RL:`) -- treated as unsupported input for this
    issue, not silently re-rendered as LR (see Non-goals).
11. MUST NOT change behavior for any existing recognized Mermaid diagram type.
12. MUST tint each branch's name/dashes/markers with its own hue when the caller passes
    `color=True` (the same `--color` plumbing already read by the pie, quadrant, and gantt
    renderers), one categorical color per lane cycling past 8, reusing
    `viewmd/mermaid/kanban/renderer.py`'s `_CATEGORICAL` palette values (maintainer review
    feedback, 2026-08-11). Every commit's id label (and its `-cherry` suffix) MUST render in one
    shared neutral hue regardless of which lane it's on, distinct from every branch color, so ids
    read consistently across the whole diagram. Connectors (`│`/`┼`/`├`/`┤`) and `[tag]` markers
    stay uncolored -- shared/connecting elements, not owned by one lane, matching the gantt
    renderer's precedent (VIEWMD-0032 requirement 11) of leaving grid/axis infrastructure neutral.

## Non-goals

- **`gitGraph TB:` (or `BT:`/`RL:`) orientation.** See "Efficiency review of the supplied
  mockups" below -- a true top-to-bottom layout is a second rendering engine, not a transpose of
  the LR one, and is deferred to a follow-up issue built on top of this one's parser/event model.
- `commit type: REVERSE|HIGHLIGHT` and `commit tag:` combined with `type:` styling, branch
  colors/`%%{init}%%` theming -- no reference example uses them.
- `cherry-pick ... parent: "<id>"` (disambiguating which parent of a merge commit to pick).
- Terminal-width responsiveness/reflow -- fixed-width rendering, matching the other Mermaid
  renderers' current posture.
- Matching any upstream reference implementation byte-for-byte -- the local `mermaid-ascii` Go
  oracle used for differential testing the flowchart/sequence/ER ports has no `gitGraph` support
  at all, so fixtures here are necessarily hand-authored against the maintainer-supplied reference
  examples (same posture as VIEWMD-0032/0033/0034/0040).

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a `_is_gitgraph_diagram`/`_parse_gitgraph`/
`_render_gitgraph` import trio and an eighth `if` branch, mirroring the `sequence` branch
(parse-then-render, catching a module-local `ParseError` into `MermaidError`). New module lives at
`viewmd/mermaid/gitgraph/` (`parser.py`, `renderer.py`), sibling to the other diagram packages.

Parsing is a straight statement replay: track `{branch_name: (lane_row, current_column)}` plus a
`current_branch` pointer, incrementing a single shared timeline column counter on every `commit`/
`merge`/`cherry-pick`. Lane row assignment is first-appearance order (`main` implicitly exists at
row 0 before the first statement). This model needs no pathfinding -- reuse
`viewmd/mermaid/grid/canvas.py`'s `Drawing`/junction-merging for laying the fixed grid of lane rows
x timeline columns onto a character canvas, the same way `viewmd/mermaid/sequence/renderer.py`
uses it for fixed lifelines, rather than flowchart's A* router (`viewmd/mermaid/grid/astar.py`),
which this diagram type has no need for.

### Efficiency review of the supplied mockups

Four of the five supplied mockups (reference examples 1-4 below) share one layout model: branches
as fixed horizontal text rows, commits as fixed points along a shared column axis, vertical
connectors drawn as short spans between adjacent rows. That's a direct fit for the
canvas/junction-merging machinery already in `viewmd/mermaid/grid/canvas.py` (built for exactly
this "fixed lane, draw a connector where two lanes touch" shape in the sequence renderer) --
**medium** implementation cost on top of gitGraph's own parsing, consistent with this issue's
overall `high` estimate being driven by breadth of statement types (branch/checkout/merge/
cherry-pick/tag), not layout difficulty.

The fifth mockup (`gitGraph TB:`) is a different shape, not a 90-degree rotation of the same
drawing code: branch names become column headers instead of row prefixes, commits flow down text
rows within a column instead of across columns within a row, and the connector alphabet inverts
(horizontal `┼`/`─` spans within a single text row replace vertical `│` spans within a single text
column). Reusing the LR renderer's drawing calls for this would mean transposing every coordinate
by hand at each call site; reusing its *event model* (the branch/column bookkeeping above) is
sound, but the character-grid rendering pass itself would have to be written a second time with
its own row/column semantics -- effectively a second renderer, not a variant of the first. Shipping
it in the same issue as the LR work roughly doubles this issue's rendering-code surface for an
orientation Mermaid docs treat as the less common case (LR is the gitGraph default).

**More efficient design for v1:** scope this issue to LR only (requirement 10) and treat
`gitGraph TB:`/`BT:`/`RL:` as unsupported input that falls back to the raw fence, exactly like a
gitGraph fence with a syntax error -- consistent with how VIEWMD-0040 (block-beta) scopes out
shapes/features it doesn't yet support rather than half-implementing them. A follow-up issue can
add TB as its own renderer once this one's parser/event model exists to build on, at which point
its cost is bounded to the drawing pass alone (the design note above), not a from-scratch parser
too. The fifth mockup is kept below, relabeled as the follow-up's target output, so that reference
example isn't lost.

### Reference examples (maintainer-supplied, in scope for this issue -- LR/default orientation)

```
--- source ---
gitGraph
    commit id: "A"
    branch develop
    commit id: "B"
    checkout main
    cherry-pick id: "B"
--- rendered ---


  main    ──●─────┼──────●─
            A     │  B-cherry
                  │      │
  develop         ●──────┼
                  B
```

```
--- source ---
gitGraph
    commit id: "1"
    commit id: "2"
    branch develop
    commit id: "3"
    commit id: "4"
    checkout main
    commit id: "5"
    merge develop id: "6"
--- rendered ---


  main    ──●─────●─────┼───────────●─────●─
            1     2     │           5     6
                        │                 │
  develop               ●─────●───────────┼
                        3     4
```

```
--- source ---
gitGraph
    commit id: "init"
    commit id: "feat"
    commit id: "fix"
--- rendered ---


  main ───●─────●─────●─
        init  feat   fix
```

```
--- source ---
gitGraph
    commit id: "init" tag: "v0.1"
    commit id: "feat"
    commit id: "release" tag: "v1.0"
--- rendered ---

        [v0.1]         [v1.0]
  main ────●──────●───────●─
         init   feat   release
```

### Deferred to a follow-up issue (out of scope here -- see Non-goals)

```
--- source ---
gitGraph TB:
    commit id: "1"
    branch develop
    commit id: "2"
    checkout main
    commit id: "3"
    merge develop
--- rendered ---


main      develop
  │
  ●
  1
  │
  ┼──────────●
  │          2
  │          │
  ●          │
  3          │
  │          │
  ●──────────┼
  0
```

## Acceptance / verification

- Unit tests for the parser: `commit id:`, bare `commit` (auto-generated 4-hex-char id, unique
  across other explicit/generated ids), `branch`, `checkout`, `merge` (with and without an explicit
  `id:`), `cherry-pick id:`, and `tag:` -- including a `cherry-pick`/`merge` referencing a commit id
  on a lane other than the current one.
- A rendered fixture for each of the four LR reference examples above, hand-verified against the
  maintainer-supplied output (per Non-goals, no oracle to differential-test against).
- A `gitGraph TB:` (or `BT:`/`RL:`) fence falls back to showing the raw fence rather than crashing
  or silently rendering as LR.
- A malformed `gitGraph` fence (e.g. `merge`/`cherry-pick` referencing an undeclared branch or
  commit id) falls back to showing the raw fence rather than crashing viewmd.
- Tests for requirement 12: no ANSI when `color=False` (the default); stripping ANSI from a
  `color=True` render reproduces the `color=False` render exactly; two different branches carry
  two different hues; every commit id label across every branch shares exactly one hue; a `[tag]`
  line and a connector line stay uncolored.
- `./run-tests.sh` green.

## Peer review

- (agent, independent `code-review` pass) Traced the parser/renderer by hand against all four reference examples (all match) and probed edge cases outside the fixture set; found that `merge <name> id: "<id>"` didn't check its id against the same `commit_owner` duplicate table plain `commit` does, so a merge id colliding with an earlier commit id silently overwrote the id -> lane mapping a later cross-lane `cherry-pick` relies on -- fixed in `viewmd/mermaid/gitgraph/parser.py` (now raises `ParseError` on collision, matching `commit`'s existing check) with a regression test added. Also flagged that a `branch` statement immediately superseded by another `branch` before ever receiving a commit leaves its `pending_parent_row` unresolved and draws no connector for that (commit-less) lane; on inspection this isn't a defect against any requirement -- a lane with zero commits has nothing to connect, and rendering confirms it degrades gracefully (no crash, no misleading marks) -- so left as-is.
- George Moses (maintainer), 2026-08-11: reviewed and tested the coloring pass (requirement 12: per-branch hues from the same categorical palette as kanban, one shared neutral hue for every commit id, connectors/tags left uncolored) and the bare-`commit`-with-auto-generated-id follow-up (requirement 2 update). Approved to land.
