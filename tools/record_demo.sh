#!/usr/bin/env bash
# Record a GIF screencast of `md docs/example.md` (scrolling through the
# pager output) using VHS: https://github.com/charmbracelet/vhs
#
#   ./tools/record_demo.sh
#
# Runs tools/demo.tape from the repo root (VHS resolves the tape's `Output`
# path relative to the current directory) and writes docs/demo.gif.
# Requires `vhs` and `md` (this repo's viewmd.sh, e.g. via ~/.local/bin/md)
# on PATH.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v vhs >/dev/null 2>&1; then
    echo "record_demo: vhs not found on PATH -- see https://github.com/charmbracelet/vhs" >&2
    exit 1
fi

if ! command -v md >/dev/null 2>&1; then
    echo "record_demo: md not found on PATH -- expected this repo's viewmd.sh on PATH (e.g. ~/.local/bin/md)" >&2
    exit 1
fi

cd "$here"
vhs tools/demo.tape

echo "Wrote docs/demo.gif" >&2
