# viewmd

View Markdown files from the command line — headers, emphasis, tables, syntax-highlighted code
blocks, basic Mermaid diagram support, and any ASCII art in fenced code blocks, rendered to your
terminal with color and auto-paged into `less`.

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

Mermaid support covers sequence diagrams, flowcharts, and entity-relationship diagrams: a fenced
` ```mermaid ` code block containing a `sequenceDiagram`, `graph`/`flowchart`, or `erDiagram`
renders as box-drawing ASCII art in place of its source — sequence diagrams with notes,
loop/alt/par fragments, and `actor` participants (drawn as a random 3-line stick figure instead of
a box); flowcharts with subgraphs, labelled and bidirectional edges, `classDef` styling, A*-based
routing around other nodes, and distinct node shapes (round, stadium/pill, circle, subroutine,
cylinder/database, and diamond decision nodes rendered as a true tapered rhombus); ER diagrams
with attribute tables, crow's-foot cardinality notation, and identifying/non-identifying
relationships. See [docs/mermaid-examples.md](docs/mermaid-examples.md) for an exhaustive tour of
all three, including [docs/diamonds.md](docs/diamonds.md) for the diamond shape specifically, and
one real limitation inherited from the upstream renderer flowcharts are ported from: `BT`/`RL`
directions are accepted but not actually reversed (aliased to `TD`/`LR`). Other Mermaid diagram
types, and any block that fails to parse, are left as plain source text rather than causing an
error.

Once installed (`pip install -e .`), the `viewmd` command is also on `PATH` inside the venv, so
`viewmd README.md` works the same as `./viewmd.sh README.md` from an activated shell.

## Development

- `./run-tests.sh` — the full check gate (pytest, ruff incl. security rules, `pip-audit`,
  `issues/` lint).
- `./tools.sh issues` — regenerate the `issues/README.md` index; `./tools.sh issues --check`
  lints without writing.
- See [AGENTS.md](AGENTS.md) for the issue-first development process,
  [docs/PLAN.md](docs/PLAN.md) for the rendering/paging design rationale, and
  [docs/SECURITY.md](docs/SECURITY.md) for the security gate's runbook.
