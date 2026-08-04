---
id: VIEWMD-0020
title: Render Mermaid sequence-diagram actors as stick-figure glyphs
status: implemented
area: [render, mermaid]
effort: medium
created: 2026-08-04
updated: 2026-08-04
accepted_by: George Moses
accepted_at: 2026-08-04
commits: [035aaff]
related: [VIEWMD-0017]
supersedes: []
changelog: "[1.4.0]"
reason:
---

# Render Mermaid sequence-diagram actors as stick-figure glyphs

## Summary

[[VIEWMD-0017]] made `actor`-declared participants parse and render, but only as ordinary boxes, identical to `participant`. In upstream Mermaid, `actor` is visually distinct: a stick figure rather than a box. This issue draws an actual stick-figure glyph for `actor` participants in the ASCII-art renderer.

## Motivation / problem

Rendering `actor` identically to `participant` is a correct but incomplete port of Mermaid semantics — the two keywords exist specifically to produce different visuals. Users porting diagrams that rely on that visual distinction (e.g. actor = human/external, participant = system) lose that signal in viewmd's output. [[VIEWMD-0017]] explicitly scoped this out as a larger, separate change; this issue is that follow-up.

## Requirements

1. MUST retain, from parsing, whether a declared participant was declared with `actor` vs. `participant` (the parser currently normalizes both to the same participant representation per [[VIEWMD-0017]]).
2. MUST render an `actor` participant's header as a 3-line stick figure (head, arms/torso, legs; box-drawing/ASCII, consistent with the renderer's existing character set) instead of a plain box top, above or in place of the existing box.
3. MUST keep the actor's label/name rendering, lifeline placement, and message-arrow alignment consistent with `participant` boxes, so mixed `actor`/`participant` diagrams still line up correctly.
4. MUST NOT change rendering of existing `participant`-only diagrams.
5. SHOULD keep the stick figure's rendered width close to (or no wider than) the label text width, to avoid unnecessarily widening diagrams that mix actors and participants.
6. MUST pick a stick figure at random, from a fixed set of variants, per actor; when a diagram has multiple actors, each should get a different figure before any variant repeats (falls back to repeating once the set is exhausted). Rendering must accept an optional seedable RNG so tests can be deterministic.

## Non-goals

Re-litigating whether `actor` parses at all — that's settled by [[VIEWMD-0017]]. This issue only concerns the visual glyph.

## Design notes / links

Mermaid's own stick-figure rendering (head circle + body/arms/legs strokes) is the visual reference; the exact ASCII/box-drawing approximation is an implementation decision for this issue, not prescribed here. See `viewmd/mermaid/sequence/` for the existing box-drawing renderer this extends.

The maintainer supplied the concrete 3-line figure variants directly (not sourced from any external site -- an initial attempt to pull reference art from simplemanarchive.com/archive found it to be a JS-rendered gallery with no scrapeable ASCII content). They're kept as `ACTOR_FIGURES` in `viewmd/mermaid/sequence/renderer.py`, a plain list of `(head, arms, legs)` 3-character-wide string tuples, so more can be added later without touching the rendering logic. After trying and dropping several variants that didn't render well (see Peer review), the final five are:

```
 O        o        o        o       \o/
\|/      /.7      <|>      (|)       |
/ \      / \      / \      / \      / \
```

## Acceptance / verification

- A render test for a diagram mixing `actor` and `participant` declarations (e.g. the [[VIEWMD-0017]] reproduction), confirming actors render as 3-line stick figures and participants still render as boxes. Since figure choice is random, this and the tests below seed `render`'s `rng` argument for determinism rather than using a golden file.
- A test confirming that with at least as many actors as figure variants, every variant is used at least once before any repeats.
- A regression test confirming an all-`participant` diagram's output is byte-for-byte unchanged.
- `./run-tests.sh` green.

## Peer review

- **Claude** (agent), 2026-08-04 (first pass, superseded): accepted an initial implementation with a single fixed 2-row glyph (head + arms, no legs, no randomization). The maintainer asked for a fuller 3-line figure with random per-actor selection from multiple variants; superseded by the second pass below.
- **Claude** (agent), 2026-08-04 (second pass): accept. `Participant.is_actor` is set in `_parse_participant` from a separate `_ACTOR_KEYWORD_RE` check (kept apart from `_PARTICIPANT_RE` per VIEWMD-0017's capture-group constraint); implicit participants introduced only by a message default to `is_actor=False`, unchanged from the first pass. `ACTOR_FIGURES` holds eight maintainer-supplied `(head, arms, legs)` 3-char-wide variants, including two added from pasted reference images (one re-adding the asymmetric-legs figure dropped earlier as incomplete); `render()` gained an optional `rng: random.Random | None` argument, shuffles a copy of `ACTOR_FIGURES` per call, and assigns figures to actors round-robin over that shuffle so multiple actors get distinct figures before any repeat (req. 6) -- checked directly: seeding `rng` and rendering one diagram with exactly `len(ACTOR_FIGURES)` actors shows every variant present exactly once. The figure's legs row is merged into the existing top-border row (an actor draws legs there, a plain participant its usual box top) so only the head/arms rows are extra height, and that extra height is reserved only when `any(p.is_actor for p in sd.participants)` -- a no-actor diagram takes the same code path as before this issue existed (req. 4), reverified against the `participant_alias` golden fixture byte-for-byte. All figure rows, the label row, and the connector row are centered at the same `box_width // 2` offset the box-bottom `tee_down` already used, so lifelines/arrows still land correctly in mixed diagrams (req. 3). `box_width` is still derived purely from the label, so a 3-char-wide figure never widens a diagram beyond what its label already required (req. 5). The `actor_alias` fixture from VIEWMD-0017 was removed from the shared upstream-pinned golden-fixture directory (`tests/test_mermaid_sequence.py`'s docstring updated to explain why) since randomized output can't be pinned there; actor coverage now lives in `tests/test_mermaid_sequence_actor_glyph.py` with a seeded `rng` for determinism. `./run-tests.sh` green (188 passed), ruff clean (added `# noqa: S311` on the three `random.Random(...)` call sites -- cosmetic glyph choice, not security-sensitive), pip-audit clean, issues index check green.
- **Claude** (agent), 2026-08-04 (third pass): accept. Two more figures added from maintainer-supplied reference images: `/|>`/`/ 7` (re-adding the previously dropped asymmetric-legs one) and a new `. o`/`(|_`/`@ |` dotted-head figure. `tests/test_mermaid_sequence_actor_glyph.py`'s single-actor test was rewritten to assert structurally (which `ACTOR_FIGURES` entry matched, box/label/connector content) instead of pinning one exact rendered string, since the pool changed size three times in this session and each change silently shifted which figure a fixed seed picks -- the other two tests (`ACTOR_FIGURES`-length-driven, and the no-actor regression) were already pool-size-agnostic. `./run-tests.sh` still green (188 passed) after both additions.
- **Claude** (agent), 2026-08-04 (fourth pass): accept. Maintainer judged three variants as not rendering nicely and had them dropped: `-|-` (straight-arms), `/|>`/`/ 7` (asymmetric legs), and `. o`/`(|_`/`@ |` (dotted head). `ACTOR_FIGURES` is back down to five entries. Because the structural test added in the third pass and the other two tests are all pool-size-agnostic, no test content needed touching -- `./run-tests.sh` green (188 passed) with no diff beyond the `ACTOR_FIGURES` list itself. Also added an "Actors" section to `docs/example.md` demonstrating two actors and a plain participant in one diagram.
- **George Moses** (maintainer), 2026-08-04: accept, "i've tested the implementation - commit and close this out."
