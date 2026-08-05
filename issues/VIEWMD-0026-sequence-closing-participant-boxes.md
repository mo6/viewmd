---
id: VIEWMD-0026
title: Draw a closing participant/actor box at the bottom of sequence-diagram lifelines
status: proposed
area: [render, mermaid]
effort:
created: 2026-08-05
updated: 2026-08-05
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0014]
supersedes: []
changelog:
reason:
---

# Draw a closing participant/actor box at the bottom of sequence-diagram lifelines

## Summary

viewmd's sequence diagrams draw each participant/actor's box (and stick figure, for `actor`) only once, above the top of its lifeline. Real Mermaid (mermaid.live) draws it twice: once above and once again below the last event on the lifeline, closing it off visually. viewmd's renderer currently ends every lifeline with a bare trailing line (`_build_lifeline`) instead of a closing box. This issue is to add the missing bottom box -- a deliberate improvement over the `mermaid-ascii` reference this was ported from, not a byte-for-byte port (confirmed: the real Go binary has the same one-box-only behavior, so this isn't a viewmd-introduced bug, but it is a real, reportable gap relative to actual Mermaid).

## Motivation / problem

Confirmed directly against the real `mermaid-ascii` binary with a plain two-participant, two-message diagram: it renders identically to viewmd, ending each lifeline in a bare `│` with no closing box. That's a real fidelity gap against actual Mermaid's own rendering (which every user of this feature will have seen and expect), not something dictated by VIEWMD-0014's byte-for-byte mandate producing a false constraint here -- there's no reason *not* to add the bottom box, since nothing about matching the upstream Go port's output for the parts it does render depends on omitting it.

## Requirements

1. MUST draw a closing box (top border, label, bottom border) at the end of every participant's lifeline, mirroring the box already drawn at the top -- reusing `viewmd/mermaid/sequence/renderer.py`'s existing `_build_line`/`_top_line`/`_label_line`/`_border_line` helpers (or equivalents) rather than a parallel implementation.
2. MUST draw the closing figure for an `actor` participant too (stick figure), matching the top rendering's `has_actor`/`figure_for_index` handling -- decide whether the actor keeps the *same* random figure at both ends of its own lifeline (recommended, since it's still depicting the same actor) or gets a fresh one; state the choice and reasoning in the implementation.
3. MUST connect each lifeline's last event row into the top of its closing box the same way the existing top box currently connects into the first event row (matching tee/border-junction glyphs already used, e.g. `chars.bottom_left`/`chars.tee_down`/`chars.bottom_right` at the top box's bottom edge has an equivalent at the closing box's top edge).
4. MUST preserve fragment frame borders (`alt`/`loop`/etc.) still closing correctly above the new closing box -- verify against existing fixtures with a fragment as a diagram's last event.
5. MUST update every affected golden fixture under `tests/fixtures/mermaid_sequence/` to the new two-box rendering, hand-verified (no upstream binary to diff against for this specific addition, since upstream doesn't have it -- same testing posture as VIEWMD-0022/0023/0025).

## Non-goals

- Changing the top box's rendering, spacing, or the participant/actor header logic (VIEWMD-0020) -- this only adds a mirrored closing box, reusing that logic rather than modifying it.
- Any other sequence-diagram rendering-fidelity gap relative to real Mermaid not specifically about the missing bottom box.
- The Mermaid flowchart issues (VIEWMD-0022/0023/0025) -- unrelated diagram type.

## Design notes / links

VIEWMD-0014 (`issues/archive/VIEWMD-0014-mermaid-sequence-diagrams.md`) is the byte-for-byte baseline this diverges from for the first time (every other sequence-diagram issue since has stayed within it: VIEWMD-0017, VIEWMD-0020, VIEWMD-0021). `viewmd/mermaid/sequence/renderer.py:render` builds the top box via `_build_line` calls with `_top_line`/`_label_line`/`_border_line` closures (lines ~161-201) and currently ends the diagram with a single `lines.append(_build_lifeline(layout, chars))` (line ~204) -- that's the line to replace with the closing box.

## Acceptance / verification

- A rendered diagram (two participants, one actor, one plain) shows a closing box/figure at the bottom of every lifeline, matching the top one's label and glyph choice for actors.
- A diagram whose last event is a fragment (`alt`/`loop`) still renders its frame border correctly above the closing boxes.
- Updated fixtures in `tests/fixtures/mermaid_sequence/`, hand-verified.
- `./run-tests.sh` green.

## Peer review

Left blank until implemented and tested; filled in as part of the Definition of Done landing gate.
