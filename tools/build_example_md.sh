#!/usr/bin/env bash
# Build docs/example.md by concatenating tools/demo-pages/*.md in order.
#
#   ./tools/build_example_md.sh
#
# tools/demo-pages/*.md is the source of truth for docs/example.md (VIEWMD
# demo-pages restructure): each page is also shown standalone, one at a
# time, by tools/demo_pages_loop.sh when recording docs/demo.gif, so every
# page must stay short enough to fit on one screen on its own (see
# tools/demo.tape's Width/Height) -- edit the pages, not docs/example.md
# directly, then re-run this script.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pages_dir="$here/tools/demo-pages"
out_file="$here/docs/example.md"

shopt -s nullglob
pages=("$pages_dir"/*.md)
shopt -u nullglob

if [[ ${#pages[@]} -eq 0 ]]; then
    echo "build_example_md: no pages found in $pages_dir" >&2
    exit 1
fi

{
    first=1
    for f in "${pages[@]}"; do
        if [[ "$first" -eq 0 ]]; then
            echo
        fi
        first=0
        cat "$f"
    done
} > "$out_file"

echo "Wrote $out_file from ${#pages[@]} pages in $pages_dir" >&2
