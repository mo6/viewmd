---
id: VIEWMD-0022
title: Render real node shapes in Mermaid flowcharts
status: proposed
area: [render, mermaid]
effort:
created: 2026-08-05
updated: 2026-08-05
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0015, VIEWMD-0027]
supersedes: []
changelog:
reason:
---

# Render real node shapes in Mermaid flowcharts

## Summary

VIEWMD-0015 ported flowchart rendering byte-for-byte against `github.com/AlexanderGrooff/mermaid-ascii`, which turned out to only recognize `A[Label]` square-bracket syntax as a distinct node shape -- every other mermaid shape syntax (`()`, `{}`, `(())`, `[()]`, `[[ ]]`, etc.) silently flattens to a bare label. This issue is to go beyond the upstream reference and implement real shape rendering in viewmd, now that the flowchart engine (`viewmd/mermaid/grid/`, `viewmd/mermaid/flowchart/`) exists to build on. (`BT`/`RL` direction reversal, originally scoped here too, is split out to [VIEWMD-0027](VIEWMD-0027-flowchart-rl-bt-direction-reversal.md) -- same underlying limitation category, but an unrelated fix in a different part of the engine.)

## Motivation / problem

Round (`()`), stadium/pill (`([ ])`), subroutine (`[[ ]]`), cylinder (`[( )]`), and diamond (`{}`) shapes are common in real-world Mermaid flowcharts -- diamonds especially, for decision nodes. Silently flattening them to a bare-label rectangle (VIEWMD-0015's `shapes_fallback` fixture demonstrates this: `B{Decide}` renders as a box literally labelled `B{Decide}`) is a visible, surprising gap directly inherited from upstream's own limitation, not a deliberate viewmd design choice.

This isn't just a cosmetic gap: it silently breaks graph topology. `docs/example.md`/`docs/mermaid-examples.md`'s own "Branching and labelled edges" example (`A[Start] --> B{Decision}` followed by `B -->|yes| C[Do it]` / `B -->|no| D[Skip it]`) is reported by the maintainer as rendering "weirdly" -- three boxes spread across two disconnected rows instead of the expected single-diamond-with-two-branches tree. Root cause: since `{}` isn't recognized, `parse_node` treats the *entire* string `"B{Decision}"` as the node's bare name, distinct from the plain `"B"` referenced by the later `-->|yes|`/`-->|no|` lines -- two different node identities for what the user wrote as one node. Fixing shape parsing must extract the name (`B`) separately from the shape delimiter and label (`{Decision}`), the same way `[...]` already does, so `B{Decision}` and later bare `B` references resolve to the same node and the branch reunites into the tree shape real Mermaid renders.

## Requirements

1. MUST parse `()` (round), `{}` (diamond), `(())` (circle), `([ ])` (stadium), `[[ ]]` (subroutine), and `[( )]` (cylinder/database) node-shape syntax in `viewmd/mermaid/flowchart/parser.py`'s node grammar, distinct from the plain `[...]` rectangle. MUST extract the node's *name* separately from the shape delimiters and label text (the way `[...]` parsing already does), so a shaped declaration like `B{Decision}` and a later bare reference to `B` resolve to the same node -- not two different nodes as they do today (see Motivation).
2. MUST render each shape with a distinguishable border in `viewmd/mermaid/grid/canvas.py`'s box-drawing (e.g. rounded corners or a distinct glyph set per shape) -- exact glyph choices are a design decision for this issue, not dictated by upstream since there's no reference output to match.
3. MUST NOT change the byte-for-byte-matched behavior for `[...]` rectangle nodes -- this issue only adds new rendering paths, it doesn't touch VIEWMD-0015's verified baseline.
4. MUST leave a flowchart fence untouched (no crash) on any shape that still isn't supported, same fallback discipline as VIEWMD-0015 requirement 6.

## Non-goals

- `BT`/`RL` direction reversal -- tracked separately as [VIEWMD-0027](VIEWMD-0027-flowchart-rl-bt-direction-reversal.md).
- Matching any upstream reference byte-for-byte -- there is none for this behavior, since `mermaid-ascii` doesn't implement it either. Golden fixtures for this issue are necessarily hand-authored/visually-verified, unlike VIEWMD-0014/0015/0016's differential-tested ones.
- Fill colors or other styling shapes can't represent in plain box-drawing art (unchanged from VIEWMD-0015's non-goals).
- Any other Mermaid flowchart feature not already covered by VIEWMD-0015 (e.g. new arrow styles, `click` interactions) -- out of scope unless discovered to be needed alongside shapes.

## Design notes / links

VIEWMD-0015 (`issues/archive/VIEWMD-0015-mermaid-flowchart-diagrams.md` once archived) is the byte-for-byte baseline this extends. `viewmd/mermaid/flowchart/parser.py:parse_node` is where shape parsing currently only recognizes `[...]`; `viewmd/mermaid/grid/canvas.py:draw_box` is where the border glyphs are chosen.

## Acceptance / verification

- Unit tests for each new shape's parsing (node type, label extraction) and a rendered fixture per shape showing a visibly distinct border, hand-verified (no upstream binary to diff against, per non-goals).
- The `docs/mermaid-examples.md` "Branching and labelled edges" example (`A[Start] --> B{Decision}`, `B -->|yes| C[Do it]`, `B -->|no| D[Skip it]`) renders as a single diamond node with two outgoing branches, not three disconnected boxes -- a unit test asserting `B{Decision}` and a later bare `B` parse to the same node name.
- All of VIEWMD-0015's existing fixtures still pass unchanged (regression guard on the byte-for-byte baseline).
- `./run-tests.sh` green.

## Peer review

Left blank until implemented and tested; filled in as part of the Definition of Done landing gate.
