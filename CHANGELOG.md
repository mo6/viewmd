# Changelog

All notable changes to viewmd, newest first. Dates are the release date.

Ordinary semver (`MAJOR.MINOR.PATCH`).

## [1.21.0] — 2026-08-15

- **Render GFM task list checkboxes** (VIEWMD-0058, render): a bullet list item starting with `[x]`/`[X]`/`[ ]` now shows ✅ or ⬜ in place of the plain `•`, with the marker stripped from the label and checked items dimmed and struck through, so the raw GFM syntax no longer leaks into the render. See `docs/example.md`.

## [1.20.0] — 2026-08-15

- **Render Mermaid block-beta diagrams** (VIEWMD-0040, render/mermaid): a tenth Mermaid diagram type, `block-beta` (or its bare `block` alias -- both accepted, per Mermaid's own grammar) -- lays labeled boxes onto an explicit or implicit grid, positioned by declaration order rather than by edges. A `columns N` directive fixes row width; a `:N` suffix lets a block span multiple columns, widening to match their combined width; blocks sharing a grid column equalize to the widest one in that column, even across rows. A block can optionally connect to another same-row block via a plain flowchart-style `-->` arrow, reusing flowchart's box-drawing and arrowhead primitives rather than reimplementing them. No upstream reference implementation to differentially test against (`mermaid-ascii` has no block-beta support), so fixtures are hand-authored against maintainer-supplied reference examples. See `docs/example.md` and `docs/mermaid-block.md`.

## [1.19.1] — 2026-08-12

- **Make flowchart A* routing actually minimize corners among equal-length paths** (VIEWMD-0025, render/mermaid): `find_path` now charges a turn penalty in the real cost (with inbound direction in the search state), so equal-Manhattan routes prefer fewer corners instead of leaving the choice to heap tie-breaking. `obstacle_routing`'s `A -> D` drops from 3 corners to 1; other fixtures with a unique shortest path are unchanged. Deliberate divergence from the VIEWMD-0015 upstream baseline.

## [1.19.0] — 2026-08-12

- **Render Mermaid mindmap diagrams** (VIEWMD-0045, render/mermaid): a ninth Mermaid diagram type, `mindmap`, drawing an indentation-defined tree radiating from a root -- children fan out to the right via `─╭─`/`─├─`/`─╰─` branch connectors, overflowing some root children to the left once a single-direction fan would grow too tall. Shape markers (`(round)`, `[square]`, `((circle))`, `{{hexagon}}`, `)cloud(`) strip to plain text; `**bold**` and `*italic*` spans in a label render as real ANSI styling, independent of `--color`. No upstream reference implementation to port from (`mermaid-ascii` has no mindmap support), so this is hand-written and hand-verified. See `docs/example.md` and `docs/mermaid-mindmap.md`.

## [1.18.1] — 2026-08-12

- **Fix gitGraph dead-lane dashes overextending past their own last commit, and live-lane passthroughs falsely joining via `┼`** (VIEWMD-0052, render/mermaid): a connector between two lanes no longer stretches intermediate (or already-finished) lanes' dash fill out to its column, and when it crosses a still-live lane's own dash the horizontal `─` stays on top instead of junction-merging into `┼`, so an unrelated `merge`/`branch` reads as running behind that branch rather than joining it. Real endpoint joins still become `┼`/`├`/`┤` as before. See `tests/fixtures/mermaid_gitgraph/sequential_merged_branches.out` and `live_lane_passthrough.out`.

## [1.18.0] — 2026-08-11

- **Render Mermaid gitGraph diagrams** (VIEWMD-0042, render/mermaid): an eighth Mermaid diagram type, `gitGraph`, in the default left-right orientation -- one horizontal lane per branch, in first-appearance order, drawn as `──●──` segments with commit ids centered beneath each marker. Parses `commit id: "<id>"` (or a bare `commit`, which auto-generates a random 4-hex-char id, matching Mermaid's own behavior), `branch`/`checkout`, `merge <name> id: "<id>"`, `cherry-pick id: "<id>"`, and an optional `tag: "<label>"` rendered in `[brackets]`. Vertical connectors between lanes merge into `┼`/`├`/`┤` via the existing junction-merging machinery already used by the sequence renderer's lifelines. With color available, each branch gets its own hue (the same categorical palette kanban uses) and every commit id shares one neutral hue across the whole diagram, independent of `--ascii`; connectors and tags stay uncolored. No upstream reference implementation to port from (`mermaid-ascii` has no gitGraph support), so this is hand-written and hand-verified against maintainer-supplied reference examples. `gitGraph TB:`/`BT:`/`RL:` orientations are out of scope for this issue. See `docs/mermaid-gitgraph.md`.

## [1.17.0] — 2026-08-11

- **Render Mermaid Gantt charts** (VIEWMD-0032, render/mermaid): a seventh Mermaid diagram type, `gantt`, drawing one row per task -- a status-tagged bar (`done`/`active`/untagged/`crit`) or a single point glyph for a `milestone` -- against a scaled timeline axis with full-height gridlines and `section`-grouped rows. Parses `section` grouping, `after <id>`/`until <id>` task chaining (including id reuse across sections), `d`/`w`/`h` durations, `excludes weekends` day-skipping, and every status tag including `crit` (rendered with its own `[`/`]` bracket marker layered over the task's other status). The tick axis automatically switches between day-level (`MM-DD`) and week-level (`W<n>`) granularity based on the diagram's total span, adding a date-anchor line under the chart in week mode so `W<n>` labels still say what date they fall on. With color available, each status gets its own hue and `crit`'s brackets get a distinct hue layered on top, independent of `--ascii` -- the third diagram type (after pie, quadrant) where `color` changes the rendering. No upstream reference implementation to port from (`mermaid-ascii` has no gantt support), so this is hand-written and hand-verified against Mermaid's own "basic" and "full syntax" reference examples. See `docs/example.md` and `docs/mermaid-gantt.md`.

## [1.16.1] — 2026-08-11

- **Fix Mermaid ER diagram non-identifying relationships using box-drawing glyphs most terminal fonts do not render** (VIEWMD-0030, render/mermaid): `UNICODE.hd`/`UNICODE.vd` (the dashed connector glyphs for non-identifying relationships) changed from `┈`/`┊` (U+2508/U+250A) to `·`/`:`, since those box-drawing codepoints sit outside the basic box-drawing block most monospace terminal fonts cover and rendered as blank space instead of a visible dashed line -- the same font-coverage problem VIEWMD-0021 fixed for sequence-diagram dotted arrows.

## [1.16.0] — 2026-08-11

- **Add `tools/worktree.sh` for parallel per-issue git worktrees** (VIEWMD-0051, tools/docs): `./tools.sh worktree add|list|remove` creates a sibling `../viewmd-VIEWMD-NNNN` git worktree per issue, branched from `develop` with the correct `bug|feature|story/VIEWMD-NNNN` name, and bootstraps its own standalone `.venv` (`pip install -e '.[dev]'`) so `./run-tests.sh`/`./tools.sh` work from it immediately — letting multiple issues be worked in parallel, each in its own directory with its own Claude Code or Cursor session, without one session's uncommitted changes or branch checkout stepping on another's. `worktree remove` only tears down the directory; branch deletion stays a separate, explicit step. See `AGENTS.md`'s "Working multiple issues in parallel" section.

## [1.15.0] — 2026-08-10

- **Render Mermaid kanban diagrams** (VIEWMD-0034, render/mermaid): a sixth Mermaid diagram type, `kanban`, drawing ordered columns of stacked task cards -- each column its own box with a categorical-hue header (one hue per column, cycling past 8), each card its own nested box with a word-wrapped label and, where present, an `@{ ticket, assigned, priority }` metadata line rendered as a severity-colored priority token, an underlined ticket ID, and a right-aligned assignee. Card width is uniform across the whole board; a column's box hugs its own content height rather than padding out to match a taller neighbor. No upstream reference implementation to port from, so this is hand-written against Mermaid's own syntax. See `docs/example.md`.

## [1.14.1] — 2026-08-10

- **Fix wikilinks with a space in their target rendering as raw markdown instead of a styled link** (render/wikilinks): `rewrite_wikilinks` rewrote `[[Getting Started]]` to `[Getting Started](wikilink:Getting Started)`, an unescaped space in the link destination that's invalid CommonMark outside of the `<...>` bracketed form — Rich silently fell back to printing the raw `[text](url)` markdown instead of a styled hyperlink, for any wikilink target containing a space. The destination is now wrapped in `<...>` (escaping backslash/`<`/`>`), which is always valid. See `docs/example.md`.
- **Rebuild `docs/demo.gif` as a page-by-page screencast, `docs/example.md` now generated from `tools/demo-pages/*.md`** (docs): replaces the single scrolling-pager recording with one that pages through the showcase a topic at a time; `tools/demo-pages/*.md` is now the source of truth, concatenated into `docs/example.md` by `tools/build_example_md.sh`. Cuts the demo GIF from 27M to ~320K and adds it to the README.

## [1.14.0] — 2026-08-10

- **Render Mermaid quadrant charts** (VIEWMD-0047, render/mermaid): a sixth Mermaid diagram type, `quadrantChart`, drawing a bordered box split into four labelled quadrants by an internal cross, with each `<label>: [x, y]` data point plotted at its normalized `0.0`-`1.0` position and labelled beneath its marker. No upstream reference implementation to port from (`mermaid-ascii` has no quadrant-chart support), so this is hand-written against Mermaid's own syntax. Its default size scales with the document's actual render width, the same posture as the pie chart (`--width`, not the raw terminal); with color available, each quadrant's border, label, and points are tinted a distinct hue over a darkened background fill, and a point's own `color:` style (or its `:::class`'s `classDef color:`) overrides its quadrant's fallback tint -- the second diagram type (after pie) where `color` changes the rendering. See `docs/example.md` and `docs/mermaid-quadrant.md`.

## [1.13.0] — 2026-08-09

- **Render Mermaid packet diagrams** (VIEWMD-0049, render/mermaid): a fifth Mermaid diagram type, `packet-beta`/`packet`, drawing a fixed-width bit/byte field layout -- the kind used to document a network protocol header -- wrapped onto rows of 32 bits each, a field spanning a row boundary split across both rows under the same repeated label. Field ranges can be given explicitly (`<start>-<end>` or the single-bit `<start>` shorthand) or with the `+<count>` cursor-relative shorthand, freely mixed within one diagram; an optional `title` line renders centered above the diagram. No upstream reference implementation to port from (`mermaid-ascii` has no packet support, and real Mermaid renders to SVG, not a terminal grid), so this is hand-written against Mermaid's own syntax and, for field-contiguity validation, its actual parser source read directly from GitHub. See `docs/example.md` and `docs/mermaid-packet.md`.

## [1.12.0] — 2026-08-09

- **Render Mermaid pie charts** (VIEWMD-0043, render/mermaid): a fourth Mermaid diagram type, `pie`, rendered two ways depending on color availability -- a circular pie (truecolor per-slice fill, Unicode quadrant-block silhouette anti-aliasing, thin-wedge labels pushed outside the circle when their wedge is too narrow to hold them) when color is enabled, and a horizontal bar chart when it isn't (`NO_COLOR`, `--color never`, non-tty output, or `--ascii`) -- a monochrome circular pie was prototyped and found illegible, so the bar chart is a deliberate second design, not a fallback pending a better one. The circle's default size scales with the document's actual render width (`--width`, not the raw terminal), landing at roughly 60% of what comfortably fits. First diagram type where color/`--ascii` change the rendering shape itself, which needed threading a `color`/`width`-aware path through the whole Mermaid render pipeline (`viewmd/render.py` → `preprocessors.py` → `mermaid/preprocess.py` → `mermaid/__init__.py`) for the first time -- every other diagram type is unaffected. See `docs/example.md` and `docs/mermaid-pie.md`.

## [1.11.0] — 2026-08-09

- **Render Mermaid flowchart parallelogram/input-output node shapes** (VIEWMD-0039, render/mermaid): adds `[/Text/]` and `[\Text\]` to the flowchart node-shape set (VIEWMD-0022) -- each row offset one column from the row above it so the box reads as genuinely slanted, `/`/`\` used as the border glyph on every row, sized like every other rectangle-family shape (`label_lines + 2` rows, self-contained width growth off the node's own label, never a sibling's). An edge still attaches flush on every side via a shared x-anchor, so a vertical chain of parallelograms connects with a straight line rather than zigzagging. See `docs/mermaid-examples.md`'s "Node shapes" section.

## [1.10.0] — 2026-08-08

- **Render flowchart diamonds as a flat lozenge, and condense connector spacing** (VIEWMD-0038, render/mermaid): diamonds drop their tapered-rhombus geometry (VIEWMD-0022/0037) for the same flat-bordered-box mechanism every other shape uses -- exactly as tall as a same-content rectangle (`label_lines + 2` rows, no longer coupled to width), with a uniform `◇` marker on all four attachment points. `subroutine`'s side bars double (`‖` → `││`), `cylinder`'s heavy/light border weighting flips (heavy now on top), and the default horizontal/vertical connector gap shrinks (`PADDING_X` 5→3, `PADDING_Y` 5→2, with a labeled vertical edge separately guaranteed 1 blank line above/below its label) -- a deliberate divergence from the upstream `mermaid-ascii` reference's own defaults, consistent with this project's precedent (VIEWMD-0036, VIEWMD-0037). See `docs/mermaid-examples.md`'s "Node shapes"/"Branching and labelled edges" sections and `docs/diamonds.md`.

## [1.9.0] — 2026-08-07

- **Shrink flowchart diamonds to be proportionate to rectangle-family boxes** (VIEWMD-0037, render/mermaid): VIEWMD-0036 made every other node shape denser, leaving diamond decision nodes looking wildly oversized by comparison (a 2-character label like `{OK}` rendered 7 rows tall next to a 3-row rectangle). Tightened the diamond sizing formula so short and medium labels shrink meaningfully (`OK`: 7→5 rows, `Decision`: 11→9); long labels are unaffected since their own label-width floor already forces enough taper rows to reach it without a gap in the one-cell-per-row taper, a documented and accepted limitation. See `docs/mermaid-examples.md`'s "Node shapes" section.

## [1.8.0] — 2026-08-07

- **Flowchart node boxes no longer pad their label with a blank row above and below** (VIEWMD-0036, render/mermaid): rectangle, round, stadium, circle, subroutine, and cylinder nodes rendered 2 rows taller than necessary, a faithfully-ported upstream `mermaid-ascii` behavior that this project's own sequence-diagram and ER-diagram boxes never had; flowcharts now match that denser style, a deliberate divergence from the reference implementation. Diamond nodes and horizontal padding are unaffected. See `docs/mermaid-examples.md`'s "Node shapes" section.

## [1.7.2] — 2026-08-07

- **Use a Latin capital X for the sequence-diagram cross (failed-message) arrowhead** (VIEWMD-0024, render/mermaid): `-x`/`--x` messages used a lowercase `x` in the `ASCII` charset and `×` (U+00D7 MULTIPLICATION SIGN) in the `UNICODE` charset, both of which read too small/faint next to the other arrowhead glyphs (`>`, `<`, `)`, `(`) at typical terminal font sizes; both charsets now use a bolder Latin `X`.

## [1.7.1] — 2026-08-07

- **Reserve routing clearance for backward-flowing edges inside a flowchart subgraph** (VIEWMD-0023, render/mermaid): an edge that flows "backward" relative to a flowchart's overall direction is routed via each node's bottom side (LR) or right side (TD); when that routing lands on the same row/column as an enclosing subgraph's own border, the arrow used to visually fuse into the frame. viewmd now reserves an extra blank row/column of clearance in that case, a deliberate divergence from the upstream `mermaid-ascii` reference (which has this limitation) rather than a byte-for-byte port. See [docs/mermaid-examples.md](docs/mermaid-examples.md)'s "Subgraphs with left-to-right layout" example.

## [1.7.0] — 2026-08-06

- **Render real node shapes in Mermaid flowcharts** (VIEWMD-0022, render/mermaid): round (`()`), stadium/pill (`([ ])`), circle (`(())`), subroutine (`[[ ]]`), and cylinder/database (`[( )]`) nodes now render with distinguishable borders instead of falling back to a bare `[...]`-style label, and diamond (`{}`) decision nodes render as a true tapered rhombus with edges attaching at the apex -- going beyond the upstream `mermaid-ascii` reference, which doesn't implement any of this. Also fixes the topology bug this caused: `B{Decision}` and a later bare `B` reference used to be treated as two different nodes, splitting a decision's yes/no branches into disconnected boxes instead of one diamond with two arms. See [docs/mermaid-examples.md](docs/mermaid-examples.md)'s "Node shapes" section and [docs/diamonds.md](docs/diamonds.md) for a tour of the diamond's three tip sizes.

## [1.6.0] — 2026-08-05

- **Render Mermaid entity-relationship diagrams as box-drawing ASCII art** (VIEWMD-0016, render/mermaid): a fenced ` ```mermaid ` block containing an `erDiagram` now renders the same way sequence diagrams and flowcharts already do -- entity attribute tables, crow's-foot cardinality notation (crow's-foot tokens, numeric shorthand, and word phrases), and identifying (solid) vs. non-identifying (dashed) relationships, including self-loops. Ported byte-for-byte from `pkg/er` of the real `mermaid-ascii` Go reference, self-contained rather than reusing the flowchart port's grid engine. A trailing attribute key silently dropped when it follows a quoted comment on the same line is a faithfully-reproduced upstream parsing bug, tracked for a possible viewmd-side fix as VIEWMD-0029; the dashed-relationship glyphs' terminal-font legibility and the layout's visual density on small diagrams are tracked as VIEWMD-0030 and VIEWMD-0031. See [docs/mermaid-examples.md](docs/mermaid-examples.md) for an exhaustive tour of all three diagram types.

## [1.5.0] — 2026-08-05

- **Render Mermaid flowchart diagrams as box-drawing ASCII art** (VIEWMD-0015, render/mermaid): a fenced ` ```mermaid ` block containing a `graph`/`flowchart` now renders the same way sequence diagrams already do -- node boxes, labelled/unlabelled/bidirectional/chained/fan-out edges, subgraphs (including nested), `classDef`/`:::` styling (rendered as real ANSI colour), and edges automatically routed around obstacle nodes via A*. Ported byte-for-byte against the real `mermaid-ascii` Go reference, including two of its real limitations: only `A[Label]` square-bracket syntax renders as a distinct shape (other shape syntax falls back to a bare label), and `BT`/`RL` directions are accepted but not actually reversed (aliased to `TD`/`LR`) -- both tracked for a possible future viewmd-only extension (VIEWMD-0022, VIEWMD-0027), along with a few other upstream quirks found during review (VIEWMD-0023, VIEWMD-0025, VIEWMD-0028). See [docs/mermaid-examples.md](docs/mermaid-examples.md) for an exhaustive tour of both diagram types.

## [1.4.2] — 2026-08-05

- **Mermaid sequence-diagram dotted arrows now render on terminals whose font lacks the box-drawing quadruple-dash glyph** (VIEWMD-0021, render/mermaid): dotted message lines (`-->>`, `-->`, `--x`, `--)`, `<<-->>`) and the `alt`/`else` divider used `┈` (U+2508), a glyph many monospace terminal fonts don't cover, so the dashed segment rendered as blank space instead of a visible line. It now uses `·` (U+00B7 MIDDLE DOT), which has near-universal monospace support and reads clearly as dotted.

## [1.4.1] — 2026-08-04

- **Mermaid diagrams and code blocks keep their natural width instead of being wrapped or cropped** (VIEWMD-0018, VIEWMD-0019, render/mermaid): a mermaid diagram wider than the render width used to be word-wrapped and padded like ordinary text, interleaving box tops, labels, and lifelines onto separate rows and destroying the art; it now renders at its own natural width, scrolling horizontally in the pager (`less -S`, now the default) instead. A code-block line longer than the render width used to fold onto an extra line; it now stays intact on one line the same way, so nothing folds and nothing is silently cut off, regardless of the terminal or `--width` setting. A short block (all lines already fit) still fills/pads to the full render width, unchanged.

## [1.4.0] — 2026-08-04

- **Render Mermaid sequence-diagram actors as stick-figure glyphs** (VIEWMD-0020, render/mermaid): an `actor`-declared participant now draws a 3-line stick figure (head, arms/torso, legs) above its label instead of an ordinary box top, matching real Mermaid's visual distinction between `actor` and `participant`. One of five figure variants is chosen at random per actor; with multiple actors in one diagram, each gets a different figure before any repeat. A diagram with no actors renders byte-for-byte as before. `docs/example.md` gained an "Actors" section demonstrating it.

## [1.3.1] — 2026-08-04

- **Accept `actor` as a synonym for `participant` in Mermaid sequence diagrams** (VIEWMD-0017, render/mermaid): a sequence diagram declaring a participant with `actor` (instead of `participant`) previously failed to parse, silently falling all the way back to raw Mermaid source for the whole diagram. `actor` now parses identically to `participant` (including quoted-name and `as`-label forms) and renders as a box; a distinct stick-figure glyph for `actor` is tracked separately as VIEWMD-0020.

## [1.3.0] — 2026-08-03

- **Render Mermaid sequence diagrams as box-drawing ASCII art** (VIEWMD-0014, render/mermaid): a fenced ` ```mermaid ` block containing a `sequenceDiagram` now renders as box-drawing art in place of its source -- all 10 arrow types, central connections, self-messages, notes (`over`/`left of`/`right of`), fragments (`loop`/`opt`/`alt`/`par`/`critical`/`break`/`rect`) including nesting and dividers, `autonumber`, and participant aliasing. Ported from scratch to Python from `pkg/sequence` of `github.com/AlexanderGrooff/mermaid-ascii` (Go, MIT licensed; see `THIRD_PARTY_NOTICES.md`) rather than shelling out to a bundled per-platform binary, verified byte-for-byte against the real Go binary across 84 golden-file cases. Other diagram types, and any block that fails to parse, render unchanged rather than erroring. Also introduces a general preprocessor-plugin pipeline (`viewmd/preprocessors.py`) that wikilinks and this new renderer both run through, so future Markdown extensions plug in the same way. New dependency: `wcwidth` (pure Python).

## [1.2.0] — 2026-08-03

- **Accept multiple Markdown files as arguments** (VIEWMD-0013, cli/render/pager): `viewmd *.md` now renders every matched file, in the order given, into a single pager session -- each file preceded by a heading naming its path and separated from the next by the same double-line divider used before front matter (VIEWMD-0004). A single-file invocation renders byte-for-byte identical to before. Mixing stdin (`-`) with a file path is rejected; a per-file read error (missing file, bad permissions, invalid UTF-8) is reported and the remaining files still render, with a non-zero exit if any file failed. Unlike `less`, there's no per-file navigation -- all files are concatenated into one continuous scroll.

## [1.1.3] — 2026-08-03

- **Parse nested mappings, block-list/array-of-object values, and block scalars in front matter** (VIEWMD-0012, render): fixes a correctness bug found by VIEWMD-0011 where a nested key (e.g. `seo.title`) could silently overwrite an unrelated top-level key of the same name (`title`); nested mappings now flatten to dotted keys instead. Also adds support for block-list (`- item`) arrays (rendering the same as the existing `[a, b, c]` form), arrays of `- field: value` objects (every item now visible, not just the last), and literal (`|`)/folded (`>`) block scalars. No new dependency; TOML/JSON front matter remains unsupported (falls back unchanged, as before).

## [1.1.2] — 2026-08-03

- **Investigate advanced front-matter feature support** (VIEWMD-0011, docs/tests): recorded, against real test documents under `tests/fixtures/frontmatter-advanced/`, how nested objects, array-of-objects, block-list arrays, multiline block scalars, and TOML/JSON front matter actually render today. Found one correctness bug -- a nested key can silently overwrite an unrelated top-level key of the same name -- filed as VIEWMD-0012. No code changes; investigation only.

## [1.1.1] — 2026-08-02

- **Require an explicit, recorded maintainer peer-review line before landing** (VIEWMD-0010, docs): `issues/AGILE.md`'s Definition of Done now requires two distinct recorded peer-review lines (the reviewing agent's pass, then the maintainer's own sign-off) before an issue can land, not just an informal "commit and close this out?" yes. Process-only change; no code affected.

## [1.1.0] — 2026-08-02

- **Add a security gate: `docs/SECURITY.md` and `pip-audit` in `run-tests.sh`** (VIEWMD-0009, tools/docs): documents the existing ruff `S`-rule coverage and adds `pip-audit` as a `[dev]` dependency and a gate step, failing on any advisory or a failed advisory-data fetch (no offline-means-clean path).

## [1.0.1] — 2026-08-02

- **Fix: `pyproject.toml` license metadata said "Proprietary"** (VIEWMD-0008, tools): contradicted the MIT `LICENSE` file added on `main`. Now reads MIT, matching it.

## [1.0.0] — 2026-08-02

- **First stable release.** Everything from `0.1.0` through `0.5.0` below: render a Markdown file to ANSI in the terminal, auto-paged into `less`; `--no-pager`, `--color`, `--width`/`--width full`; a YAML front-matter block renders as a table (empty fields hidden by default, `--full-front-matter` to show them all) with a clear divider before the body; Obsidian-style `[[wikilinks]]` highlighted like standard Markdown links. No functional change from `0.5.0` — this tags the point the tool is considered stable for everyday use.

## [0.5.0] — 2026-08-02

- **Highlight Obsidian-style `[[wikilinks]]`** (VIEWMD-0006, render): `[[Target]]` and `[[Target|Display text]]` now render with the same highlight a standard Markdown link gets (blue + underline), brackets gone. Fenced code blocks (including ones indented under a list item) and inline code spans are left untouched, so wikilink-shaped text in real code renders as literal code.

## [0.4.0] — 2026-08-02

- **Hide empty front-matter fields by default; add `--full-front-matter`** (VIEWMD-0005, render/cli): a front-matter field with no value (or only whitespace) no longer shows up as a blank row in the table. `--full-front-matter` restores every parsed field, empty ones included.

## [0.3.0] — 2026-08-02

- **Render YAML front matter as a table, divided from the body** (VIEWMD-0004, render): a file opening with a `--- ... ---` block now renders that block as a key/value table (with `[a, b]`-style lists shown comma-joined) followed by a dim double-line divider, ahead of the rendered document body. A file with no front matter, an unterminated `---` block, or a block that parses to zero pairs renders exactly as before.

## [0.2.0] — 2026-08-02

- **Cap render width to 100 columns by default; `--width N` or `--width full` to override** (VIEWMD-0003, cli/render): a wide terminal no longer stretches prose and tables to the full window; the default render width is now `min(100, detected terminal width)`. `--width` still takes an exact column count, and now also accepts the literal `full` to render at the full detected terminal width, uncapped by the 100-column default.

## [0.1.1] — 2026-08-02

- **Fix: symlinked `viewmd.sh`/`tools.sh` couldn't find the project's venv** (VIEWMD-0002, bug, cli): `dirname "${BASH_SOURCE[0]}"` resolved to a symlink's own location rather than its target, so `ln -sf .../viewmd.sh ~/.local/bin/viewmd` failed with a bogus "no virtualenv" error when run from outside the project directory. Both scripts now walk the symlink chain by hand (`readlink`, no `-f` since macOS lacks it) before computing the project root.

## [0.1.0] — 2026-08-02

- **Initial release** (VIEWMD-0001): render a Markdown file to ANSI in the terminal, auto-paged into `less` when stdout is a terminal. Headers, emphasis, lists, blockquotes, GFM tables, and fenced code blocks (Pygments syntax highlighting, exact spacing preserved for ASCII art) via `rich.markdown.Markdown`. `--no-pager`, `--color {auto,always,never}` (respecting `NO_COLOR`), `--width`, and stdin input (`-` or omitted). Also ships the issue-first SDLC scaffolding (`AGENTS.md`, `issues/`, `tools/issues.py`) that governs how future changes land.
