---
id: VIEWMD-0015
title: Render Mermaid flowchart diagrams as box-drawing ASCII art
status: in-progress
area: [render, mermaid]
effort: high
created: 2026-08-03
updated: 2026-08-05
accepted_by: George Moses
accepted_at: 2026-08-05
commits: []
related: [VIEWMD-0014]
supersedes: []
changelog:
reason:
---

# Render Mermaid flowchart diagrams as box-drawing ASCII art

## Summary

Extend the Mermaid support added in VIEWMD-0014 to flowcharts (`graph`/`flowchart` diagrams): fenced ` ```mermaid ` blocks containing a flowchart render as box-drawing art, the same way sequence diagrams already do, via a from-scratch Python port of the `cmd/` package of `github.com/AlexanderGrooff/mermaid-ascii`.

## Motivation / problem

VIEWMD-0014 rendered sequence diagrams but explicitly left flowcharts as a non-goal, since they're the most involved of the three diagram types the upstream Go library implements: they need a real grid-layout engine and A* edge-routing (`container/heap`-based pathfinding around obstacles, `cmd/arrow.go`), not just column/row placement. Flowcharts are also the most common Mermaid diagram type in the wild, so leaving them unrendered is the most visible gap in what VIEWMD-0014 shipped.

## Requirements

1. MUST render ` ```mermaid ` fences containing a `graph`/`flowchart` diagram to box-drawing art, matching `cmd/`'s output byte-for-byte for: both directions (`TD`/`LR` at minimum -- confirm `BT`/`RL` support in the source before committing to them), node shapes (`[]`, `()`, `{}`, and whichever others `cmd/mapping_node.go` defines), labelled and unlabelled edges, subgraphs, and style classes to the extent ASCII output can represent them (`cmd/graph.go`, `cmd/parse.go`).
2. MUST reuse the shared grid/drawing/arrow-routing engine (`cmd/draw.go`, `cmd/arrow.go`, `cmd/direction.go`, `cmd/mapping_node.go`, `cmd/mapping_edge.go`, `cmd/math.go`, `cmd/label.go`) as a Python module distinct from the flowchart-specific parser/placement code, so a later ER-diagram port (a separate issue) doesn't need its own arrow router if it turns out to need one.
3. MUST verify the port byte-for-byte against the real Go binary (built locally from the cloned `mermaid-ascii` repo) on a differential-test corpus, the same methodology VIEWMD-0014 used -- not hand-written expected output.
4. MUST slot into the existing `viewmd/mermaid/` package and `viewmd/preprocessors.py` pipeline from VIEWMD-0014 (dispatch by diagram type in `viewmd/mermaid/__init__.py`'s `render()`), not a parallel mechanism.
5. MUST NOT add any dependency beyond what VIEWMD-0014 already added (`wcwidth`) -- no compiled binaries, no shelling out. `container/heap`'s Python equivalent is the stdlib `heapq`.
6. MUST leave a flowchart fence untouched (original source shown, no crash) when parsing or layout fails.

## Non-goals

- Diagram types other than flowchart and sequence (class, state, Gantt, pie, user journey, git graph) -- not implemented in the upstream Go library at all, so there is nothing to port; ER diagrams are their own separate issue (VIEWMD-0016).
- Styling directives that ASCII can't represent (fill colours, `classDef` colour styling) beyond whatever plain-frame fallback the upstream implementation already does.
- Sizing/wrapping the rendered diagram to the terminal's `--width`.

## Design notes / links

Reference implementation: `cmd/{parse,graph,draw,arrow,direction,mapping_node,mapping_edge,math,label,render}.go` in `github.com/AlexanderGrooff/mermaid-ascii` (~2,879 non-test lines excluding the `cobra` CLI/`web` HTTP-server glue, which isn't ported). See VIEWMD-0014's design notes for the general porting approach (translate, don't shell out; differential-test against the real binary) -- the same approach applies here, just with a substantially larger reference implementation (a real A*-based layout engine, not just column/row placement).

## Acceptance / verification

- A golden-file differential-test corpus (`tests/fixtures/mermaid_flowchart/`) covering both directions, every node shape, labelled/unlabelled edges, subgraphs, and multi-node graphs with edges that must route around other nodes -- each pinned to output captured from the real Go binary.
- Unit tests for parse-error paths, mirroring VIEWMD-0014's `test_mermaid_sequence_parser.py` structure.
- `./run-tests.sh` green.

## Peer review

Left blank until implemented and tested; filled in as part of the Definition of Done landing gate.
