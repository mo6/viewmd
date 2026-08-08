# Changelog

All notable changes to viewmd, newest first. Dates are the release date.

Ordinary semver (`MAJOR.MINOR.PATCH`).

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
