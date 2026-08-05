---
id: VIEWMD-0016
title: Render Mermaid entity-relationship diagrams as box-drawing ASCII art
status: in-progress
area: [render, mermaid]
effort: medium
created: 2026-08-03
updated: 2026-08-05
accepted_by: George Moses
accepted_at: 2026-08-05
commits: []
related: [VIEWMD-0014, VIEWMD-0015]
supersedes: []
changelog:
reason:
---

# Render Mermaid entity-relationship diagrams as box-drawing ASCII art

## Summary

Extend the Mermaid support added in VIEWMD-0014/VIEWMD-0015 to entity-relationship (`erDiagram`) diagrams: fenced ` ```mermaid ` blocks containing an ER diagram render as box-drawing art, via a from-scratch Python port of the `pkg/er` package of `github.com/AlexanderGrooff/mermaid-ascii`.

## Motivation / problem

`pkg/er` is the third and last diagram type the upstream Go library implements (alongside sequence, done in VIEWMD-0014, and flowchart, VIEWMD-0015). Unlike flowcharts it does not need the A*-based arrow-routing engine -- `pkg/er/renderer.go` implements its own self-contained layout, closer in shape to the sequence-diagram renderer than to the flowchart one. It's a smaller, independent port that rounds out coverage of everything the upstream library supports.

## Requirements

1. MUST render ` ```mermaid ` fences containing an `erDiagram` to box-drawing art, matching `pkg/er`'s output byte-for-byte for: entity boxes, attributes, crow's-foot cardinality notation, and identifying vs. non-identifying relationships (solid vs. dashed connecting lines -- see `pkg/er/renderer.go`'s glyph set).
2. MUST verify the port byte-for-byte against the real Go binary (built locally from the cloned `mermaid-ascii` repo) on a differential-test corpus, the same methodology VIEWMD-0014 and VIEWMD-0015 used.
3. MUST slot into the existing `viewmd/mermaid/` package and dispatch in `viewmd/mermaid/__init__.py`'s `render()`, alongside sequence and flowchart.
4. MUST NOT add any new dependency.
5. MUST leave an ER-diagram fence untouched (original source shown, no crash) when parsing fails.
6. SHOULD NOT depend on the flowchart port's shared grid/drawing engine (VIEWMD-0015) unless investigation of `pkg/er/renderer.go` shows it actually reuses that engine upstream -- initial reading of the Go source suggests it doesn't and implements its own renderer.

## Non-goals

- Diagram types other than sequence, flowchart, and ER -- the upstream Go library implements no others (class, state, Gantt, pie, user journey, git graph are not in `AlexanderGrooff/mermaid-ascii` at all).

## Design notes / links

Reference implementation: `pkg/er/{parser,renderer}.go` in `github.com/AlexanderGrooff/mermaid-ascii` (~1,348 non-test lines). See VIEWMD-0014's design notes for the porting approach.

## Acceptance / verification

- A golden-file differential-test corpus (`tests/fixtures/mermaid_er/`) covering entities with attributes, both cardinality notations, and identifying/non-identifying relationships -- each pinned to output captured from the real Go binary.
- Unit tests for parse-error paths.
- `./run-tests.sh` green.

## Peer review

- **Claude** (agent), 2026-08-05: Ported `pkg/er/{parser,layout,renderer}.go` to `viewmd/mermaid/er/{parser,layout,renderer,charset}.py`, self-contained per req. 6 (does not depend on `viewmd/mermaid/grid`, confirmed by reading `pkg/er/layout.go`: it implements its own canvas/routing rather than reusing the flowchart engine). Wired into `viewmd/mermaid/__init__.py`'s `render()` dispatch. Built the reference binary from the local `mermaid-ascii` clone and captured 8 `.mmd` fixtures x 2 charsets (16 cases) under `tests/fixtures/mermaid_er/`, covering entity attribute tables, both cardinality notations (crow's-foot and word/numeric shorthand), identifying/non-identifying relationships, self-loops, aliases, `:::class`/`classDef`/`style`/`accTitle`/`accDescr`/`direction` lines, backtick-escaped and parenthesised attribute types, and a 6-entity/6-relationship grid layout exercising multi-lane connector routing. All 16 differential cases match the Go binary byte-for-byte, including two upstream rendering quirks reproduced faithfully rather than silently fixed (a `:::class`-decorated entity's attach-tee placement, and a trailing key token being silently dropped when it follows a quoted attribute comment on the same line — both are pre-existing `pkg/er` behavior, not new bugs). Added 23 parser unit tests (`tests/test_mermaid_er_parser.py`) covering every parse-error path plus sniff/entity/relationship semantics, and 2 preprocess-integration tests confirming an unparseable `erDiagram` fence is left untouched. Updated `README.md`/`docs/example.md`/`docs/mermaid-examples.md` for ER support, matching VIEWMD-0015's precedent. `./run-tests.sh` (pytest 298 passed, ruff, pip-audit, issues check) all green.
