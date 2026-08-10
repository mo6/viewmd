---
id: VIEWMD-0033
title: Render Mermaid user journey diagrams
status: proposed
area: [render, mermaid]
effort: medium
created: 2026-08-06
updated: 2026-08-06
accepted_by:
accepted_at:
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Render Mermaid user journey diagrams

## Summary

Add a fifth Mermaid diagram type -- `journey` -- alongside the existing flowchart, sequence, ER, and (pending) gantt renderers (`viewmd/mermaid/{flowchart,sequence,er}/`, [VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md)). A user journey diagram (https://mermaid.ai/open-source/syntax/userJourney.html) is a per-task satisfaction score (1-5) plotted across ordered, `section`-grouped tasks, with one or more named actors attached to each task, rendered here as a boxed timeline modelled directly on real Mermaid's own output (see the mock-up below). This is a first version -- see Non-goals for what's deliberately left out.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `journey` fence today -- it falls through every `_is_*_diagram` sniff. User journey diagrams are a distinct Mermaid diagram type from anything currently supported: unlike flowchart/sequence/er's graph-of-nodes shape, or gantt's date-scaled bars, a journey diagram is a boxed timeline -- ordered, `section`-grouped task boxes along a horizontal arrow, each with a dashed drop-line whose depth encodes that task's satisfaction score -- a new rendering shape for `viewmd/mermaid/`, not a variation on an existing one.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `journey` (`viewmd/mermaid/journey/parser.py:sniff`, following the `sniff`/`parse`/`render` module shape already used by `flowchart`/`sequence`/`er`) and wire it into `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
2. MUST parse `title <text>` (optional, rendered above the chart).
3. MUST parse `section <name>` lines, grouping the tasks that follow until the next `section` (or end of diagram) under that section's label, in declaration order.
4. MUST parse a task line of the form `<name>: <score>: <actor1>, <actor2>, ...` where `<score>` is an integer 1-5 and at least one actor is required. MUST reject (fall back per requirement 8) a score outside 1-5 or a task line missing its actor list, rather than silently clamping or defaulting.
5. MUST render each section as its own box (`┌─┐│└┘`), spanning the combined width of its tasks' boxes, and each task as its own box directly below its section's box, in declaration order, left-to-right -- see the mock-up below for the specific layout.
6. MUST render a horizontal timeline arrow beneath the task boxes, spanning the full chart width with an arrowhead (`▶`) at its right end, and a dashed vertical drop-line (`┊`) from each task down to a mood indicator, whose *depth* (number of `┊` rows before the indicator) is proportional to `6 - score` -- a higher score gets a shorter drop, a lower score a longer one, matching real Mermaid's own vertical placement.
7. MUST assign each unique actor name (first-seen order) a distinct marker glyph from a fixed shape set (e.g. `●`, `▲`, `■`, `◆`, ...; `use_ascii`-safe fallbacks per the existing convention in `viewmd/mermaid/grid/canvas.py`), placed on a row directly above each task's box for every actor attached to that task, and render a legend mapping glyph to actor name (first-seen order), since (unlike color) shape alone doesn't self-label.
8. MUST leave a `journey` fence whose content fails to parse untouched (fall back to showing the raw fence), same fallback discipline as the other Mermaid renderers' MUST-NOT-crash requirement.
9. MUST NOT change behavior for any existing recognized Mermaid diagram type (flowchart, sequence, er, and gantt once VIEWMD-0032 lands).

## Non-goals

- Per-actor color (real Mermaid assigns each actor a distinct color for its dot) -- v1 uses distinct marker *shapes* instead, since not every terminal reliably renders truecolor and shape survives `use_ascii` fallback the same way the gantt/flowchart glyph conventions already do. Color MAY be added as a follow-up enhancement layered on top of the shapes, not a replacement for them.
- A literal smiley-face icon at each drop-line's end -- there's no font-independent monospace equivalent of Mermaid's colored circular smiley, so v1 substitutes a short text mood token (`:)`/`:|`/`:(`) instead, per the mock-up below.
- Any interactivity, click handlers, or Mermaid's theming/`%%{init}%%` directives.
- Matching any upstream reference implementation byte-for-byte -- there is no non-Mermaid reference renderer for this diagram type (unlike VIEWMD-0015's flowchart port), so fixtures are necessarily hand-authored/visually-verified, same posture as VIEWMD-0022 and VIEWMD-0032. The score-to-mood-token thresholds below are inferred from a reference screenshot, not a documented Mermaid specification.
- Terminal-width responsiveness beyond a reasonable fixed assumption, matching the other Mermaid renderers' current posture.

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a `_is_journey_diagram`/`_parse_journey`/`_render_journey` import trio and a fifth `if` branch, mirroring the `er` branch (parse-then-render, catching a module-local `ParseError` into `MermaidError`). New module lives at `viewmd/mermaid/journey/` (`parser.py`, `renderer.py`), sibling to the other diagram packages. Follows the same mock-up-driven design process as [VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md) -- there's no upstream ASCII reference to port, so the rendering shape itself is this issue's main open design question.

### Mock-up (pending maintainer review)

Renders the maintainer-supplied example:

```
journey
    title My working day
    section Go to work
      Make tea: 5: Me
      Go upstairs: 3: Me
      Do work: 1: Me, Cat
    section Go home
      Go downstairs: 5: Me
      Sit down: 5: Me
```

**Boxed timeline, modelled directly on real Mermaid's own rendering** (the maintainer supplied a screenshot of `mermaid.js`'s actual output for this exact diagram: boxed section headers, boxed task labels below them with small actor-colored dots at each box's top-left corner, a horizontal timeline arrow, and a dashed drop-line per task ending in a mood face whose *vertical position* encodes the score -- shallow drop for a high score, deep drop for a low one). Adapted to box-drawing/ASCII: `┌─┐│└┘` for both section and task boxes (no shared borders between adjacent boxes, matching the screenshot's visibly separate boxes), `┊` for the dashed drop (box-drawing's own broken-vertical glyph, not a hand-picked substitute), `▶` as the arrow's head, and a `:)"/:|"/":("` mood token in place of the screenshot's smiley-face icon (no font-independent monospace equivalent of a colored circular smiley exists, so this substitutes text in the same spirit `use_ascii` mode already substitutes elsewhere in `viewmd/mermaid/`). The per-actor marker row sits *above* each task box rather than overlapping its top border like the screenshot, since overlapping a marker glyph directly onto a box-drawing corner character would corrupt the border rather than sit visually on top of it the way it can in a graphical renderer. Generated column-exactly (box widths, section-spanning widths, and drop depths all computed from the data, not hand-aligned):

```
My working day

○ Cat          ┌────────────────────────────────────┐  ┌───────────────────────────┐
● Me           │             Go to work             │  │          Go home          │
               └────────────────────────────────────┘  └───────────────────────────┘
               ●           ●              ○●           ●                ●
               ┌──────────┐┌─────────────┐┌─────────┐  ┌───────────────┐┌──────────┐
               │ Make tea ││ Go upstairs ││ Do work │  │ Go downstairs ││ Sit down │
               └──────────┘└─────────────┘└─────────┘  └───────────────┘└──────────┘
       ────────────────────────────────────────────────────────────────────────────▶
                    :)            ┊            ┊              :)             :)
                                  ┊            ┊
                                 :|            ┊
                                               ┊
                                              :(
```

Depth mapping used above: score 5 → 1-row drop, 4 → 2, 3 → 3, 2 → 4, 1 → 5 (linear, `depth = 6 - score`), and mood token: score ≥4 → `:)`, score 3 → `:|`, score ≤2 → `:(`, both directly read off the screenshot's own apparent mapping rather than invented independently. In the "Do work" box, `○●` sit side by side (both `Cat` and `Me` are on that task) -- an inherent limitation of a single row of concatenated glyphs above the box when two-plus actors share a task: it gets visually cramped past two or three actors. This doesn't come up in the maintainer's example beyond this one box, but is worth the maintainer's attention for real-world diagrams with more actors.

Open questions for maintainer sign-off: (a) how a task with 3+ actors should render its marker row beyond simple glyph concatenation -- stack onto a second row, spread the box wider, or accept the concatenation limitation for v1; (b) whether the legend should be sorted by first-appearance order (as shown) or alphabetically; (c) whether the score-to-mood-token thresholds (`≥4`/`==3`/`≤2`) should be codified as a MUST in the requirements above (they currently are, per requirement 6, but the exact threshold values were inferred from a screenshot, not a documented spec, so are worth an explicit sign-off) or left as an implementation detail that can be tuned later without a follow-up issue; (d) whether the marker row sitting *above* the task box (rather than overlapping its top-left corner like real Mermaid) reads clearly enough, or whether an alternative -- e.g. placing actor initials just inside the box's own top border -- should be explored instead.

## Acceptance / verification

- Unit tests for the parser: `section` grouping, task line parsing (name/score/actor-list), rejection of an out-of-range score and a missing actor list.
- A rendered fixture (hand-verified, no upstream binary to diff against per Non-goals) reproducing the maintainer's example above per the mock-up.
- A fixture exercising `use_ascii` mode's fallback glyphs for the marker shape set.
- A fixture covering all three mood-token thresholds (score ≥4, ==3, ≤2) and their corresponding drop depths.
- A malformed `journey` fence (e.g. a task line with a score of `7`) falls back to showing the raw fence rather than crashing viewmd.
- `./run-tests.sh` green.

## Peer review

