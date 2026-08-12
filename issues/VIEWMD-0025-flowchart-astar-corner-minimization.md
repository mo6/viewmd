---
id: VIEWMD-0025
title: Make flowchart A* routing actually minimize corners, not just bias toward them
status: in-progress
area: [render, mermaid]
effort: medium
created: 2026-08-05
updated: 2026-08-12
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-12
commits: []
related: [VIEWMD-0015]
supersedes: []
changelog:
reason:
---

# Make flowchart A* routing actually minimize corners, not just bias toward them

## Summary

`viewmd/mermaid/grid/astar.py`'s `heuristic()` (ported from `cmd/arrow.go`, comment: "punish for taking extra corner, we prefer straight (less complex) lines") doesn't actually minimize the number of corners a routed edge takes. It only biases the priority queue's *search order* -- the real cost function charges exactly 1 per grid step regardless of direction, so every monotone path of the same Manhattan length is treated as equally optimal, and which one A* actually returns among several equal-length candidates is effectively decided by priority-queue tie-breaking, not corner count. This issue is to make corner count actually participate in what's being minimized, so routed edges look as simple as the underlying grid allows -- a deliberate improvement over upstream, not a byte-for-byte port.

## Motivation / problem

Confirmed directly against the real `mermaid-ascii` binary (not a viewmd-only artifact) with the VIEWMD-0015 `obstacle_routing` fixture: `A --> D` routes through 3 corners, weaving between `B` and `C`'s columns, even though a plain 1-corner route (right along the row above `B`/`C`, then straight down into `D`) is fully obstacle-free and exactly the same total step count -- verified by walking that alternate path against the same obstacle grid `A*` searches. Every extra corner makes a diagram harder to read for no routing-cost reason; this is a real, avoidable quality problem in nontrivial flowcharts (more nodes and edges only make more equal-length-but-different-shape candidate paths more likely, not less).

### Illustrating the problem

Instrumenting `Graph._determine_path` directly against the `obstacle_routing` fixture (`tests/fixtures/mermaid_flowchart/obstacle_routing.mmd`) gives the exact routed waypoints per edge, confirming the corner counts by construction rather than by eye:

```
A -> B  0 corners  [(1,2), (1,4)]
A -> C  1 corner   [(2,1), (5,1), (5,4)]
A -> D  3 corners  [(2,1), (4,1), (4,2), (9,2), (9,4)]
B -> D  4 corners  [(2,5), (3,5), (3,3), (7,3), (7,5), (8,5)]
C -> D  0 corners  [(6,5), (8,5)]
```

`A -> D` is the clearest case: same Manhattan distance (7 across, 3 down) as a 1-corner route would need, but the router returns a two-step staircase -- right, down, right, down -- instead. Today's actual rendered output (`./viewmd.sh` against the fixture):

```
┌───┐                
│ A ├───┬─┐          
└─┬─┘   └─┼───────┐  
  │       │       │  
  ▼   ┌───▼───┐   ▼  
┌───┐ │ ┌───┐ │ ┌───┐
│ B ├─┘ │ C ├─┴►│ D │
└───┘   └───┘   └───┘
```

Abstracted down to just the `A -> D` shape (obstacles/other edges omitted), current vs. the simpler shape this issue asks for -- same start, same end, same Manhattan length, fewer turns:

```
--- current (3 corners: right, down, right, down) ---
A──┐
   │
   └─────┐
         │
         D

--- target (1 corner: right, down) -- illustrative, not a pinned exact shape ---
A─────────┐
          │
          D
```

The target shape is illustrative of the *kind* of simplification expected (per requirement 2/Acceptance below, any equal-length route with strictly fewer corners than today's satisfies this issue -- the exact tie-break among multiple fewer-corner candidates is left to whatever `_GoHeap` produces once corner cost is real).

Maintainer-supplied reference (2026-08-12): Mermaid's own live-editor default layout for this exact `A/B/C/D` graph (free-form SVG curves, not a grid-locked router) independently confirms the same target -- every edge takes at most one gentle turn: `A -> B` and `C -> D` run straight, `A -> C` one turn, `A -> D` one turn (curving right around `C` rather than weaving through its column), `B -> D` one turn. viewmd's own router is grid-locked (orthogonal steps only, no free curves), so it cannot always reproduce that exact shape -- in particular `B -> D` shares a row with `C`'s box in viewmd's own node placement, which a free SVG curve can arc around but an orthogonal path must detour around with two turns, not one. Redrawn as a full diagram in viewmd's own box-drawing vocabulary (not upstream's shape/style -- see Non-goals), with every edge independently re-checked for turn count and column alignment:

```
--- current: 8 corners total (A->B 0, A->C 1, A->D 3, B->D 4, C->D 0) ---
┌───┐                
│ A ├───┬─┐          
└─┬─┘   └─┼───────┐  
  │       │       │  
  ▼   ┌───▼───┐   ▼  
┌───┐ │ ┌───┐ │ ┌───┐
│ B ├─┘ │ C ├─┴►│ D │
└───┘   └───┘   └───┘

--- target: 4 corners total (A->B 0, A->C 1, A->D 1, B->D 2, C->D 0) ---
┌───┐
│ A ├─────┬───────┐
└─┬─┘     │       │
  │       │       │
  ▼       ▼       ▼
┌───┐   ┌───┐   ┌───┐
│ B │   │ C │──►│ D │
└─┬─┘   └───┘   └─▲─┘
  │               │
  └───────────────┘
```

`A -> D` drops from 3 corners to 1 (right past `C`'s column at the same row `A -> C` already shares, then straight down into `D`'s top border -- matching the abstracted mockup above). `B -> D` drops from 4 corners to 2 (down from `B`, under both boxes, up into `D`'s bottom border) -- not the reference image's single curve (an orthogonal router genuinely cannot match a free-curve arc around an obstacle in the same row with only one turn), but still half today's corner count and no back-and-forth weave. `A -> B` and `C -> D` are already optimal today (0 corners) and stay that way. This full-diagram version is illustrative of the same "no weaving, every turn is load-bearing" target as the abstracted `A -> D`-only version above, not a byte-for-byte pinned fixture -- the exact shape the fixed router actually produces still depends on `_GoHeap`'s tie-breaking once corner cost is real (Acceptance below).

## Requirements

1. MUST change the cost function in `viewmd/mermaid/grid/astar.py`'s `find_path` (not just the heuristic) so a step that turns a corner costs more than a step continuing straight -- e.g. track the direction that reached each grid cell (threading it through `cost_so_far`/the priority-queue item alongside the coordinate, since a plain `GridCoord` no longer disambiguates "arrived here going straight" from "arrived here via a turn") and add a small penalty when the next step's direction differs from it.
2. MUST keep the search still admissible/correct -- the true-shortest-*Manhattan-distance* path must never be rejected in favor of a longer one just to save a corner; only tie-break among equal-Manhattan-length candidates in favor of fewer corners.
3. MUST NOT change output for any diagram where only one shortest path exists (the overwhelming majority of flowchart fixtures, including everything sparse enough to have an unambiguous route) -- this only changes behavior when multiple equal-length candidates exist.
4. MUST update the `obstacle_routing` fixture (and any other VIEWMD-0015 fixture whose rendered path shape changes) to the new, simpler routing, with the old byte-for-byte-matched-to-upstream version either replaced or kept as a `related`/superseded reference showing the before/after.

## Non-goals

- Fixing this upstream in `mermaid-ascii` itself -- tracked separately as a bug report for the maintainer to file (not a viewmd issue); see the suggested fix noted there (the same "fold corner cost into the real cost function" approach).
- The unrelated subgraph-border-overlap routing issue (VIEWMD-0023) -- different root cause (subgraph padding, not path selection), separate fix.
- Re-deriving VIEWMD-0022's node-shape/BT-RL-direction work -- unrelated, separate issue.

## Design notes / links

VIEWMD-0015 (`issues/archive/VIEWMD-0015-mermaid-flowchart-diagrams.md`) is the byte-for-byte baseline this diverges from, specifically `viewmd/mermaid/grid/astar.py`'s `find_path`/`heuristic`/`_GoHeap`. Note `_GoHeap` was hand-ported from Go's `container/heap` specifically to match upstream's tie-breaking exactly (VIEWMD-0015's peer review documents a real bug found and fixed there); changing the cost function here changes what counts as a "tie" in the first place, so re-verify `_GoHeap`'s behavior still holds once corner cost is part of `newCost`, not just `priority`.

## Acceptance / verification

- The `obstacle_routing` fixture (or its replacement) renders a genuinely simpler (fewer-corner) route than VIEWMD-0015's byte-for-byte-matched version, hand-verified (no upstream binary to diff against, since this is a deliberate divergence -- same testing posture as VIEWMD-0022/VIEWMD-0023).
- A regression fixture confirming a diagram with only one shortest path is unaffected (byte-identical to its VIEWMD-0015 rendering).
- All of VIEWMD-0015's other fixtures (the ones with only one shortest path per edge) still pass unchanged.
- `./run-tests.sh` green.

## Peer review

Left blank until implemented and tested; filled in as part of the Definition of Done landing gate.
