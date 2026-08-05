---
id: VIEWMD-0023
title: Reserve routing clearance for backward-flowing edges inside a flowchart subgraph
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

# Reserve routing clearance for backward-flowing edges inside a flowchart subgraph

## Summary

An edge that flows "backward" relative to a flowchart's overall direction (e.g. `DB --> Server` in a `graph LR` where `DB` was laid out to the right of `Server`) is routed out the bottom of both boxes. When both nodes sit inside a subgraph, that low horizontal segment lands on the same row as the subgraph's own bottom border and visually fuses with it -- the arrow appears to travel along, and its arrowhead appears to sit flush on, the subgraph's frame instead of inside it. VIEWMD-0015 reproduces this byte-for-byte from upstream (`docs/mermaid-examples.md`'s "Subgraphs with left-to-right layout" example demonstrates it deliberately, with a callout noting it's not a viewmd defect). This issue is to fix it in viewmd -- a deliberate, documented divergence from the upstream reference, not a byte-for-byte port.

## Motivation / problem

Root cause (confirmed against the real `mermaid-ascii` binary, not just viewmd's port): `cmd/direction.go`'s `determineStartAndEndDir` deliberately routes backward-flowing edges via each node's bottom side, to avoid threading back through whatever nodes sit between the two endpoints. That choice is reasonable on its own. But `calculateSubgraphBoundingBox`'s padding below the lowest node in a subgraph (`subgraphPadding = 2`, fixed) has no awareness of routed edge paths -- it doesn't know a backward edge is about to occupy a row just below the lowest node, so it doesn't reserve extra clearance the way `hasIncomingEdgeFromOutsideSubgraph`'s `subgraphOverhead` already does for a different case (an *incoming* edge crossing a subgraph boundary from outside). The result: the subgraph border and a backward edge's low segment can end up on the exact same row.

## Requirements

1. MUST detect, for each subgraph, whether any edge routed entirely or partly through it needs clearance below the subgraph's lowest node (the backward-flowing, bottom-attached case from `direction.go`'s `isBackwards` branches) before `calculate_subgraph_bounding_box` finalizes `min_y`/`max_y`.
2. MUST reserve enough additional vertical clearance in that case so the backward edge's horizontal segment and the subgraph's border render on distinct rows, with at least one blank row of separation (matching the visual clearance every other edge/border relationship in the renderer already gets).
3. MUST NOT change layout/output for diagrams with no backward-flowing edges inside a subgraph -- this is strictly additive clearance for the one case identified, not a general re-layout.
4. SHOULD apply the same fix to the equivalent `TD`/`BT`-direction backward-edge case (routed via each node's right side, per `direction.go`'s `TD`-mode backward branches), which has the same root cause on the perpendicular axis, even though no VIEWMD-0015 fixture currently demonstrates it -- confirm whether it needs a fixture added here.

## Non-goals

- Fixing this upstream in `mermaid-ascii` itself -- tracked separately as a bug report for the maintainer to file (not a viewmd issue); see the suggested fix noted there (computing subgraph padding from actual routed edge paths crossing the boundary).
- Any other routing-quality issue found during VIEWMD-0015 (e.g. the A* heuristic not actually minimizing corner count on equal-length paths) -- a distinct problem with its own tradeoffs, not part of this issue unless it turns out to share a fix.
- Re-deriving VIEWMD-0022's node-shape/BT-RL-direction work -- unrelated, separate issue.

## Design notes / links

VIEWMD-0015 (`issues/archive/VIEWMD-0015-mermaid-flowchart-diagrams.md` once archived) is the byte-for-byte baseline this diverges from, specifically at `viewmd/mermaid/flowchart/graph.py`'s `_calculate_subgraph_bounding_box`/`_has_incoming_edge_from_outside_subgraph` (the existing analogous overhead mechanism to extend) and `viewmd/mermaid/grid/coords.py`'s `determine_start_and_end_dir` (where the backward-edge bottom-attachment routing decision is made). `docs/mermaid-examples.md`'s "Subgraphs with left-to-right layout" example is the concrete repro to fix and re-verify.

## Acceptance / verification

- The `docs/mermaid-examples.md` repro fixture (`Frontend`/`Backend` subgraphs, `DB --> Server` backward edge) renders with a visible gap between the backward edge's line and the subgraph border, and the doc's callout about the overlap is removed/updated once fixed.
- A new fixture demonstrating the fix, hand-verified (no upstream binary to diff against, since this is a deliberate divergence -- same testing posture as VIEWMD-0022).
- All of VIEWMD-0015's existing byte-for-byte fixtures still pass unchanged (regression guard: this must only add clearance in the specific backward-edge-in-subgraph case, never touch other layouts).
- `./run-tests.sh` green.

## Peer review

Left blank until implemented and tested; filled in as part of the Definition of Done landing gate.
