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
./viewmd.sh notes.md --width 80     # override terminal width detection
```

Once installed (`pip install -e .`), the `viewmd` command is also on `PATH` inside the venv, so
`viewmd README.md` works the same as `./viewmd.sh README.md` from an activated shell.

## Development

- `./run-tests.sh` — the full check gate (pytest, ruff, `issues/` lint).
- `./tools.sh issues` — regenerate the `issues/README.md` index; `./tools.sh issues --check`
  lints without writing.
- See [AGENTS.md](AGENTS.md) for the issue-first development process, and
  [docs/PLAN.md](docs/PLAN.md) for the rendering/paging design rationale.
