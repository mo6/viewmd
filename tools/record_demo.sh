#!/usr/bin/env bash
# Record a GIF screencast paging through tools/demo-pages/*.md one page at a
# time (see tools/demo_pages_loop.sh) using VHS: https://github.com/charmbracelet/vhs
#
#   ./tools/record_demo.sh
#
# Rebuilds docs/example.md from tools/demo-pages/*.md (tools/demo-pages is
# the source of truth -- see tools/build_example_md.sh), then runs
# tools/demo.tape from the repo root (VHS resolves the tape's `Output` path
# relative to the current directory) and writes docs/demo.gif. Requires
# `vhs` and `gifsicle` on PATH; tools/demo_pages_loop.sh invokes this repo's
# own ./viewmd.sh directly, so no PATH alias for it is needed.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v vhs >/dev/null 2>&1; then
    echo "record_demo: vhs not found on PATH -- see https://github.com/charmbracelet/vhs" >&2
    exit 1
fi

if ! command -v gifsicle >/dev/null 2>&1; then
    echo "record_demo: gifsicle not found on PATH -- see https://www.lcdf.org/gifsicle/ (brew install gifsicle)" >&2
    exit 1
fi

cd "$here"
./tools/build_example_md.sh
vhs tools/demo.tape

gifsicle -O3 --lossy=30 --colors 64 docs/demo.gif -o docs/demo.gif

echo "Wrote docs/demo.gif" >&2
