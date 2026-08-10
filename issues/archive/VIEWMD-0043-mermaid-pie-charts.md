---
id: VIEWMD-0043
title: Render Mermaid pie charts
status: implemented
area: [render, mermaid]
effort: medium
created: 2026-08-09
updated: 2026-08-09
accepted_by: George Moses
accepted_at: 2026-08-09
commits: [e114c32]
related: []
supersedes: []
changelog: "[1.12.0]"
reason:
---

# Render Mermaid pie charts

## Summary

Add a Mermaid diagram type -- `pie` -- alongside the existing flowchart, sequence, and ER
renderers (`viewmd/mermaid/{flowchart,sequence,er}/`) and the diagram types proposed in
[VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md) through
[VIEWMD-0042](VIEWMD-0042-mermaid-gitgraph-diagrams.md). A Mermaid `pie` chart
(https://mermaid.js.org/syntax/pie.html) is a set of labeled slices with numeric values.
This issue's design is two-tiered: when color is available, render an actual circular pie --
wedges filled with distinct truecolor ANSI regions, computed on a character grid with an
aspect-ratio correction so it reads as round rather than egg-shaped -- and fall back to a
horizontal bar chart (one bar per slice, sized to its share of the total) whenever color isn't
available: `NO_COLOR` set, `--color never`, non-tty output, or `--ascii` requested. A monochrome
circular pie was prototyped and rejected first -- see Design notes and `poc/pie/pie_poc.py` for
why -- so the bar chart is not a placeholder pending a better circular design, it is the correct
no-color rendering on its own terms.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `pie` fence today --
it falls through every `_is_*_diagram` sniff. Pie charts are a common, simple Mermaid diagram type
and, of the eight diagram types termaid supports that viewmd does not yet track
(state, architecture, pie, treemap, mindmap, quadrant, xychart, packet), this was originally scoped
as the smallest: no layout algorithm, just proportional bar-width math. Prototyping a colored
circular rendering (`poc/pie/pie_poc.py`) found that color changes the calculus enough to be worth
doing as the primary rendering rather than dismissing a circular pie outright, the way `termaid` (a
sibling terminal-Mermaid renderer, `src/termaid/renderer/piechart.py`) does -- but it surfaced a
real gap in viewmd's current architecture along the way: **there is no way for a Mermaid renderer to
know whether color is enabled.** `viewmd/__main__.py` already resolves `--color`/`NO_COLOR` into a
single `color: bool`, but that value stops at `viewmd/render.py:render_markdown`'s Rich `Console`
construction -- it is never threaded into `viewmd/mermaid/preprocess.py:render_mermaid_blocks` or
`viewmd/mermaid/__init__.py:render`, both of which only know about `use_ascii` today. Nothing in the
shipped renderers needed color before, so this was never noticed; a pie chart that wants to look
different with and without color is the first diagram type that does.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `pie` (`viewmd/mermaid/pie/parser.py:sniff`,
   following the `sniff`/`parse`/`render` module shape already used by the other diagram packages)
   and wire it into `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
2. MUST parse an optional `title <text>` line, an optional `showData` modifier on the `pie` line
   itself (appending each slice's raw value next to its percentage), and one `"<label>" : <value>`
   line per slice (`<value>` a non-negative integer or decimal), tolerating `%%` comments and blank
   lines anywhere in the block.
3. MUST thread a color-enabled flag end to end through the Mermaid render pipeline, since none
   exists today (see Motivation): `viewmd/__main__.py`'s already-resolved `--color`/`NO_COLOR`
   boolean into `render_markdown` (`viewmd/render.py`) into `render_mermaid_blocks`
   (`viewmd/mermaid/preprocess.py`) into `viewmd/mermaid/__init__.py:render`, as a new keyword
   parameter sitting alongside the existing `use_ascii`. Every other diagram type's renderer
   signature gains the parameter but MUST ignore it (no behavior change) until it has a use for it
   -- this issue is the only one that reads it for now.
4. MUST render a circular pie when the color flag from requirement 3 is enabled and `use_ascii` is
   false: each slice is a wedge on a character grid, filled with a distinct truecolor ANSI region
   (`\x1b[38;2;r;g;bm`, the same embedding-raw-ANSI-in-plain-text approach as
   `viewmd/mermaid/grid/canvas.py:wrap_text_in_color`, corrected in Design notes below -- that
   helper is currently unused, not already wired up as an earlier draft of this issue claimed), a
   bold title (requirement 7) centered above it, each slice's percentage inside its wedge, and a
   legend (one line per slice: a color swatch plus its label) to the right, vertically centered --
   per `poc/pie/pie_poc.py:render_circle` and mock-up 3 below.
4a. MUST anti-alias the circle's outer silhouette with Unicode quadrant block characters
   (`▘▝▖▗▀▄▌▐▚▞▛▜▙▟█`, Block Elements) rather than leaving a stepped, jagged edge or a separate
   border-ring character: each cell samples 4 sub-points against the ellipse boundary independently
   and renders the one glyph (of 16) matching exactly which sub-points are inside, so every boundary
   cell gets a partial-fill glyph, not just whichever cells happen to match a specific pattern. This
   is the third design tried for the silhouette, and the only one that held up -- see Design notes
   for the two that were prototyped and visually rejected first (a flat ring character, and per-cell
   directional tick marks), both confirmed worse than no separate border treatment at all before this
   approach was tried.
5. MUST correct for terminal character cells being roughly twice as tall as wide when computing the
   circle, so it reads as round rather than an ellipse: an `(x/rx)^2 + (y/ry)^2 <= 1` grid mask with
   `ry` roughly `rx * aspect` for a tunable `aspect` constant (0.42 empirically verified against one
   real terminal, matching `poc/pie/pie_poc.py:render_circle`'s default -- not hardcoded to exactly
   0.5/2:1, since that ratio is a guess this script cannot verify, see Design notes). The wedge
   *angle* test (which slice a cell belongs to) MUST use these same aspect-corrected coordinates, not
   raw unscaled grid `dx,dy` -- using unscaled coordinates skews wedge boundaries away from their
   correct on-screen angle by the same amount the row compression itself introduces.
5a. MUST expose the aspect constant from requirement 5 as a user-settable override, not only an
   internal constant -- this cannot be auto-detected (see Design notes on why), so a circle that
   renders oval in a given terminal needs a one-setting fix available to the user, not a bug report.
   `poc/pie/pie_poc.py --aspect` is the CLI-flag precedent; viewmd's shipped equivalent (a flag, a
   config file setting, or an environment variable) is an implementation decision for this issue.
5b. MUST size the circle's default radius relative to the detected terminal width rather than a
   fixed constant, so a pie chart doesn't default to being wildly oversized (or tiny) relative to the
   document it's embedded in: `poc/pie/pie_poc.py:_default_radius` computes 60% of the largest radius
   whose full render (circle plus legend) still fits the terminal width, floored at a sane minimum --
   viewmd already has terminal-width detection (used for `--width`/full-terminal rendering elsewhere)
   to reuse here rather than reimplementing `poc/pie/pie_poc.py:_terminal_width`'s
   `shutil.get_terminal_size` call from scratch. An explicit radius override (as in the POC's
   `--radius`) MAY still be offered, but MUST NOT be required for a reasonably-sized default.
6. MUST render each slice's percentage label at its wedge's centroid when the wedge's angular span
   exceeds a reasonable legibility threshold, and outside the circle (with the label positioned
   along the same mid-angle leader) when it doesn't -- a very thin slice (e.g. the 3% `Rats` wedge
   in the reference example) cannot hold text inside itself. `poc/pie/pie_poc.py` uses 25 degrees as
   that threshold; the exact cutoff is an implementation decision for this issue, not dictated here.
6a. MUST NOT leave more than one blank row between the title and the first row of actual content
   (the circle, or an outside-placed label from requirement 6, whichever comes first): the margin
   requirement 5's grid needs above the circle for an outside label to have somewhere to sit can
   otherwise stack a blank row, the label row, and *another* blank row before the circle itself
   begins, reading as 2-3 empty lines instead of the single deliberate separator between the title
   and everything below it. `poc/pie/pie_poc.py:render_circle` trims every blank row ahead of the
   circle's first actual fill glyph (keeping any label text in between) rather than only stripping a
   literal leading blank line, since the extra blank row here sits *after* the label, not before it.
7. MUST render the title bold (requirement 4's circular case and requirement 8's bar-chart fallback
   alike) via a raw ANSI bold escape (`\x1b[1m<text>\x1b[0m`), gated by the *same* color-enabled
   flag as every other ANSI attribute this issue emits -- not an independent always-on escape. This
   corrects an earlier draft of this issue, which treated bold as exempt from the color Non-goal;
   `poc/kanban/kanban_poc.py`'s `Colorizer` already establishes the repo's actual precedent (one
   `enabled` flag gates fg color *and* underline together), and `poc/pie/pie_poc.py`'s `Colorizer`
   follows the same rule for fg color and bold. A genuinely no-ANSI terminal (piped output,
   `NO_COLOR`, `--color never`) should see zero embedded escapes, not a half-styled result.
8. MUST render a horizontal bar chart -- one row per slice, in declaration order: the label
   right-aligned in a fixed-width column (sized to the longest label), a bar filled proportionally
   to `value / sum(values)` against the widest bar in the chart, and a trailing percentage (one
   decimal place, matching Mermaid's own `%.1f%%` convention) -- whenever requirement 3's color flag
   is disabled, or `use_ascii` is true regardless of the color flag. `use_ascii` MUST also switch the
   bar's fill glyph to an ASCII-safe character (`#`, matching the existing `use_ascii` convention
   used elsewhere in `viewmd/mermaid/`) instead of `█`, per `poc/pie/pie_poc.py:render_bar`.
9. MUST leave a `pie` fence whose content fails to parse (e.g. a slice line missing its `:`
   separator, or a negative value) untouched -- fall back to showing the raw fence, same fallback
   discipline as the other Mermaid renderers' MUST-NOT-crash requirement.
10. MUST NOT change the rendered output of any existing recognized Mermaid diagram type -- the new
    color-flag parameter (requirement 3) is additive and every other renderer ignores it.

## Non-goals

- A monochrome/no-color circular pie -- prototyped and rejected (see Design notes): character-grid
  wedge boundaries are visibly jagged without color to soften them, the terminal-font aspect-ratio
  assumption (requirement 5) is unverifiable and fragile, and only 2-3 fill patterns stay
  distinguishable without color, worse than the bar chart's equivalent problem since a pie has no
  separate label row to lean on. The bar-chart fallback (requirement 8) is the deliberate no-color
  answer, not a stand-in for a circular design not yet found.
- Slice ordering by value (Mermaid renders slices in declaration order for the legend; this issue
  keeps that order rather than sorting descending by value), in both the circular and bar-chart
  rendering.
- A slice palette beyond a small fixed rotation (`poc/pie/pie_poc.py:SLICE_COLORS`, six
  approximate-Mermaid-default hues cycling for a seventh-plus slice) -- matching Mermaid's own
  `%%{init: {"theme": ...}}%%`-driven palette, or letting the user choose one, is deferred.
- The `%%{init: {"pie": {...}}}%%` config keys Mermaid added in v11.16.0+: `textPosition` (radial
  label position) and `donutHole` (punches a hole for a donut look) remain out of scope even for the
  now-circular rendering -- both assume sub-character positioning precision a character grid cannot
  give. `legendPosition` (top/bottom/left/right/center) is closer to relevant now that requirement 4
  renders an actual legend, but a single fixed position (right of the circle, matching Mermaid's own
  default and `poc/pie/pie_poc.py`) is sufficient for v1; making it configurable is a follow-up.
  `highlightSlice` (emphasize one slice by label) is a natural fit for the new per-slice color
  (brightening, or an outline) but is deferred to keep this issue's scope to the two renderings
  already described.
- Matching any upstream reference implementation byte-for-byte -- the local `mermaid-ascii` Go
  oracle used for differential-testing flowchart/sequence/ER has no pie-chart support, so fixtures
  here are hand-authored/visually-verified, same posture as VIEWMD-0032 onward. termaid's own bar
  rendering (mock-up 1 below) is a useful cross-check for the fallback path, not an oracle to match
  exactly, and has no circular rendering to cross-check against at all.

## Design notes / links

**`poc/pie/pie_poc.py` is the implementation example for this issue -- read it before writing
`viewmd/mermaid/pie/`, don't re-derive the design from this text alone.** Every layout constant,
formula, and glyph choice cited by name in the Requirements above (the quadrant-block lookup table,
the aspect-corrected angle math, the thin-wedge label threshold, the default-radius formula, the
blank-row trim) exists as runnable, already-debugged code there, not just as prose here -- several
of them (the aspect-angle interaction in requirement 5, the blank-row trim in requirement 6a) were
bugs caught and fixed *in that script* through actual visual review, documented inline as comments
at the exact line they apply to. Porting logic out of the issue text by hand risks re-introducing a
mistake the POC already ruled out; porting it out of the script does not.

`viewmd/mermaid/__init__.py` is the dispatch point: add a
`_is_pie_diagram`/`_parse_pie`/`_render_pie` import trio and a new `if` branch, mirroring the `er`
branch (parse-then-render, catching a module-local `ParseError` into `MermaidError`). New module
lives at `viewmd/mermaid/pie/` (`parser.py`, `renderer.py`), sibling to the other diagram packages.

**The color-flag plumbing (requirement 3) is the part of this issue that isn't self-contained to
the new `pie/` package.** Four call sites need the new parameter threaded through in order:
`viewmd/__main__.py` (already resolves `--color`/`NO_COLOR`, per its existing
`# auto: NO_COLOR (https://no-color.org) wins over tty detection` comment -- nothing to add here,
just don't drop the value it already has), `viewmd/render.py:render_markdown` (currently only uses
its `color: bool` to build the Rich `Console`; needs to pass it down into the preprocessing pass
before Rich ever sees the body), `viewmd/mermaid/preprocess.py:render_mermaid_blocks` (currently
calls `render(mermaid_source)` with no color awareness at all), and
`viewmd/mermaid/__init__.py:render` (gains the new parameter and passes it to `_render_pie`; every
other `_render_*` call in this dispatch function keeps its current signature plus an ignored
parameter, per requirement 10). Get this wrong in one direction and `--color never`/`NO_COLOR`
leaks a colored circular pie into piped/logged output; get it wrong in the other and `--color
always` on a real tty still only shows the bar-chart fallback.

**Correction to an earlier draft of this issue:** requirement 4 above cites
`viewmd/mermaid/grid/canvas.py:wrap_text_in_color` (a truecolor-ANSI-wrap helper, same escape
pattern this issue needs) as an *existing* precedent for embedding raw ANSI into Mermaid-rendered
output. That's not accurate -- the function exists but is dead code today: nothing in
`viewmd/mermaid/flowchart/` or anywhere else calls it, and no test exercises it. This issue would be
the first live caller of that pattern, not a second one. (Whether `style`/`classDef` fill-color
support for flowcharts was intended to use it and never got wired up, or it's leftover scaffolding,
is outside this issue's scope to resolve -- worth a maintainer look separately.)

**`poc/pie/pie_poc.py`** is a working, runnable prototype of both renderings, validated against the
reference example below -- not shipped code (no `use_ascii`/color-flag plumbing into the real
`viewmd` package, a self-contained `Colorizer` instead of reusing `canvas.py`), but the layout math,
aspect-ratio handling, thin-wedge label placement, and glyph choices in requirements 4-8 above are
all taken directly from it, run and eyeballed before being written down here rather than
hand-derived. Run it directly to compare both renderings against the same input:

```
python3 poc/pie/pie_poc.py poc/pie/example.mmd --color always   # circular
python3 poc/pie/pie_poc.py poc/pie/example.mmd --color never    # bar-chart fallback
python3 poc/pie/pie_poc.py poc/pie/example.mmd --color never --ascii   # bar-chart, ASCII-safe glyph
python3 poc/pie/pie_poc.py poc/pie/example.mmd --color always --radius 22 --aspect 0.42
```

**The outer silhouette went through three designs before landing on requirement 4a's quadrant
blocks, each one actually rendered and visually judged, not just reasoned about on paper:**

1. *A separate ring character* (a flat `o` marking every cell within a fixed band of the ellipse's
   edge) was the first attempt. Rejected: the band is a fixed width in `r^2` space, which is not
   linear in actual radial distance near the edge, so the ring came out wildly inconsistent --
   between 4 and 32 marked cells depending on radius alone, often with visible gaps, on top of
   reading as a second, disconnected outline sitting just outside the fill rather than a clean edge.
2. *Per-cell directional tick marks* (`▔▁│╱╲`, chosen by the boundary cell's angle octant, replacing
   the flat ring with something whose own shape suggested the local tangent direction) was the
   second attempt, built to fix the first's inconsistency with proper edge detection (a cell flagged
   as border iff a neighbor fell outside the ellipse -- no gaps, unlike the `r^2`-band approach).
   Still rejected, for a different reason: rendered and viewed in a real terminal, the individual
   tick marks read as a spiky, disconnected fringe, not a curve -- fixing the gap problem did not fix
   the fact that a ring of small unconnected marks doesn't look like an edge at all. Both attempts
   were fully reverted; the plain solid-fill silhouette (no separate border treatment) looked cleaner
   than either.
3. *Quadrant blocks* (requirement 4a) is the design that held up under the same scrutiny: rendered,
   viewed in a real terminal, at multiple radii (20-30) and against a second five-slice example, and
   confirmed round rather than jagged, spiky, or oval (once paired with requirement 5a's aspect
   fix -- see below). The key structural difference from attempt 2: every boundary cell gets *some*
   glyph from a direct 16-way lookup on 4 independently-sampled sub-points, not a glyph chosen only
   when a specific pattern of neighbors matches. That is what actually fixes the "disconnected flecks"
   failure mode, not merely switching glyph sets.

A fourth idea -- extending the same corner-sampling anti-aliasing to *interior* wedge-to-wedge
boundaries (`◤◥◣◢` triangle glyphs, foreground/background truecolor split per cell) was also
prototyped and rejected, for the same "disconnected flecks" reason as attempt 2 above: it only fired
on a narrow specific 4-corner pattern (exactly one corner differing from the other three), so most
boundary cells along a real diagonal wedge seam never matched it and rendered as an ordinary solid
cell instead, leaving triangles scattered sparsely rather than tracing a continuous seam. Requirement
4a is deliberately scoped to the outer silhouette only, per this finding -- interior wedge-to-wedge
anti-aliasing is not required by any Requirement above, and would need the same 4-independent-
sub-point technique (not the 4-corner-pattern one) to have a chance of holding up if attempted later.

**Requirement 5's aspect constant cannot be measured by this script, only guessed and then
corrected by a human.** There is no reliable, cross-terminal way to query a terminal's actual
character-cell pixel dimensions -- some terminals expose `ws_xpixel`/`ws_ypixel` via `TIOCGWINSZ`,
many report zero, and even where it's populated it doesn't account for a terminal profile's
line-height/leading setting stacking further vertical space on top of the font's own metrics. This
is not a hypothetical concern: the first value tried (`aspect=0.5`, assuming a clean 2:1
character height:width ratio) rendered visibly oval in the maintainer's actual terminal (macOS
Terminal.app) -- tall, not the 2:1 assumption's flat/wide failure direction, confirming real
terminal fonts don't line up with a clean round-number guess. `0.42` is that terminal's
empirically-corrected value, arrived at by rendering several candidates side by side and picking
the one that actually looked round, not derived from any font metric -- which is exactly why
requirement 5a exists: this needs to stay a one-setting escape hatch for whichever value a given
user's terminal actually needs, not a constant anyone can get right for every terminal at once.

### Mock-ups

**Mock-up 3 -- circular, color-enabled (primary rendering, requirements 4-4a, 5-6a), the literal
output of `python3 poc/pie/pie_poc.py poc/pie/example.mmd --color always --radius 22 --aspect 0.42`**
with color stripped for this plain-text issue (`Colorizer(enabled=False)` -- the glyphs themselves
are unchanged from the real colored render; only the `\x1b[38;2;r;g;bm` wrapping is absent here).
Verified directly against the running POC at this exact radius/aspect: 1330 ANSI escapes across the
colored render, resolving to exactly the 3 expected `38;2;r;g;b` truecolor codes, one per slice, and
zero background-color escapes (requirement 4a's quadrant blocks don't need the foreground/background
split a rejected interior-boundary variant would have, see Design notes):

```
             Pets adopted by volunteers

                      3%
                     ▗▄▄▄▄▄▄▄▄▄▖
               ▗▄▟█████████████████▙▄▖
            ▄▟█████████████████████████▙▄
         ▗▟███████████████████████████████▙▖
        ▟███████████████████████████████████▙
      ▗██████████17%██████████████████████████▖
     ▗█████████████████████████████████████████▖
     ███████████████████████████████████████████
    ▐███████████████████████████████████████████▌       ██ Dogs
    ▐███████████████████████████████████████████▌       ██ Cats
    ▐███████████████████████████████████████████▌       ██ Rats
     ███████████████████████████████████████████
     ▝█████████████████████████████████████████▘
      ▝█████████████████████████79%███████████▘
        ▜███████████████████████████████████▛
         ▝▜███████████████████████████████▛▘
            ▀▜█████████████████████████▛▀
               ▝▀▜█████████████████▛▀▘
                     ▝▀▀▀▀▀▀▀▀▀▘
```

The Dogs (79.4%) and Cats (17.5%) wedges are wide enough to hold their percentage label inside the
wedge (requirement 6); Rats (3.1%, span ~11 degrees, under the 25-degree threshold) gets its label
pushed outside instead, directly above the circle -- and per requirement 6a, exactly one blank row
separates the title from that label, not the 2-3 that an earlier version of this render left in
(one from the deliberate title/body separator, one from the margin geometry between the label and
the circle's own top edge). Note also that the title, the "3%" label, and the "17%"/"79%" in-wedge
labels are the *only* plain-block/space characters mixed in with quadrant glyphs in this render --
every silhouette-edge row uses a quadrant partial-fill glyph where the true boundary crosses it,
which is what makes this read as round rather than the stepped-diamond shape a plain full-block-only
fill produces at the same radius (compare to the flat, unblended `D`/`C` boundary steps in the two
now-superseded design attempts documented in Design notes above).

**Mock-up 1 -- baseline bar-chart fallback (termaid's actual output), kept for reference:**

```
--- source ---
pie title Pets adopted by volunteers
    "Dogs" : 386
    "Cats" : 85
    "Rats" : 15
--- termaid's rendered bar-chart form ---
  Dogs┃████████████████████████████████  79.4%
  Cats┃▓▓▓▓▓▓▓  17.5%
  Rats┃░   3.1%
```

termaid right-aligns the label directly against the bar's leading edge (`┃`) rather than in a
separate padded column; viewmd's exact column layout is a design decision left open for this
issue's implementation, not dictated by this reference. Unlike termaid, requirement 8's fallback
does not need density-glyph differentiation (`█`/`▓`/`░`) between slices -- every bar uses the same
`█` (or `#` under `--ascii`), since the fallback path has no color to differentiate by, but also
doesn't need to: each bar already has its own row and label, unlike the circular rendering's wedges.

**Mock-up 2 -- optional enhancement to the bar-chart fallback, not required for v1: percentage tick
axis + sub-character bar precision.** Adds a 0/25/50/75/100% scale above the bars and resolves each
bar's fractional column to the nearest eighth-block glyph (`▏▎▍▌▋▊▉`) rather than rounding down to
the nearest whole character -- at a fixed bar width, two slices a few points apart can otherwise
render as visually identical bars:

```
--- source ---
pie title Pets adopted by volunteers
    "Dogs" : 386
    "Cats" : 85
    "Rats" : 15
--- rendered ---
  Pets adopted by volunteers

       0%        25%       50%       75%       100%
       │         │         │         │         │
  Dogs┃███████████████████████████████▊ 79.4%
  Cats┃███████ 17.5%
  Rats┃█▎ 3.1%
```

Worked out against a 40-column full-scale bar (bar starts at column 8, right after the `"  Dogs┃"`
prefix; ticks sit at columns 8/18/28/38/48, one every 10 columns per 25%): Dogs (79.4%) is
40 x 0.794 = 31.76 columns -> 31 solid `█` plus a `▊` (6/8) partial block, landing its right edge
one column past the 75% tick, consistent with being only 4.4 points past it. Cats (17.5%) is
exactly 40 x 0.175 = 7.0 columns -> 7 solid blocks, no partial glyph needed. Rats (3.1%) is
40 x 0.031 = 1.24 columns -> 1 solid `█` plus a `▎` (2/8) partial. The axis label row and the tick
row must be generated from the same `bar_width`/segment-width constants as the bars themselves --
computing them independently is an easy source of column drift (both the tick-vs-bar alignment and
the per-label padding one column at a time) rather than a one-off transcription slip. Whether this
lands alongside v1 or as a follow-up is a maintainer call, not required by any Requirement above.

## Acceptance / verification

- Unit tests for the parser: `title`, `showData` present/absent, integer and decimal values, `%%`
  comments and blank lines ignored, and an empty `pie` block (zero slices).
- Unit tests for the color-flag plumbing (requirement 3): `render_markdown(..., color=True)` vs.
  `color=False` against the same `pie` source reach `_render_pie` with the corresponding flag,
  end to end -- not just unit-tested at the `viewmd/mermaid/pie/` package boundary. A test
  confirming `NO_COLOR` set in the environment reaches the same outcome as `--color never` through
  `viewmd/__main__.py`.
- A rendered fixture confirming `color=True` (and not `use_ascii`) produces the circular rendering
  (requirement 4) with the expected wedge/slice assignment for the reference example, and that its
  output contains exactly 3 distinct truecolor ANSI sequences (one per slice) plus the bold-title
  escape -- not asserting exact pixel/character layout byte-for-byte, per the Non-goals' no-oracle
  posture, but asserting the color/structural properties mock-up 3 describes.
- A fixture confirming the silhouette anti-aliasing (requirement 4a) actually uses more than one
  quadrant-block glyph across the rendered circle -- not just `█`/space -- so a future change can't
  silently regress back to a plain stepped edge without a test noticing.
- A fixture confirming the wedge-angle test (requirement 5) uses the aspect-corrected coordinates:
  render the same chart at two different `aspect` values and confirm a slice's boundary column shifts
  between them (if it didn't, the angle test would be ignoring `aspect` entirely, silently
  reintroducing the skew requirement 5 exists to prevent).
- A fixture confirming the aspect override (requirement 5a) actually changes the rendered row count
  for a fixed radius -- proving it reaches the circle math, not just accepted and ignored.
- A fixture confirming the default radius (requirement 5b) scales with a mocked/injected terminal
  width -- e.g. asserting the specific 100-columns-in -> 24-radius-out relationship
  `poc/pie/pie_poc.py:_default_radius` produces, and that an explicit radius argument overrides it.
- A fixture confirming requirement 6a: exactly one blank line separates the title from the first
  content row, both for a chart with a thin outside-placed label (reference example, Rats) and one
  without any thin slices at all (where the naive version had nothing extra to trim in the first
  place, so this fixture also guards against removing a needed row by mistake).
- A rendered fixture confirming `color=False` (regardless of `use_ascii`) and confirming
  `use_ascii=True` (regardless of color) both produce the bar-chart fallback (requirement 8), with
  zero ANSI escapes in the `color=False` case.
- A rendered fixture with `showData` set on the bar-chart fallback, confirming raw values appear
  alongside percentages.
- A fixture exercising the thin-wedge external-label placement (requirement 6) using the reference
  example's 3.1% Rats slice, confirming its percentage renders outside the circle rather than
  overlapping neighboring wedges.
- A malformed `pie` fence (e.g. a slice line missing its `:` separator, or a negative value) falls
  back to showing the raw fence rather than crashing viewmd, in both color and no-color modes.
- A regression check that every other Mermaid diagram type's rendered output is byte-identical
  before and after the color-flag parameter (requirement 3) is threaded through its call site
  (requirement 10).
- `./run-tests.sh` green.

## Peer review

- **Claude Sonnet 5** (agent), 2026-08-09: Implemented against Requirements 1-10 (including 4a,
  5a, 5b, 6a) -- `viewmd/mermaid/pie/{parser,renderer}.py`, the color-flag plumbing through
  `viewmd/__main__.py` (unchanged) -> `viewmd/render.py` -> `viewmd/preprocessors.py` ->
  `viewmd/mermaid/preprocess.py` -> `viewmd/mermaid/__init__.py:render`, and
  `viewmd/mermaid/grid/canvas.py:wrap_text_bold` as the sibling to `wrap_text_in_color` the Design
  notes called for. `./run-tests.sh` is green (382 tests: pytest, ruff, pip-audit, `tools/issues.py
  --check`); every pre-existing golden-fixture test for flowchart/sequence/ER passed unchanged,
  satisfying requirement 10's no-regression bar without needing a new dedicated test. One real bug
  was found and fixed while testing against the terminal-width-derived default radius (not
  something the issue text anticipated): a thin outside-pushed slice label's computed position can
  land outside the render grid entirely and silently vanish once the radius is large enough --
  reproduced with the reference example at radius 24 (the actual 100-column default), fixed by
  clamping the label position to the nearest valid cell rather than dropping it
  (`viewmd/mermaid/pie/renderer.py`, `_render_circle`), and covered by
  `test_thin_wedge_label_stays_on_grid_at_large_radius`. `VIEWMD_PIE_ASPECT`/`VIEWMD_PIE_RADIUS`
  environment variables satisfy requirement 5a/5b's override; a dedicated `--color`-style CLI flag
  was considered and not used, since an env var was explicitly listed as an acceptable option and
  needs no changes to `viewmd/__main__.py`'s argument parser. No findings left as a follow-up issue.

- **Claude Sonnet 5** (agent), 2026-08-09: A second finding, from the maintainer testing `--width`
  against a real pie chart after the above review: the initial implementation of requirement 5b
  independently re-queried `shutil.get_terminal_size()` inside the pie renderer (copied straight
  from `poc/pie/pie_poc.py:_terminal_width`, which has no `--width` to defer to, being a standalone
  script) instead of reusing viewmd's already-resolved render width -- exactly what requirement
  5b's own text called for ("viewmd already has terminal-width detection ... to reuse here rather
  than reimplementing ... from scratch") and what the implementation missed on the first pass.
  Confirmed with `--width 60` vs. `--width 200` against the same source producing byte-identical
  pie output before the fix. Fixed by threading `width` through the same four-call-site pipeline
  `color` already uses (`viewmd/render.py` -> `viewmd/preprocessors.py` ->
  `viewmd/mermaid/preprocess.py` -> `viewmd/mermaid/__init__.py:render` ->
  `viewmd/mermaid/pie/renderer.py`), falling back to the raw terminal size only when no `width` is
  given (e.g. calling the renderer directly, as `poc/pie/pie_poc.py` still does standalone).
  Covered by `test_pie_chart_circular_size_respects_render_width` (`tests/test_render.py`, full
  pipeline) and `test_render_width_kwarg_overrides_raw_terminal_size`
  (`tests/test_mermaid_pie.py`, renderer unit level). `./run-tests.sh` green (384 tests). No
  findings left as a follow-up issue.

