---
id: VIEWMD-0025
title: Make flowchart A* routing actually minimize corners, not just bias toward them
status: proposed
area: [render, mermaid]
effort:
created: 2026-08-05
updated: 2026-08-05
accepted_by:
accepted_at:
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

VIEWMD-0015 (`issues/archive/VIEWMD-0015-mermaid-flowchart-diagrams.md` once archived) is the byte-for-byte baseline this diverges from, specifically `viewmd/mermaid/grid/astar.py`'s `find_path`/`heuristic`/`_GoHeap`. Note `_GoHeap` was hand-ported from Go's `container/heap` specifically to match upstream's tie-breaking exactly (VIEWMD-0015's peer review documents a real bug found and fixed there); changing the cost function here changes what counts as a "tie" in the first place, so re-verify `_GoHeap`'s behavior still holds once corner cost is part of `newCost`, not just `priority`.

## Acceptance / verification

- The `obstacle_routing` fixture (or its replacement) renders a genuinely simpler (fewer-corner) route than VIEWMD-0015's byte-for-byte-matched version, hand-verified (no upstream binary to diff against, since this is a deliberate divergence -- same testing posture as VIEWMD-0022/VIEWMD-0023).
- A regression fixture confirming a diagram with only one shortest path is unaffected (byte-identical to its VIEWMD-0015 rendering).
- All of VIEWMD-0015's other fixtures (the ones with only one shortest path per edge) still pass unchanged.
- `./run-tests.sh` green.

## Peer review

Left blank until implemented and tested; filled in as part of the Definition of Done landing gate.
