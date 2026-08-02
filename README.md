# viewmd

View Markdown files from the command line — headers, emphasis, tables, syntax-highlighted code
blocks, and any ASCII art in fenced code blocks, rendered to your terminal with color and
auto-paged into `less`.

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

Obsidian-style wikilinks (`[[Target]]`, `[[Target|Display text]]`) render highlighted the same
way a standard Markdown link does, brackets gone — outside of fenced code blocks and inline code
spans, which are left untouched.

Once installed (`pip install -e .`), the `viewmd` command is also on `PATH` inside the venv, so
`viewmd README.md` works the same as `./viewmd.sh README.md` from an activated shell.

## Development

- `./run-tests.sh` — the full check gate (pytest, ruff, `issues/` lint).
- `./tools.sh issues` — regenerate the `issues/README.md` index; `./tools.sh issues --check`
  lints without writing.
- See [AGENTS.md](AGENTS.md) for the issue-first development process, and
  [docs/PLAN.md](docs/PLAN.md) for the rendering/paging design rationale.
