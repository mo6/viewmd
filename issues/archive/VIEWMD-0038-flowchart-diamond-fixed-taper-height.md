---
id: VIEWMD-0038
title: Render flowchart diamonds as a flat single-row lozenge, and condense connector spacing
status: implemented
area: [render, mermaid]
effort: high
created: 2026-08-08
updated: 2026-08-08
accepted_by: George Moses
accepted_at: 2026-08-08
commits: [4ae7580]
related: [VIEWMD-0022, VIEWMD-0036, VIEWMD-0037]
supersedes: []
changelog: "[1.10.0]"
reason:
---

# Render flowchart diamonds as a flat single-row lozenge, and condense connector spacing

## Summary

An earlier draft of this issue proposed shrinking the diamond's multi-row diagonal taper to a fixed 1-2 rows above/below the label, while keeping the taper itself. The maintainer instead wants a more radical redesign: drop the multi-row taper entirely and render a diamond as a flat-topped/bottomed "lozenge" -- rounded corners, with the same `◇` (WHITE DIAMOND) glyph marking all four attachment points (UP and DOWN on the flat top/bottom border, LEFT and RIGHT on the content row). This makes a diamond exactly as tall as a same-content rectangle -- 1 row per label line plus 2 border rows, with no separate taper term at all. The maintainer also wants two small companion glyph changes to `subroutine` and `cylinder` nodes, and both horizontal and vertical connectors shortened so the whole diagram reads as condensed as possible -- all from the same sketch and a follow-up compound-diagram example.

## Motivation / problem

`docs/mermaid-examples.md` still shows diamonds much taller than their rectangle-family neighbors even after VIEWMD-0037's margin-tightening pass, because that fix could only shrink the *margins* around the taper's inherent row-count-scales-with-label-width coupling (see VIEWMD-0037's own Design notes), not remove the coupling itself. The maintainer's own before/after sketch for the "Node shapes" example makes the target unmistakable:

Current (real rendered output, the "Node shapes" second example in `docs/mermaid-examples.md`):

```
┌────────────┐     ╭──────────╮        /▔▔▔\
‖            ‖     │          │       /     \
‖ Subroutine ├────►│ Cylinder ├────►/ Diamond \
‖            ‖     │          │      \       /
└────────────┘     ╰══════════╯       \▁▁▁/
```

Maintainer's proposed target (verbatim from the maintainer's sketch -- verified self-consistent: every border row's character count matches its content row exactly):

```
┌──────────────┐   ╭══════════╮   ╭────◇────╮
││ Subroutine │├──►│ Cylinder ├──►◇ Diamond ◇
└──────────────┘   ╰──────────╯   ╰────◇────╯
```

Four things changed in that sketch: the diamond collapsed from a 5-row taper to a 3-row flat lozenge (matching the rectangle's own height exactly, not just "closer to it") and uses `◇` uniformly on all four sides rather than a distinct left/right glyph; `subroutine`'s single `‖` side glyph became a doubled `││` (padding around the label unchanged); `cylinder`'s heavy/light border weighting flipped (heavy `═` now on top instead of the bottom); and the arrows connecting all three shrank from 4 dashes (`────►`) to 2 (`──►`), shortening every connector in the diagram to make it read as condensed as possible.

The maintainer followed up with a full compound-diagram transformation (the "Branching and labelled edges" example) confirming the condensing goal extends to *vertical* connector length too, not just horizontal:

Current (real rendered output):

```
┌───────────┐
│   Start   │
└─────┬─────┘
      │
      │
      │
      │
      ▼
    /▔▔▔\
   /     \
  /       \
 /         \
/ Decision  \──── no ─────┐
 \         /              │
  \       /               │
   \     /                │
    \▁▁▁/                 │
      │                   │
      │                   │
     yes                  │
      │                   │
      ▼                   ▼
┌───────────┐        ┌─────────┐
│   Do it   │        │ Skip it │
└───────────┘        └─────────┘
```

Maintainer's proposed target (latest, best-aligned revision -- verified self-consistent below):

```
┌───────────┐
│   Start   │
└─────┬─────┘
      │
      ▼
╭─────◇─────╮
◇  Diamond  ◇── no ──┐
╰─────◇─────╯        │
      │              │
     yes             │
      │              │
      ▼              ▼
┌───────────┐   ┌─────────┐
│   Do it   │   │ Skip it │
└───────────┘   └─────────┘
```

Beyond the diamond's own shrink, two connector-length changes are visible: the unlabeled `Start`→`Decision` arrow shortened from 4 blank rows + arrowhead (5 rows) to 1 blank row + arrowhead (2 rows); and the labeled `yes` branch shortened from 2 blank rows + label + 1 blank row + arrowhead (5 rows) to 1 blank row + label + 1 blank row + arrowhead (4 rows) -- a smaller reduction, and, as Design notes below explains, one that can't come from the same single constant as the unlabeled case.

## Requirements

1. MUST render a diamond as a rounded-corner box the same shape family as `round`/`stadium`/`circle` -- 1 row per label line, no extra taper rows -- with the same `◇` character marking all four attachment points: centered in an otherwise flat top border (UP), centered in an otherwise flat bottom border (DOWN), and immediately left and right of the content on every content row (LEFT/RIGHT).
2. MUST size a diamond exactly like a rectangle-family node: `label_lines` content rows plus 1 top and 1 bottom border row, with no term coupling height to width. (This is a stronger, simpler result than VIEWMD-0037's approach: because height no longer depends on width at all, both caveats VIEWMD-0037 and this issue's earlier draft had to document -- the "long label floor" and the "sibling-column" interaction -- stop applying to diamonds entirely. A diamond's height depends only on its own label's line count, exactly like every other shape.)
3. MUST keep multi-line `<br>` labels packing one row per line with no blank row between them (matching the rectangle-family convention from VIEWMD-0036), with the `◇` LEFT/RIGHT glyph present on every content row, not just one.
4. MUST change `subroutine`'s side-border glyph from the single `‖` (`viewmd/mermaid/grid/canvas.py:309`) to a doubled pair of thin vertical bars on both left and right sides, matching the maintainer's sketch, keeping the existing 1-space horizontal padding around the label unchanged. The existing convention where an attaching edge replaces the border glyph with a `├`/`┤`/`┬`/`┴` junction character stays -- it now replaces the *second* of the two bars, not the single glyph.
5. MUST swap `cylinder`'s heavy/light horizontal border weighting (`viewmd/mermaid/grid/canvas.py:311`): the heavy double line (`═`) moves to the top border, the light line (`─`) to the bottom -- the reverse of today.
6. MUST reduce the default horizontal edge/arrow gap between nodes (`PADDING_X`, `viewmd/mermaid/flowchart/parser.py:17`, currently `5`) to `3`, verified to reproduce the maintainer's sketch exactly (`5` renders `────►`, `3` renders `──►`) -- this is a deliberate divergence from the upstream `mermaid-ascii` reference's own default of `5` (confirmed identical in `pkg/diagram/testutil/testutil.go`), consistent with this project's precedent of diverging toward a denser default (VIEWMD-0036, VIEWMD-0037). `PADDING_X` remains a user-overridable Mermaid directive value (`viewmd/mermaid/flowchart/parser.py:389`) -- only the *default* changes.
7. MUST NOT change `round`, `stadium`, `circle`, or plain rectangle sizing/glyphs -- only `subroutine`, `cylinder`, and `diamond` are in scope, per the maintainer's sketch.
8. MUST keep the existing UP/DOWN/LEFT/RIGHT attachment-cell conventions every other shape already follows (an edge attaches at the same relative grid cell regardless of shape).
9. SHOULD apply the same treatment in the `ASCII` charset using an ASCII-safe substitute for `◇` (e.g. `<>`-style corner glyphs, or a plain `+`; exact choice left to implementation and visual review, since ASCII has no diamond glyph).
10. MUST reduce the default vertical edge/arrow gap (`PADDING_Y`, `viewmd/mermaid/flowchart/parser.py:18`, currently `5`) to `2` for an *unlabeled* vertical edge, verified to reproduce the maintainer's sketch exactly (`5` renders 4 blank rows + arrowhead; `2` renders 1 blank row + arrowhead). Same divergence-from-upstream rationale as requirement 6 (`PaddingY` defaults to `5` in the upstream reference too); `PADDING_Y` remains user-overridable.
11. MUST separately reserve enough extra row height for a *labeled* vertical edge that its label renders with exactly 1 blank row above and 1 below (label + 2, not just whatever `PADDING_Y` alone produces) -- verified empirically that no single `PADDING_Y` value satisfies both requirement 10's unlabeled target and this labeled target simultaneously (see Design notes). This needs a new mechanism: `_determine_label_line` (`viewmd/mermaid/flowchart/graph.py:538-582`) already reserves extra *column* width for a labeled edge's text (both the horizontal- and vertical-line branches bump `self.column_width[middle_x]`, `graph.py:582`); it has no equivalent *row*-height reservation for a vertical edge's label today. Add one, mirroring the existing column-width reservation but sizing `row_height` at the label's row instead.

## Non-goals

- Changing `round`, `stadium`, `circle`, or rectangle sizing/glyphs -- only `subroutine`, `cylinder`, and `diamond` are in scope, per the maintainer's sketch.
- Rectangle-family sizing (VIEWMD-0036 territory) -- only edge/arrow *gap* length (requirements 6, 10, 11), not node size, is in scope here.
- A guarantee about exact border-dash counts/centering of the `◇` marker for every label width -- implementation detail, verified visually rather than specified to the character here.

## Design notes / links

**This is a bigger structural change than VIEWMD-0037's margin tightening, not an extension of it.** Diamonds currently have their own bespoke drawing function, `_draw_diamond` (`viewmd/mermaid/grid/canvas.py:396-473`), because a real tapered rhombus is genuinely different geometry from every other shape's uniform-border box. Under this redesign, a diamond is no longer geometrically different from `round`/`stadium`/`circle`/`subroutine`/`cylinder` -- it becomes just another set of border/side glyphs drawn by the *same* mechanism those shapes already use (`draw_box` + `_box_glyphs`, `canvas.py:244-293`). The one wrinkle: `draw_box`'s current top/bottom border loop fills the entire row with one repeated character (`glyphs.h_top`/`glyphs.h_bot`); it has no notion of "flat line with one different character in the middle." That loop needs a small extension (or diamond needs a thin wrapper around it) to place a single center-marker glyph after filling the row. Once that exists, `diamond_tip_half_width`, `diamond_intrinsic_height`, `diamond_height_for_width`, and `_draw_diamond` itself all become dead code removable by this issue, and `NodeShape.DIAMOND`'s special-case branch in `graph.py:333-368`'s `_set_column_width` collapses to the same `else` branch every other shape already uses (`cols`/`rows` from label width/height, no taper term) -- see `graph.py:366-371` for that existing branch to match.

**On the choice of `◇` for all four sides:** an earlier version of this issue (before the maintainer's second sketch) explored a distinct pointed glyph for LEFT/RIGHT (`<`/`>`, or a recommended `◁`/`▷`) separate from `◇` on top/bottom. The maintainer's latest sketch uses `◇` uniformly on all four sides instead -- simpler (one glyph, one font-coverage decision, not two) and arguably more legible as "this is a diamond" precisely because the same corner mark repeats on every side. That superseded the earlier `◁`/`▷` recommendation; no separate LEFT/RIGHT glyph decision remains for the `UNICODE` charset.

**Verified the maintainer's sketches are internally width-consistent** (unlike an earlier sketch in this issue's first draft, which had a border one character narrower than its content row): in the "Node shapes" sketch, `┌──────────────┐`/`││ Subroutine │├`/`└──────────────┘` are all exactly 16 characters, `╭══════════╮`/`│ Cylinder ├`/`╰──────────╯` are all exactly 12, and `╭────◇────╮`/`◇ Diamond ◇`/`╰────◇────╯` are all exactly 11; in the later, best-aligned "Branching and labelled edges" sketch the diamond widened slightly to 2 spaces of padding each side (`╭─────◇─────╮`/`◇  Diamond  ◇`/`╰─────◇─────╯`, all exactly 13 characters) and left-aligns flush with the `Start`/`Do it` rectangles above and below it in the same grid column -- both are legitimate variations of the same design (exact padding is an implementation/visual-review detail per the Non-goals), not a contradiction.

**The diamond's bottom corners are fully rounded** (`╰╯`, matching the top `╭╮`), not the sharp `└┘` an earlier revision of the maintainer's sketch used -- consistent with every other rounded-corner shape (`round`, `cylinder`) already using `╭╮╰╯` uniformly on all four corners.

**`PADDING_X = 3` was verified empirically, not assumed:** rendering `graph LR\n A[X] --> B[Y]` with `PADDING_X` overridden to `3` on the current (unmodified) checkout reproduces `├──►│` exactly, matching the maintainer's sketch's connector length character-for-character; the current default `5` renders `├────►│`. This confirms requirement 6's specific value directly rather than guessing at "shorter."

**`PADDING_Y = 2` alone does not reproduce the maintainer's labeled-edge target -- verified empirically, a real finding, not a guess.** Rendering the "Branching and labelled edges" diagram (using a plain rectangle in place of the not-yet-implemented compact diamond, to isolate the padding effect from the old taper's distortion) at each candidate `PADDING_Y`:
- `PADDING_Y = 2`: unlabeled `Start`→`Decision` renders exactly 1 blank + arrowhead (matches requirement 10) -- but the labeled `yes` edge collapses to 0 blank rows on either side of the label (`yes` immediately followed by `▼`, no gap at all).
- `PADDING_Y = 4`: the labeled `yes` edge renders exactly 1 blank + label + 1 blank + arrowhead (matches requirement 11) -- but the unlabeled edge now renders 3 blank rows + arrowhead, overshooting requirement 10's 1-blank target by 2 rows.

No single value satisfies both simultaneously, because today's `_determine_label_line` never reserves extra row height for a vertical label -- the label is simply centered (`_paint_arrow_label`'s `_inset_line(line, 1, 2)`, `graph.py:915-919`) within whatever `row_height` the base `PADDING_Y` already produced for that gap, the same allocation an unlabeled edge gets. Requirements 10 and 11 are two separate, independently-verified changes for this reason -- lowering the shared base constant, then adding a per-labeled-edge row reservation on top of it, not one combined tweak.

**Precise before/after height comparison for real doc examples**, computed directly from requirement 2's formula (`label_lines + 2`, fully decoupled from width) against today's actual measured heights (VIEWMD-0037's baseline): `{OK}` 5 → 3 rows, `{Decision}` 9 → 3 rows, `{Cache hit?}` 9 → 3 rows, `{Authenticated?}` 13 → 3 rows, `{Authorized?}` 9 → 3 rows, `{Path?}` 11 rows *(already stretched well past its own 7-row standalone baseline by its `[Handle left]` sibling under the current taper design's reach coupling)* → 3 rows, and `{Ready to<br>ship?}` (2-line label) 9 → 4 rows. The `{Path?}` case is the clearest illustration of requirement 2's structural improvement: today it's taller than every other single-line-label diamond purely because of the sibling-column/taper-reach interaction; under this redesign it renders at the same flat 3 rows as `{OK}`, because nothing about a diamond's height depends on its width anymore. Full compound-diagram mockups (the "Nested decisions", "Branching and labelled edges", "Decision with stadium terminals" sections in `docs/mermaid-examples.md`) are not hand-fabricated here -- getting arrow-routing and connector-length details right for a diagram this different from today's requires the real renderer, not manual ASCII construction; verifying those end-to-end is the Acceptance criteria below.

## Acceptance / verification

- `./run-tests.sh` green after regenerating every flowchart golden fixture under `tests/fixtures/mermaid_flowchart/` (the `PADDING_X`/`PADDING_Y` default changes affect the spacing of every flowchart fixture, not just those with a diamond/subroutine/cylinder -- expect a wide regeneration, each hand-diffed against its pre-change version to confirm only connector length/node shape changed, nothing else drifted).
- Visual check: render `docs/mermaid-examples.md` end-to-end and confirm every diamond now renders at exactly `label_lines + 2` rows (matching a same-content rectangle), `◇` marks all four attachment points, `subroutine` shows its doubled side-bar, `cylinder`'s heavy line is now on top, and every arrow connector (horizontal and vertical) is visibly shorter than before.
- Visual check: an edge attaching to a diamond's LEFT/RIGHT/UP/DOWN side still attaches flush with no gap, at the new glyph positions.
- Visual check: `{Path?}` in "Decision with stadium terminals" now renders at the same height as every other diamond, confirming requirement 2's decoupling claim empirically (it was the case most affected by the old taper-reach coupling).
- Visual check: a multi-line (`<br>`) diamond label packs one row per line with `◇` present on each side of each row, no blank row between lines.
- Visual check: render "Branching and labelled edges" and confirm it matches the maintainer's compound-diagram target -- unlabeled vertical edges at 1 blank row + arrowhead (requirement 10), labeled vertical edges at 1 blank + label + 1 blank + arrowhead (requirement 11), independently of each other.

## Peer review

- (agent, independent) First pass found two blocking bugs, both exposed by the smaller `PADDING_X`/`PADDING_Y` defaults removing accidental slack: (1) an edge attaching to `subroutine`'s doubled-bar LEFT/RIGHT side landed its arrowhead one pixel too far in, overwriting the outer bar instead of stopping in the gap before it -- no existing fixture had a subroutine node with an incoming edge, so it slipped through fixture regeneration; (2) `_has_incoming_edge_from_outside_subgraph` only fired when the *target* node was itself inside a subgraph, so an edge leaving a subgraph to an external node (e.g. `subgraph_nested`'s `A --> D`) never got clearance, letting the subgraph's own border merge into the external node's box. Also independently confirmed requirements 1-3/5/6/9-11, the three subgraph-overhead-axis/clamp/innermost-subgraph fixes found during fixture regeneration, and flagged two non-blocking visual-density artifacts (arrowhead glyphs overlapping unrelated routed lines' dashes, no node/label corruption) in `obstacle_routing`/`self_loop` at the new `PADDING_Y=2` default -- assessed as an acceptable known trade-off, not a blocker. Verdict: not ready to land as reviewed.
- (implementer) Fixed both blocking findings: (1) `graph._attach_border_extra`/`_draw_path` now stop a line/arrowhead short of a node's *entire* border strip width, not just 1 pixel, so `subroutine`'s outer bar is never overwritten by an arriving edge; (2) `_has_incoming_edge_from_outside_subgraph` no longer early-returns when the target node has no subgraph of its own. Re-verified both repro cases directly, regenerated all fixtures again, `./run-tests.sh` pytest/issues/pip-audit all green (324 passed; the only non-zero exit is 10 pre-existing `poc/` ruff `E741`/`E501` findings, confirmed via `git stash` to predate this branch and untouched by this diff). This fix itself has not had a second independent pass -- flagging that to the maintainer rather than asserting it.
