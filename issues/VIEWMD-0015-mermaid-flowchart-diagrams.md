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
related: [VIEWMD-0014, VIEWMD-0022]
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

1. MUST render ` ```mermaid ` fences containing a `graph`/`flowchart` diagram to box-drawing art, matching `cmd/`'s output byte-for-byte for: both directions (`TD`/`LR`), labelled and unlabelled edges, subgraphs, and `classDef`/`:::` style classes (`cmd/graph.go`, `cmd/parse.go`). Confirmed against the real binary during implementation: `cmd/`'s parser only ever recognizes `A[Label]` square-bracket syntax as a distinct node shape -- `()`, `{}`, `(())`, and every other mermaid shape syntax is silently flattened to a bare label, and `BT`/`RL` directions are accepted syntax but aliased to `TD`/`LR` internally, never actually reversed. This is not a gap to fill in; the port matches this behavior exactly rather than adding shape/direction support the reference implementation itself doesn't have, so every corner of the port stays differential-testable against requirement 3 below.
2. MUST reuse the shared grid/drawing/arrow-routing engine (`cmd/draw.go`, `cmd/arrow.go`, `cmd/direction.go`, `cmd/label.go`) as a Python module (`viewmd/mermaid/grid/`) distinct from the flowchart-specific parser/model/layout code (`viewmd/mermaid/flowchart/`), so a later ER-diagram port (a separate issue) doesn't need its own coordinate types, A* router, or canvas/junction-merging drawing code if it turns out to need them. `cmd/mapping_node.go`/`cmd/mapping_edge.go`'s node-sizing/edge-routing orchestration stayed with the flowchart-specific graph model instead of the shared package: in the upstream source itself these are methods on the single flowchart-specific `*graph` receiver, not generic across diagram types (ER diagrams in the same upstream repo use their own entirely separate `pkg/er` implementation rather than reusing `cmd/graph.go`), so factoring them out as "shared" would be a boundary the reference implementation doesn't actually have.
3. MUST verify the port byte-for-byte against the real Go binary (built locally from the cloned `mermaid-ascii` repo) on a differential-test corpus, the same methodology VIEWMD-0014 used -- not hand-written expected output.
4. MUST slot into the existing `viewmd/mermaid/` package and `viewmd/preprocessors.py` pipeline from VIEWMD-0014 (dispatch by diagram type in `viewmd/mermaid/__init__.py`'s `render()`), not a parallel mechanism.
5. MUST NOT add any dependency beyond what VIEWMD-0014 already added (`wcwidth`) -- no compiled binaries, no shelling out. `container/heap`'s equivalent turned out not to be a drop-in use of the stdlib `heapq`: Go's heap breaks equal-priority ties purely by array structure (no secondary key), and `heapq`'s different sift implementation pops ties in a different order for the same push sequence, which is directly visible in A*-routed output (confirmed with a differential fixture requiring routing around an obstacle node). `viewmd/mermaid/grid/astar.py` ports `container/heap`'s push/pop/up/down algorithm by hand instead, still pure stdlib, no new dependency.
6. MUST leave a flowchart fence untouched (original source shown, no crash) when parsing or layout fails.

## Non-goals

- Diagram types other than flowchart and sequence (class, state, Gantt, pie, user journey, git graph) -- not implemented in the upstream Go library at all, so there is nothing to port; ER diagrams are their own separate issue (VIEWMD-0016).
- Styling directives that ASCII can't represent (fill colours themselves, since a box-drawing frame has no fill). `classDef`/`:::` foreground `color:` *is* rendered, as real 24-bit ANSI truecolor escapes wrapping each label character, matching `cmd/draw.go`'s `wrapTextInColor` -- confirmed against the real binary, not assumed to be out of scope.
- Sizing/wrapping the rendered diagram to the terminal's `--width`.

## Design notes / links

Reference implementation: `cmd/{parse,graph,draw,arrow,direction,mapping_node,mapping_edge,math,label,render}.go` in `github.com/AlexanderGrooff/mermaid-ascii` (~2,879 non-test lines excluding the `cobra` CLI/`web` HTTP-server glue, which isn't ported). See VIEWMD-0014's design notes for the general porting approach (translate, don't shell out; differential-test against the real binary) -- the same approach applies here, just with a substantially larger reference implementation (a real A*-based layout engine, not just column/row placement).

Python module layout: `viewmd/mermaid/grid/` (`coords.py`, `astar.py`, `canvas.py`, `label.py`) is the shared engine from requirement 2; `viewmd/mermaid/flowchart/` (`parser.py`, `graph.py`, `renderer.py`) is the flowchart-specific parser/model/layout, mirroring `viewmd/mermaid/sequence/`'s existing `parser.py`/`renderer.py` split plus the extra `graph.py` for the node/edge/subgraph model and layout algorithm.

## Acceptance / verification

- A golden-file differential-test corpus (`tests/fixtures/mermaid_flowchart/`) covering both directions, the `BT`/`RL` alias behavior, labelled/unlabelled/bidirectional edges, chained arrows, fan-out, subgraphs (incl. nested), `classDef`/`:::` styling, parallel/duplicate edges, multi-line labels, and multi-node graphs with edges that must route around other nodes -- each pinned to output captured from the real Go binary.
- Unit tests for parse-error paths, `sniff()`, node-shape/edge/subgraph/style parsing, and the `BT`/`RL`/`TD`/`LR` aliasing, mirroring VIEWMD-0014's `test_mermaid_sequence_parser.py` structure.
- `./run-tests.sh` green.

## Peer review

- **Claude** (agent), 2026-08-05: Implemented `viewmd/mermaid/grid/` (`coords.py`, `astar.py`, `canvas.py`, `label.py`) and `viewmd/mermaid/flowchart/` (`parser.py`, `graph.py`, `renderer.py`), wired into `viewmd/mermaid/__init__.py`'s dispatch with a broad internal-error catch (req. 6) alongside the existing sequence-diagram branch. Factored `sequence/renderer.py`'s private `_width()` into `textutil.width()` for reuse (req. 2's spirit). 16 golden fixtures under `tests/fixtures/mermaid_flowchart/` (32 cases incl. ASCII) generated from the real Go binary at `~/Documents/Projects/mermaid-ascii` per req. 3, covering both directions, the `BT`/`RL` alias, labelled/unlabelled/bidirectional/chained/fan-out edges, nested subgraphs, `classDef` color styling, parallel edges, self-loops, an obstacle-routing case, and multi-line labels; plus 31 parser unit tests (parse errors, `sniff()`, node-shape fallback, subgraph nesting, direction aliasing). All pass, plus a ~25-fixture manual differential batch beyond the committed corpus. `./run-tests.sh` green (pytest, ruff, pip-audit, issues check).
  Found and fixed one real bug during verification: `viewmd/mermaid/grid/astar.py`'s ported `container/heap` used Python's floor-dividing `//` for the parent-index calculation `(j-1)//2`, which gives `-1` at the root (`j=0`) where Go's truncating `/` gives `0` -- silently indexing `items[-1]` (the array's last element) instead of stopping, corrupting tie-break order in A*'s priority queue. Caught by an obstacle-routing fixture that requires routing around another node, where it produced a visually different (but equal-cost) path than the real binary; fixed by special-casing `j == 0`, verified with a standalone Go/Python heap-trace comparison before and after.
  Also corrected requirement 1 (shape/direction scope) and requirement 2 (module-boundary wording) to state what was actually confirmed against the real binary during implementation, per the maintainer's scope decision recorded above (2026-08-05, "Match upstream exactly").
