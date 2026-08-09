---
id: VIEWMD-0049
title: Render Mermaid packet diagrams
status: implemented
area: [render, mermaid]
effort: low
created: 2026-08-09
updated: 2026-08-09
accepted_by: George Moses
accepted_at: 2026-08-09
commits: [d2fb19e]
related: []
supersedes: []
changelog: "[1.13.0]"
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

1. MUST recognize a ` ```mermaid ` fence whose first meaningful line's keyword token is
   `packet-beta` or `packet` (Mermaid v11 dropped the `-beta` suffix; both spellings render
   identically and MUST be accepted, matching the `pie`/`pie showData` case in
   `viewmd/mermaid/pie/parser.py:sniff`) (`viewmd/mermaid/packet/parser.py:sniff`, following the
   `sniff`/`parse`/`render` module shape already used by the other diagram packages) and wire it
   into `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
2. MUST parse a field line of the form `<start>-<end>: "<label>"` (a multi-bit field), the
   single-bit shorthand `<start>: "<label>"` (equivalent to `<start>-<start>`), and the
   cursor-relative bits shorthand `+<count>: "<label>"` (Mermaid v11.7.0+; equivalent to
   `<cursor>-<cursor + count - 1>`, where `cursor` starts at 0 and advances to one past the
   previous field's end after every field, `+N` or explicit, per the reference example below).
   `+N` and explicit `<start>-<end>`/`<start>` forms MUST be mixable within the same diagram, in
   declaration order (e.g. `+16` followed by `9-15` followed by another `+N` continuing from 16).
   An explicit `end` less than `start`, or a `+0` (zero-bit) field, MUST raise a parse error
   (requirement 7's fallback), matching upstream's own `populate()` checks
   (`packages/mermaid/src/diagrams/packet/parser.ts`, confirmed directly against the grammar/parser
   source rather than assumed from docs).
3. MUST parse fields in strictly contiguous declaration order and preserve that order in the
   rendered output: each field's `start` MUST equal one past the previous field's `end` (0 for the
   first field), a `+N` field always satisfies this automatically since its `start` derives from
   the cursor, but an explicit `<start>-<end>`/`<start>` field whose `start` disagrees MUST raise a
   parse error (requirement 7's fallback) rather than being silently accepted with a gap or
   overlap -- **this reverses this issue's original draft**, which had assumed (without checking
   upstream source) that non-contiguous fields pass through unvalidated; `populate()` in
   `packages/mermaid/src/diagrams/packet/parser.ts` throws `"Packet block ... is not contiguous.
   It should start from ..."` on exactly this case, so matching that is the correct behavior for a
   `packet-beta`/`packet` implementation, not a design choice to relax.
4. MUST render fields wrapped onto rows of a fixed bit width (Mermaid's own default is 32 bits per
   row, per the reference example below), each row showing a numbered bit-range header line above
   a bordered box divided into one cell per field on that row, sized proportionally to each field's
   bit width within the row.
5. MUST split a field that spans a row boundary (its `start`-`end` range crosses the fixed row
   width) across two rows, each half showing the same label.
6. MUST truncate a label too long for its field's proportional cell width using the same
   wide-character-safe truncation convention already used elsewhere in viewmd's Mermaid renderers
   (`viewmd/mermaid/er/`) rather than overflowing or destroying the cell's borders.
7. MUST leave a `packet-beta`/`packet` fence whose content fails to parse untouched (fall back to
   showing the raw fence), same fallback discipline as the other Mermaid renderers'
   MUST-NOT-crash requirement.
8. MUST NOT change behavior for any existing recognized Mermaid diagram type.
9. MUST parse an optional `title <text>` line (its own line in the fence body, same directive
   form and same regex-after-`title `-keyword approach as
   `viewmd/mermaid/pie/parser.py:parse`'s existing `title` handling -- not the YAML-frontmatter
   `title: "..."` form, see Non-goals) and, when present, render it centered, in plain text, on its
   own line directly above the diagram's rows. Plain rather than bold (**reversing this issue's
   original draft**, which specified `wrap_text_bold`): packet has no `color` parameter at all
   (unlike `pie`, where bold is itself gated behind `color`) and the Non-goals section is explicit
   that this issue introduces no ANSI -- an unconditional bold escape would quietly contradict
   that with no way to opt back out.

## Non-goals

- A configurable row bit-width (`%%{init: {"packet": {"bitsPerRow": N}}}%%`) -- a single fixed
  default (32 bits per row, matching Mermaid's own default and termaid's reference output) is
  sufficient for v1.
- Color/theme differentiation between fields -- viewmd's existing Mermaid renderers do not use ANSI
  color today, and this issue does not introduce it.
- YAML frontmatter (a ` --- ` block preceding the diagram keyword, e.g. `---\ntitle: "TCP Packet"\n---`)
  as a second way to set the title -- no viewmd Mermaid renderer parses generic Mermaid frontmatter
  today (checked: `pie`, the only other renderer with title support, only handles the inline
  `title <text>` directive), so adding frontmatter parsing here would be a cross-cutting change
  affecting every diagram type, not a packet-specific one. Requirement 9 covers only the inline
  `title <text>` form; a fence using frontmatter-style `title:` still falls back to the raw fence
  (requirement 7) same as before this issue, and frontmatter support in general is a candidate for
  its own separate issue if wanted.
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
already established there rather than reimplementing display-width math (in practice, no such
truncation helper actually exists yet in `er/` either -- ER auto-grows its boxes to fit content
instead of truncating -- so this issue's renderer needs its own small wide-character-safe
truncate helper, there being nothing to import). Requirement 9's title parse has a direct,
already-implemented precedent to mirror: `viewmd/mermaid/pie/parser.py`'s `title` regex; its
render is centered plain text only (no `wrap_text_bold`, see requirement 9's note on why bold
doesn't apply here).

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

### Mockup: field spanning a row boundary (requirement 5)

Hand-authored (no termaid/oracle output available for this one) -- illustrates a 13-bit field
(`19-31`) that is the tail half of a 19-31/32-47 split, alongside a field that fits entirely
within one row:

```
--- source ---
packet-beta
    0-18: "Flags"
    19-47: "Sequence Number"
    48-63: "Checksum"
--- rendered (mockup) ---
 0                                                      18 19                                   31
 ╭─────────────────────────────────────────────────────────┬───────────────────────────────────────╮
 │                          Flags                          │            Sequence Number            │
 ╰─────────────────────────────────────────────────────────┴───────────────────────────────────────╯
 32                                            47 48                                            63
 ╭────────────────────────────────────────────────┬────────────────────────────────────────────────╮
 │                Sequence Number                 │                    Checksum                    │
 ╰────────────────────────────────────────────────┴────────────────────────────────────────────────╯
```

`Sequence Number` (bits 19-47) is drawn twice, once per row, per requirement 5.

### Mockup: `+N` cursor-relative shorthand, mixed with explicit ranges (requirement 2)

Hand-authored -- two consecutive `+N` fields followed by an explicit range picking up exactly
where the cursor left off, matching Mermaid's own documented mix-and-match behavior:

```
--- source ---
packet-beta
    +8: "Type"
    +8: "Code"
    16-31: "Checksum"
--- rendered (mockup) ---
 0                      7 8                     15 16                                            31
 ╭────────────────────────┬────────────────────────┬────────────────────────────────────────────────╮
 │          Type          │          Code          │                    Checksum                    │
 ╰────────────────────────┴────────────────────────┴────────────────────────────────────────────────╯
```

`+8` resolves to `0-7` (cursor starts at 0), the second `+8` resolves to `8-15` (cursor now at
8), and the explicit `16-31` both continues the cursor contiguously and demonstrates it isn't
required to be a `+N` field itself.

### Mockup: TCP header (real-world example, hand-authored)

The canonical protocol-header example from Mermaid's own packet docs, spanning 8 rows at the
32-bit default and exercising a field that fills an entire row (`Sequence Number`,
`Acknowledgment Number`, `(Options and Padding)`), six adjacent 1-bit fields packed into a single
row (the TCP flag bits), and a field spanning two full rows (`Data (variable length)`,
192-255, split per requirement 5 rather than partial-bit-split like the mockup above):

```
--- source (adapted from Mermaid docs: `title "TCP Packet"` frontmatter rewritten as the inline
    `title TCP Packet` directive requirement 9 actually parses -- see caveat below) ---
packet-beta
    title TCP Packet
    0-15: "Source Port"
    16-31: "Destination Port"
    32-63: "Sequence Number"
    64-95: "Acknowledgment Number"
    96-99: "Data Offset"
    100-105: "Reserved"
    106: "URG"
    107: "ACK"
    108: "PSH"
    109: "RST"
    110: "SYN"
    111: "FIN"
    112-127: "Window"
    128-143: "Checksum"
    144-159: "Urgent Pointer"
    160-191: "(Options and Padding)"
    192-255: "Data (variable length)"
--- rendered (mockup; title line centered per requirement 9) ---
                                            TCP Packet
 0                                             15 16                                            31
 ╭────────────────────────────────────────────────┬────────────────────────────────────────────────╮
 │                  Source Port                   │                Destination Port                │
 ╰────────────────────────────────────────────────┴────────────────────────────────────────────────╯
 32                                                                                            63
 ╭────────────────────────────────────────────────────────────────────────────────────────────────╮
 │                                        Sequence Number                                         │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────╯
 64                                                                                            95
 ╭────────────────────────────────────────────────────────────────────────────────────────────────╮
 │                                     Acknowledgment Number                                      │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────╯
 96        99 100            105 106 107 108 109 110 111 112                                          127
 ╭────────────┬──────────────────┬───┬───┬───┬───┬───┬───┬────────────────────────────────────────────────╮
 │Data Offset │     Reserved     │URG│ACK│PSH│RST│SYN│FIN│                     Window                     │
 ╰────────────┴──────────────────┴───┴───┴───┴───┴───┴───┴────────────────────────────────────────────────╯
 128                                          143 144                                          159
 ╭────────────────────────────────────────────────┬────────────────────────────────────────────────╮
 │                    Checksum                    │                 Urgent Pointer                 │
 ╰────────────────────────────────────────────────┴────────────────────────────────────────────────╯
 160                                                                                          191
 ╭────────────────────────────────────────────────────────────────────────────────────────────────╮
 │                                     (Options and Padding)                                      │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────╯
 192                                                                                          223
 ╭────────────────────────────────────────────────────────────────────────────────────────────────╮
 │                                     Data (variable length)                                     │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────╯
 224                                                                                          255
 ╭────────────────────────────────────────────────────────────────────────────────────────────────╮
 │                                     Data (variable length)                                     │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Mockup: UDP header (real-world example, hand-authored)

```
--- source (Mermaid docs, verbatim -- `packet` keyword per requirement 1, `title` directive per
    requirement 9, `+16` shorthand per requirement 2, all now in scope) ---
packet
    title UDP Packet
    +16: "Source Port"
    +16: "Destination Port"
    32-47: "Length"
    48-63: "Checksum"
    64-95: "Data (variable length)"
--- rendered (mockup; title line centered per requirement 9) ---
                                            UDP Packet
 0                                             15 16                                            31
 ╭────────────────────────────────────────────────┬────────────────────────────────────────────────╮
 │                  Source Port                   │                Destination Port                │
 ╰────────────────────────────────────────────────┴────────────────────────────────────────────────╯
 32                                            47 48                                            63
 ╭────────────────────────────────────────────────┬────────────────────────────────────────────────╮
 │                     Length                     │                    Checksum                    │
 ╰────────────────────────────────────────────────┴────────────────────────────────────────────────╯
 64                                                                                            95
 ╭────────────────────────────────────────────────────────────────────────────────────────────────╮
 │                                     Data (variable length)                                     │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────╯
```

**Caveat, updated -- of the three syntax gaps these two real-world examples originally surfaced,
two are now in scope per the maintainer's ask:** the bare `packet` keyword (requirement 1) and
the inline `title <text>` directive (requirement 9), alongside `+N` (requirement 2, added
earlier). The one gap still deliberately out of scope is the YAML-frontmatter spelling of the
title (` ---\ntitle: "..."\n--- `) that Mermaid's own TCP doc example actually uses -- see the
Non-goals entry above for why (it's a generic, cross-diagram-type Mermaid feature, not a
packet-specific one). The TCP mockup above is therefore adapted to use the inline `title TCP
Packet` form instead of the frontmatter the docs show, so it's parseable under requirement 9 as
scoped; the UDP mockup already used the inline form verbatim and needed no adaptation. A fence
using the frontmatter spelling still falls back to raw-fence display (requirement 7).

## Acceptance / verification

- Unit tests for the parser: a multi-bit field, the single-bit shorthand, declaration-order
  preservation, a gap between two explicit ranges raising a parse error (requirement 3), an
  explicit range overlapping the previous field's end raising a parse error (requirement 3), an
  explicit `end < start` raising a parse error, and a `+0` field raising a parse error
  (requirement 2).
- Unit tests for the `+N` cursor-relative shorthand: a `+N` field starting at cursor 0, a `+N`
  field continuing from a prior field's end, and a `+N` field mixed with explicit
  `<start>-<end>`/`<start>` fields in the same diagram, cursor continuing correctly across the mix
  (requirement 2).
- A rendered fixture reproducing the `+N`-mixed-with-explicit-ranges mockup above.
- Unit tests for the `packet` (non-`-beta`) sniff alias (requirement 1) and for the `title <text>`
  directive parse (requirement 9), including a diagram with no `title` line (title omitted from
  the render entirely, not rendered as an empty line).
- A rendered fixture reproducing the UDP mockup above (`packet` keyword, `title`, and `+N` all in
  the same fixture), confirming the title renders centered and bold above the diagram's rows.
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

- **Claude Sonnet 5** (agent), 2026-08-09: Implemented against Requirements 1-9 --
  `viewmd/mermaid/packet/{parser,renderer}.py`, wired into `viewmd/mermaid/__init__.py:render`
  alongside the `er`/`pie` branches. `./run-tests.sh` is green (435 tests: pytest, ruff,
  pip-audit, `tools/issues.py --check`); every pre-existing golden-fixture test for
  flowchart/sequence/ER/pie passed unchanged, satisfying requirement 8's no-regression bar.
  Verified end-to-end through the actual CLI (`viewmd` on a scratch `.md` file with a
  `packet-beta`/`title` fence), not just the module directly.

  Two corrections made to this issue's own requirements while implementing, both against real
  Mermaid source (`mermaid-js/mermaid` on GitHub, since the local `mermaid-ascii`/termaid tooling
  has no packet support to check against and the public docs pages don't cover validation
  semantics): requirement 3 originally claimed non-contiguous fields pass through unvalidated --
  reversed after reading `packages/mermaid/src/diagrams/packet/parser.ts`'s `populate()`, which
  throws on exactly that case; and requirement 9 originally specified a bold title (`wrap_text_bold`)
  -- reversed to plain centered text, since packet has no `color` parameter to gate it behind and
  Non-goals disclaims introducing ANSI. Both are noted inline at the requirements themselves, not
  just here.

  The row/box-drawing proportions (chars-per-bit, header-number column alignment) were
  reverse-engineered from the one real reference example in this issue (termaid's actual output,
  four 16-bit fields) by counting exact character/column positions -- not from any documented
  formula, since none is published and termaid isn't installed locally to test further cases
  against. Two findings from that exercise: (1) each field's cell is `3 * bits - 1` characters
  wide, not the flat `3 * bits` most of this issue's other mockups (the `+N`, TCP, and UDP ones)
  were drawn with -- those mockups are therefore each one character per cell narrower than what
  the actual renderer now produces; a cosmetic difference only, not a structural one, and left
  uncorrected in the mockups themselves as not worth the rework for illustrations already marked
  hand-authored/non-oracle. (2) the header's bit-range numbers align under the box's corner
  columns in a way that isn't simple per-field centering (the first field's header slot is one
  column wider than its box cell, to align under the left corner; no other field gets this
  treatment) -- implemented and matches the reference example's header line exactly. One further
  quirk in that same reference example could *not* be explained or reproduced: the "Source Port"
  content row's label padding is asymmetric (17/19) despite an even total pad (36), while ordinary
  floor/ceil centering (used here, and which exactly matches the reference's *other* three field
  labels) would give 18/18. Left as ordinary symmetric centering rather than chasing an
  unexplained one-field anomaly with no second data point to disambiguate a theory from (per
  Non-goals' explicit no-oracle-to-match-exactly disclaimer); flagging here in case the maintainer
  has termaid source access to check.

  No truncation helper existed anywhere in `viewmd/mermaid/` to reuse (requirement 6's original
  text assumed `viewmd/mermaid/er/` had one; ER actually auto-grows its boxes instead of
  truncating, checked directly rather than assumed) -- added a small local wide-character-safe
  `_truncate`/`_center` in `viewmd/mermaid/packet/renderer.py` instead, covered by
  `test_wide_char_label_truncates_without_destroying_borders` (unicode ellipsis `…`) and the
  `wide_label.mmd` fixture's `.ascii.out` variant (no room for an ASCII `...` ellipsis at that
  width, falls back to a hard character-safe cut with no ellipsis rather than crashing or
  overflowing).

