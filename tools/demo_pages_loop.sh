#!/usr/bin/env bash
# Show each tools/demo-pages/*.md file in turn via ./viewmd.sh, pausing 5s
# between pages. Every page is short enough to fit on one screen, so the
# pager (less -F) auto-advances without a keypress -- but only if the
# terminal is also wide enough that no line needs horizontal scrolling;
# less -F won't auto-exit otherwise, even with -S chopping. See
# tools/demo.tape's Width. Used by tools/record_demo.sh via tools/demo.tape.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$here"

for f in tools/demo-pages/*.md; do
    clear
    ./viewmd.sh --width 100 --color always "$f"
    sleep 5
done
