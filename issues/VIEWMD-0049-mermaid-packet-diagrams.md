---
id: VIEWMD-0049
title: Render Mermaid packet diagrams
status: proposed
area: [render, mermaid]
effort: low
created: 2026-08-09
updated: 2026-08-09
accepted_by:
accepted_at:
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Render Mermaid packet diagrams

## Summary

Add a Mermaid diagram type -- `packet-beta` -- alongside the existing flowchart, sequence, and ER
renderers (`viewmd/mermaid/{flowchart,sequence,er}/`) and the diagram types proposed in
[VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md) through
[VIEWMD-0042](VIEWMD-0042-mermaid-gitgraph-diagrams.md). A Mermaid packet diagram
(https://mermaid.js.org/syntax/packet.html) draws a fixed-width bit/byte field layout -- the kind
used to document a network protocol header -- as a table of labeled ranges wrapped onto rows of a
fixed bit width.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `packet-beta` fence
today -- it falls through every `_is_*_diagram` sniff. Of the eight diagram types termaid supports
that viewmd does not yet track, this is one of the smaller ones (`src/termaid/{parser,renderer,model}/packet.py`,
~290 lines combined in termaid): a fixed-row-width table with numbered bit-range labels, closer to
a formatting problem (row wrapping at a fixed bit width, column-width division within a row) than
a new layout algorithm.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `packet-beta` (`viewmd/mermaid/packet/parser.py:sniff`,
   following the `sniff`/`parse`/`render` module shape already used by the other diagram packages)
   and wire it into `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
2. MUST parse a field line of the form `<start>-<end>: "<label>"` (a multi-bit field) and the
   single-bit shorthand `<start>: "<label>"` (equivalent to `<start>-<start>`).
3. MUST parse fields in declaration order and preserve that order in the rendered output; fields
   need not be parsed as validated-contiguous (a gap or overlap between declared ranges is passed
   through as given, not rejected -- see Non-goals).
4. MUST render fields wrapped onto rows of a fixed bit width (Mermaid's own default is 32 bits per
   row, per the reference example below), each row showing a numbered bit-range header line above
   a bordered box divided into one cell per field on that row, sized proportionally to each field's
   bit width within the row.
5. MUST split a field that spans a row boundary (its `start`-`end` range crosses the fixed row
   width) across two rows, each half showing the same label.
6. MUST truncate a label too long for its field's proportional cell width using the same
   wide-character-safe truncation convention already used elsewhere in viewmd's Mermaid renderers
   (`viewmd/mermaid/er/`) rather than overflowing or destroying the cell's borders.
7. MUST leave a `packet-beta` fence whose content fails to parse untouched (fall back to showing
   the raw fence), same fallback discipline as the other Mermaid renderers'
   MUST-NOT-crash requirement.
8. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- Validating that fields are contiguous/non-overlapping -- requirement 3 explicitly passes ranges
  through as declared; a dedicated validation/warning pass is out of scope.
- A configurable row bit-width (`%%{init: {"packet": {"bitsPerRow": N}}}%%`) -- a single fixed
  default (32 bits per row, matching Mermaid's own default and termaid's reference output) is
  sufficient for v1.
- Color/theme differentiation between fields -- viewmd's existing Mermaid renderers do not use ANSI
  color today, and this issue does not introduce it.
- Matching any upstream reference implementation byte-for-byte -- the local `mermaid-ascii` Go
  oracle used for differential-testing flowchart/sequence/ER has no packet-diagram support, so
  fixtures here are hand-authored/visually-verified, same posture as VIEWMD-0032 onward. termaid's
  own rendering (below) is a useful cross-check, not an oracle to match exactly.

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a
`_is_packet_diagram`/`_parse_packet`/`_render_packet` import trio and a new `if` branch, mirroring
the `er` branch (parse-then-render, catching a module-local `ParseError` into `MermaidError`). New
module lives at `viewmd/mermaid/packet/` (`parser.py`, `renderer.py`), sibling to the other diagram
packages. The bordered-row-of-cells box is close enough to `viewmd/mermaid/er/renderer.py`'s
divided entity box that the same divider-drawing helper may be directly reusable; requirement 6's
CJK/wide-character truncation should reuse whatever helper VIEWMD-00xx-era ER wide-character work
already established there rather than reimplementing display-width math.

### Reference example (termaid's actual output)

```
--- source ---
packet-beta
    0-15: "Source Port"
    16-31: "Destination Port"
    32-47: "Length"
    48-63: "Checksum"
--- rendered ---
 0                                             15 16                                           31
 ╭───────────────────────────────────────────────┬───────────────────────────────────────────────╮
 │                 Source Port                   │               Destination Port                │
 ╰───────────────────────────────────────────────┴───────────────────────────────────────────────╯
 32                                            47 48                                           63
 ╭───────────────────────────────────────────────┬───────────────────────────────────────────────╮
 │                    Length                     │                   Checksum                    │
 ╰───────────────────────────────────────────────┴───────────────────────────────────────────────╯
```

Here all four fields happen to fit two-per-32-bit-row without splitting; a field crossing a row
boundary (requirement 5) is not exercised by this particular example and needs its own fixture.

## Acceptance / verification

- Unit tests for the parser: a multi-bit field, the single-bit shorthand, declaration-order
  preservation, and a non-contiguous field list (requirement 3, passed through unvalidated).
- A rendered fixture reproducing the four-field example above, hand-verified (per Non-goals, no
  oracle to differential-test against; termaid's own output is a cross-check, not a target to match
  exactly).
- A rendered fixture with a field spanning a row boundary, confirming it splits across both rows
  with the same label (requirement 5).
- A fixture with a label too long for its cell (including a wide/CJK label, per requirement 6),
  confirming truncation doesn't destroy the cell's borders -- termaid's own test suite
  (`tests/test_packet.py:TestPacketWideChars`) is a useful template for this case.
- A malformed `packet-beta` fence (e.g. a field line missing its `:` separator) falls back to
  showing the raw fence rather than crashing viewmd.
- `./run-tests.sh` green.

## Peer review

