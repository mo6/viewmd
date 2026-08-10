# viewmd

View Markdown files from the command line — headers, emphasis, tables, syntax-highlighted code
blocks, basic Mermaid diagram support, and any ASCII art in fenced code blocks, rendered to your
terminal with color and auto-paged into `less`.

![viewmd demo](docs/demo.gif)

## Install

```
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Usage

```
./viewmd.sh README.md              # renders and pages into $PAGER (less -R -F -X) if stdout is a terminal
./viewmd.sh README.md --no-pager   # print rendered ANSI straight to stdout, no pager
cat notes.md | ./viewmd.sh          # read from stdin
./viewmd.sh notes.md --color=never  # plain text, no ANSI color
./viewmd.sh notes.md --width 80     # render at exactly 80 columns
./viewmd.sh notes.md --width full   # render at the full terminal width, uncapped
./viewmd.sh notes.md --full-front-matter  # show every front-matter field, including empty ones
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

Passing more than one path (or a glob the shell expands, like `*.md`) renders all of them, each
preceded by a heading naming its path and separated by a divider, concatenated into a single
`less` session — unlike `less` itself, there's no per-file navigation (`:n`/`:p`); it's one long
scroll through every file in the order given. Mixing stdin (`-`) with a file path is rejected.

Obsidian-style wikilinks (`[[Target]]`, `[[Target|Display text]]`) render highlighted the same
way a standard Markdown link does, brackets gone — outside of fenced code blocks and inline code
spans, which are left untouched.

Once installed (`pip install -e .`), the `viewmd` command is also on `PATH` inside the venv, so
`viewmd README.md` works the same as `./viewmd.sh README.md` from an activated shell.

## Mermaid diagrams

A fenced ` ```mermaid ` code block containing a `sequenceDiagram`, `graph`/`flowchart`,
`erDiagram`, `pie`, `packet-beta`/`packet`, or `quadrantChart` renders as box-drawing ASCII art in
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

## Development

- `./run-tests.sh` — the full check gate (pytest, ruff incl. security rules, `pip-audit`,
  `issues/` lint).
- `./tools.sh issues` — regenerate the `issues/README.md` index; `./tools.sh issues --check`
  lints without writing.
- See [AGENTS.md](AGENTS.md) for the issue-first development process,
  [docs/PLAN.md](docs/PLAN.md) for the rendering/paging design rationale, and
  [docs/SECURITY.md](docs/SECURITY.md) for the security gate's runbook.
