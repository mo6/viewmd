# viewmd

View Markdown files from the command line — headers, emphasis, tables, syntax-highlighted code
blocks, GFM task list checkboxes, Obsidian/GitHub-style admonition callouts, basic Mermaid diagram
support, and any ASCII art in fenced code blocks, rendered to your terminal with color and
auto-paged into `less`.

![viewmd demo](docs/demo.gif)

## Install

```
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Usage

```
./viewmd.sh README.md              # renders and pages into $PAGER (less -R -F -X --mouse) if stdout is a terminal
./viewmd.sh README.md --no-pager   # print rendered ANSI straight to stdout, no pager
cat notes.md | ./viewmd.sh          # read from stdin
./viewmd.sh notes.md --color=never  # plain text, no ANSI color
./viewmd.sh notes.md --width 80     # render at exactly 80 columns
./viewmd.sh notes.md --width full   # render at the full terminal width, uncapped
./viewmd.sh notes.md --full-front-matter  # show every front-matter field, including empty ones
./viewmd.sh notes.md --no-toc             # skip the heading table of contents (on by default)
./viewmd.sh notes.md --config ./my.conf   # read config from an explicit path instead of the default
./viewmd.sh *.md                    # render every matched file, in order, in one pager session
```

Render width defaults to `min(100, detected terminal width)` — 100 columns is a common prose
line-length standard, so a wide terminal doesn't stretch prose or tables edge to edge. `--width N`
picks an exact width instead; `--width full` uses the full terminal width regardless of the
100-column default.

A file that opens with a YAML-style front-matter block (`--- ... ---`) — common in this project's
own `issues/*.md`, and in static-site-generator posts — renders that block as a key/value table,
followed by a divider, ahead of the document body. Parsing covers flat `key: value` pairs and
`[a, b]`-style lists; it is not a full YAML parser (see [docs/PLAN.md](docs/PLAN.md)). Fields
with no value are omitted from the table by default; `--full-front-matter` shows every field,
empty ones included.

A document with two or more `#` / `##` / `###` headings also gets a table of contents: the leading
`#` title renders first (as a normal heading), then an indented outline of the remaining headings,
then the rest of the body. The outline starts at three levels and steps down to h1–h2, then to
h1-only, if it would otherwise exceed 20 entries; every remaining `#` heading is kept even when
there are more than 20 of them. `--no-toc` turns it off; `--toc` turns it back on (for example to
override a config file that disabled it). `h4` and deeper headings stay in the body but are left
out of the outline.

Passing more than one path (or a glob the shell expands, like `*.md`) renders all of them, each
preceded by a heading naming its path and separated by a divider, concatenated into a single
`less` session — unlike `less` itself, there's no per-file navigation (`:n`/`:p`); it's one long
scroll through every file in the order given. Mixing stdin (`-`) with a file path is rejected.

Passing a directory renders its `_Index.md` if one exists (exact case match), exactly as if that
file had been passed directly; otherwise it renders a table-of-contents listing of the
directory's immediate entries (subdirectories first, then Markdown files, each alphabetically) —
a file's title (from front matter, its first heading, or its filename) and last-modified time,
one level deep, no recursion. This applies the same way whether the directory is the only `path`
argument or one of several.

Obsidian-style wikilinks (`[[Target]]`, `[[Target|Display text]]`) render highlighted the same
way a standard Markdown link does, brackets gone — outside of fenced code blocks and inline code
spans, which are left untouched.

A GitHub-flavored-Markdown task list item (`- [x] label` / `- [ ] label`) renders with a ✅/⬜
checkbox glyph in place of the plain bullet, the marker stripped from the label and a checked
item's text dimmed and struck through.

A blockquote whose first line is an Obsidian/GitHub-style `[!TYPE]` marker (`> [!NOTE]`,
`> [!WARNING]`, ...) renders as a bordered, colored callout card with the type's icon and label in
its top border, instead of a plain quote. GitHub's five canonical types — `NOTE`, `TIP`,
`IMPORTANT`, `WARNING`, `CAUTION` — each get their own icon and color; any other `[!TYPE]` (e.g.
Obsidian-only aliases) still renders as a generic card, using the type token as its label.

Once installed (`pip install -e .`), the `viewmd` command is also on `PATH` inside the venv, so
`viewmd README.md` works the same as `./viewmd.sh README.md` from an activated shell.

## Configuration file

A per-user config file supplies default values for `--width`, `--color`,
`--full-front-matter`, and `--toc`, so a standing preference doesn't need to be passed on every
invocation. An explicit CLI flag always wins over the file (`--no-toc` / `--no-full-front-matter`
are the flags that turn those defaults back off if the file sets them on); a missing file is not
an error — it's the same as viewmd's built-in defaults.

To set one up:

```
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/viewmd"
cat > "${XDG_CONFIG_HOME:-$HOME/.config}/viewmd/config" <<'EOF'
width = 80
color = never
full_front_matter = true
toc = false
EOF
```

viewmd looks for the file at `$XDG_CONFIG_HOME/viewmd/config` if `XDG_CONFIG_HOME` is set and
non-empty, otherwise `~/.config/viewmd/config`. It's a flat `key = value` file, one setting per
line; blank lines, `# comment` lines, and an optional `[section]` header are all ignored. Known
keys:

| Key | Values | Mirrors |
|---|---|---|
| `width` | a positive integer, or `full` | `--width` |
| `color` | `auto`, `always`, or `never` | `--color` |
| `full_front_matter` | `true`/`false` (also `yes`/`no`, `on`/`off`, `1`/`0`) | `--full-front-matter` |
| `toc` | `true`/`false` (same boolean synonyms) | `--toc` / `--no-toc` |

An unrecognized key is ignored (forward-compatible with future options); a key with an invalid
value, or a file that fails to parse, prints a `viewmd: ...` error and exits non-zero rather than
silently falling back. `--config PATH` reads configuration from `PATH` instead of the default
location — useful for a one-off alternate profile. Setting `VIEWMD_NO_CONFIG` to any non-empty
value skips reading a config file entirely, regardless of what's on disk — handy for CI or a
reproducible one-off run that must not pick up a developer's own file (`--config PATH` still wins
even then, since it's explicit).

## Mermaid diagrams

A fenced ` ```mermaid ` code block containing a `sequenceDiagram`, `graph`/`flowchart`,
`erDiagram`, `pie`, `packet-beta`/`packet`, `quadrantChart`, `kanban`, `gantt`, `gitGraph`,
`mindmap`, `block-beta`/`block`, or `xychart-beta`/`xychart` renders as box-drawing ASCII art in
place of its source. Other Mermaid diagram types, and any block that fails to parse, are left as
plain source text rather than causing an error. See
[docs/mermaid-examples.md](docs/mermaid-examples.md) for an exhaustive tour of sequence diagrams,
flowcharts, and ER diagrams, and [docs/example.md](docs/example.md) for one example of every
diagram type below, side by side with the rest of viewmd's Markdown support.

### Sequence diagrams, flowcharts, and ER diagrams

Sequence diagrams support notes, loop/alt/par fragments, and `actor` participants (drawn as a
random 3-line stick figure instead of a box). Flowcharts support subgraphs, labelled and
bidirectional edges, `classDef` styling, A*-based routing around other nodes, and distinct node
shapes (round, stadium/pill, circle, subroutine, cylinder/database, and diamond decision nodes
rendered as a rounded lozenge) — see [docs/diamonds.md](docs/diamonds.md) for the diamond shape
specifically, plus one real limitation inherited from the upstream renderer flowcharts are ported
from: `BT`/`RL` directions are accepted but not actually reversed (aliased to `TD`/`LR`). ER
diagrams support attribute tables, crow's-foot cardinality notation, and identifying/non-identifying
relationships.

### Pie charts

Pie charts render two different ways depending on whether color is available: a true circle
(per-slice truecolor fill, Unicode quadrant-block edge anti-aliasing, a legend, sized relative to
`--width` rather than a fixed constant) when it is, a horizontal bar chart when it isn't
(`--color never`, `NO_COLOR` set, non-tty output, or `--ascii`) — a monochrome circle was tried
and found illegible, so the bar chart is a deliberate second design, not a lesser fallback.

### Packet diagrams

A `packet-beta`/`packet` block draws a fixed-width bit/byte field layout (the kind used to
document a network protocol header) wrapped onto 32-bit rows, with a field spanning a row boundary
split across both rows under the same repeated label. Field ranges can be given explicitly
(`<start>-<end>`/`<start>`) or with the `+<count>` cursor-relative shorthand, freely mixed in the
same diagram. See [docs/mermaid-packet.md](docs/mermaid-packet.md) for more packet-diagram
fixtures.

### Quadrant charts

A `quadrantChart` block draws a bordered box split into four labelled quadrants by an internal
cross, with each `<label>: [x, y]` data point plotted at its normalized `0.0`-`1.0` position and
labelled beneath its marker. Like the pie chart, it's sized relative to `--width` rather than a
fixed constant; with color available, each quadrant's border/label/points are tinted a distinct
color over a darkened background fill, with a point's own `color:`/`classDef` styling overriding
its quadrant's tint. See [docs/mermaid-quadrant.md](docs/mermaid-quadrant.md) for more
quadrant-chart fixtures.

### Kanban boards

A `kanban` block draws ordered columns of stacked task cards: each column its own box with a
colored header (one hue per column, cycling past 8), each card its own nested box word-wrapped to
a uniform width. A card's optional `@{ ticket, assigned, priority }` metadata renders as a colored
line under its label — a severity-colored `[H]`/`[VH]`/`[L]`/`[VL]`/`[M]` priority token and an
underlined ticket ID on the left, the assignee right-aligned. Columns hug their own content
height rather than padding out to match a taller neighbor.

### Gantt charts

A `gantt` block draws one row per task: a status-tagged bar (`done`/`active`/untagged/`crit`) or a
single point glyph for a `milestone`, grouped into labelled `section`s, against a scaled timeline
axis with full-height gridlines. The axis automatically switches from day-level (`MM-DD`) to
week-level (`W<n>`) ticks for a longer date span, adding a date-anchor line under the chart (every
4th week tick's absolute date) so week labels still say what date they fall on. With color
available, each status gets its own hue and a `crit` task's bracket markers get a distinct hue
layered on top, independent of `--ascii`. See [docs/mermaid-gantt.md](docs/mermaid-gantt.md) for
more gantt-chart fixtures.

### gitGraph diagrams

A `gitGraph` block (default left-right orientation) draws one horizontal lane per branch, in
first-appearance order, as `──●──` segments with commit ids centered beneath each marker. Supports
`commit`/`branch`/`checkout`/`merge`/`cherry-pick`, an optional `tag:` rendered in `[brackets]`,
and a bare `commit` with no `id:` (auto-generates a random 4-hex-char id, matching Mermaid's own
behavior). Vertical connectors between lanes merge into `┼`/`├`/`┤` where they cross a lane's own
content. With color available, each branch gets its own hue and every commit id shares one neutral
hue across the diagram, independent of `--ascii`; connectors and tags stay uncolored.
`gitGraph TB:`/`BT:`/`RL:` orientations are not supported. See
[docs/mermaid-gitgraph.md](docs/mermaid-gitgraph.md) for more gitGraph fixtures.

### Mindmap diagrams

A `mindmap` block draws an indentation-defined tree radiating from a root: children fan out to the
right via `─╭─`/`─├─`/`─╰─` branch connectors, and once a single-direction fan would grow too tall
some root children overflow to the left instead. Mermaid shape markers (`(round)`, `[square]`,
`((circle))`, `{{hexagon}}`, `)cloud(`) are stripped to plain text; `**bold**` and `*italic*` spans
in a label render as real ANSI styling (independent of `--color`). See
[docs/mermaid-mindmap.md](docs/mermaid-mindmap.md) for more mindmap fixtures.

### Block diagrams

A `block-beta` block (or its bare `block` alias) lays labeled boxes onto an explicit or implicit
grid, positioned by declaration order rather than by edges. A `columns N` directive fixes row
width; a `:N` suffix lets a block span multiple columns, widening to match their combined width;
blocks sharing a grid column equalize to the widest one in that column, even across rows. A block
can optionally connect to another same-row block via a plain flowchart-style `-->` arrow. See
[docs/mermaid-block.md](docs/mermaid-block.md) for more block-diagram fixtures.

### XY charts

An `xychart-beta` block (or its bare `xychart` alias) plots one bar dataset, one line dataset, or both together against a shared category x-axis and numeric y-axis. Bars fill with eighth-resolution block glyphs (`▁` through `█`); lines are an orthogonal step/staircase using the same rounded corners as flowchart stadium/round nodes, drawn on top of the bars in a combo chart. Like pie and quadrant, the plot sizes itself from `--width` -- capped at the full viewport and never narrower than half of it, with height near-square at that floor and never flatter than 2:1. Horizontal orientation, extra series, and a numeric x-axis are not supported. See [docs/mermaid-xychart.md](docs/mermaid-xychart.md) and [docs/nvidia-stock-xychart.md](docs/nvidia-stock-xychart.md) for more.

## Development

- `./run-tests.sh` — the full check gate (pytest, ruff incl. security rules, `pip-audit`,
  `issues/` lint).
- `./tools.sh issues` — regenerate the `issues/README.md` index; `./tools.sh issues --check`
  lints without writing.
- See [AGENTS.md](AGENTS.md) for the issue-first development process,
  [docs/PLAN.md](docs/PLAN.md) for the rendering/paging design rationale, and
  [docs/SECURITY.md](docs/SECURITY.md) for the security gate's runbook,
  [SECURITY.md](SECURITY.md) to report a vulnerability, and
  [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for the project's code of conduct.
- See [TODO.md](TODO.md) — or directly, [issues/README.md](issues/README.md) — for what's
  proposed, in progress, and implemented.
