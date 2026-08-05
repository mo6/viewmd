---
id: VIEWMD-0027
title: Implement true BT/RL direction reversal in Mermaid flowcharts
status: proposed
area: [render, mermaid]
effort:
created: 2026-08-05
updated: 2026-08-05
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0015, VIEWMD-0022]
supersedes: []
changelog:
reason:
---

# Implement true BT/RL direction reversal in Mermaid flowcharts

## Summary

VIEWMD-0015 ported flowchart rendering byte-for-byte against `github.com/AlexanderGrooff/mermaid-ascii`, which accepts `BT` (bottom-to-top) and `RL` (right-to-left) as valid direction syntax but aliases them internally to `TD`/`LR` -- drawing the exact same top-to-bottom/left-to-right layout regardless. This issue is to implement true reversal for both, now that the flowchart engine (`viewmd/mermaid/grid/`, `viewmd/mermaid/flowchart/`) exists to build on. (Split out from [VIEWMD-0022](VIEWMD-0022-flowchart-shape-and-direction-support.md), which originally scoped this alongside node-shape support -- same limitation category, unrelated fix.)

## Motivation / problem

Confirmed against the real `mermaid-ascii` binary (not a viewmd-only artifact): a `graph RL` diagram with `A --> B --> C` renders identically to the equivalent `graph LR` diagram -- arrows still point left-to-right. The maintainer expects, and real Mermaid renders, the layout genuinely mirrored: for `RL`, `C` on the left, `A` on the right, arrows pointing right-to-left (`A --> B --> C` still means "A points to B points to C", just laid out with the flow direction visually reversed). `BT` has the same problem on the vertical axis. Silently drawing the un-reversed direction produces a diagram the user didn't ask for, with no indication anything was ignored.

## Requirements

1. MUST implement true `RL` (right-to-left) layout: reverse the horizontal placement order `create_mapping` currently uses for `LR` (root nodes/levels growing left-to-right) so they grow right-to-left instead, with arrowheads/edge routing following.
2. MUST implement true `BT` (bottom-to-top) layout: same reversal on the vertical axis relative to `TD`.
3. MUST keep edge routing (`viewmd/mermaid/grid/astar.py`, `viewmd/mermaid/flowchart/graph.py`'s `_determine_path`/`determine_start_and_end_dir`) correct under the reversed axis -- attachment-side heuristics currently assume growth in the `TD`/`LR` direction and need to account for the flip, not just the leveling/placement step.
4. MUST NOT change the byte-for-byte-matched behavior for `TD`/`LR` diagrams -- this issue only changes what `BT`/`RL` do, it doesn't touch VIEWMD-0015's verified baseline.
5. MUST leave a flowchart fence untouched (no crash) if reversal can't be computed for some diagram shape not yet handled, same fallback discipline as VIEWMD-0015 requirement 6.

## Non-goals

- Node shape rendering (`()`, `{}`, etc.) -- tracked separately as [VIEWMD-0022](VIEWMD-0022-flowchart-shape-and-direction-support.md).
- Matching any upstream reference byte-for-byte for `BT`/`RL` output -- there is none, since `mermaid-ascii` doesn't implement real reversal either. Fixtures for this issue are necessarily hand-authored/visually-verified, unlike VIEWMD-0014/0015/0016's differential-tested ones.
- Subgraph placement heuristics beyond what's needed for `BT`/`RL` to render correctly on diagrams that already have subgraph fixtures in VIEWMD-0015 (e.g. `graph.py`'s LR-specific `should_separate` external/subgraph-root-splitting logic) -- adapt only as far as required, don't redesign subgraph layout wholesale.

## Design notes / links

VIEWMD-0015 (`issues/archive/VIEWMD-0015-mermaid-flowchart-diagrams.md` once archived) is the byte-for-byte baseline this extends. `viewmd/mermaid/flowchart/parser.py:parse` is where `BT`/`RL` are currently parsed and aliased (`graph_direction = "TD"` / `"LR"`); `viewmd/mermaid/flowchart/graph.py:create_mapping` is where placement order/leveling happens; `viewmd/mermaid/grid/coords.py:determine_start_and_end_dir` is where attachment-side heuristics are keyed on `graph_direction` today (only `"TD"`/`"LR"` branches exist).

The concrete example the maintainer flagged: `graph RL` with `A --> B --> C` should render `C`, `B`, `A` left-to-right with arrows pointing right-to-left (`A→B→C` semantically, drawn mirrored), not identically to `graph LR`.

## Acceptance / verification

- A fixture for `graph RL` with a simple chain (`A --> B --> C`) showing the layout genuinely mirrored relative to its `LR` counterpart -- nodes in reversed screen position, arrows pointing the opposite screen direction, edge semantics (`A` still points to `B` still points to `C`) unchanged. Hand-verified against what real Mermaid (e.g. mermaid.live) renders for the same source, since there's no upstream Go binary output to diff against.
- Same for `BT` against its `TD` counterpart.
- A subgraph fixture under `RL`/`BT` renders without crashing and with a sane (if not exhaustively polished) layout.
- All of VIEWMD-0015's existing `TD`/`LR` fixtures still pass unchanged (regression guard on the byte-for-byte baseline).
- `./run-tests.sh` green.

## Peer review

Left blank until implemented and tested; filled in as part of the Definition of Done landing gate.
