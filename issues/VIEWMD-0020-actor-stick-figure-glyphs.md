---
id: VIEWMD-0020
title: Render Mermaid sequence-diagram actors as stick-figure glyphs
status: in-progress
area: [render, mermaid]
effort: medium
created: 2026-08-04
updated: 2026-08-04
accepted_by: George Moses
accepted_at: 2026-08-04
commits: []
related: [VIEWMD-0017]
supersedes: []
changelog:
reason:
---

# Render Mermaid sequence-diagram actors as stick-figure glyphs

## Summary

[[VIEWMD-0017]] made `actor`-declared participants parse and render, but only as ordinary boxes, identical to `participant`. In upstream Mermaid, `actor` is visually distinct: a stick figure rather than a box. This issue draws an actual stick-figure glyph for `actor` participants in the ASCII-art renderer.

## Motivation / problem

Rendering `actor` identically to `participant` is a correct but incomplete port of Mermaid semantics — the two keywords exist specifically to produce different visuals. Users porting diagrams that rely on that visual distinction (e.g. actor = human/external, participant = system) lose that signal in viewmd's output. [[VIEWMD-0017]] explicitly scoped this out as a larger, separate change; this issue is that follow-up.

## Requirements

1. MUST retain, from parsing, whether a declared participant was declared with `actor` vs. `participant` (the parser currently normalizes both to the same participant representation per [[VIEWMD-0017]]).
2. MUST render an `actor` participant's header as a small stick-figure glyph (box-drawing/ASCII, consistent with the renderer's existing character set) instead of a plain box top, above or in place of the existing box.
3. MUST keep the actor's label/name rendering, lifeline placement, and message-arrow alignment consistent with `participant` boxes, so mixed `actor`/`participant` diagrams still line up correctly.
4. MUST NOT change rendering of existing `participant`-only diagrams.
5. SHOULD keep the stick figure's rendered width close to (or no wider than) the label text width, to avoid unnecessarily widening diagrams that mix actors and participants.

## Non-goals

Re-litigating whether `actor` parses at all — that's settled by [[VIEWMD-0017]]. This issue only concerns the visual glyph.

## Design notes / links

Mermaid's own stick-figure rendering (head circle + body/arms/legs strokes) is the visual reference; the exact ASCII/box-drawing approximation is an implementation decision for this issue, not prescribed here. See `viewmd/mermaid/sequence/` for the existing box-drawing renderer this extends.

## Acceptance / verification

- A render/golden test for a diagram mixing `actor` and `participant` declarations (e.g. the [[VIEWMD-0017]] reproduction), confirming actors render as stick figures and participants still render as boxes.
- A regression test confirming an all-`participant` diagram's output is byte-for-byte unchanged.
- `./run-tests.sh` green.

## Peer review

