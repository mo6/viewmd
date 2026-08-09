#!/usr/bin/env bash
# Combine each tests/fixtures/<type>/*.mmd fixture set into one Markdown
# file per type under docs/, each fixture shown as its raw source (a plain
# fence, so viewmd prints it verbatim instead of rendering it) immediately
# followed by the same definition in a ```mermaid fence for the actual
# rendering -- so source and output sit side by side for a quick eyeball
# check across the whole fixture set in one file.
#
#   ./tools/combine_fixtures.sh [glob]
#   ./viewmd.sh docs/mermaid_flowchart.md
#
# Writes docs/mermaid_er.md, docs/mermaid_flowchart.md, and
# docs/mermaid_sequence.md, one per fixture type found under tests/fixtures.
#
# [glob] is a filename glob (not a path) matched against each type's
# tests/fixtures/<type>/*.mmd directory; defaults to '*.mmd' (every
# fixture). The same glob is applied to every fixture type; types with no
# matches are skipped.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixtures_root="$here/tests/fixtures"
docs_dir="$here/docs"
glob="${1:-*.mmd}"

shopt -s nullglob
types=("$fixtures_root"/mermaid_*/)
shopt -u nullglob

if [[ ${#types[@]} -eq 0 ]]; then
    echo "combine_fixtures: no mermaid_* fixture directories found in $fixtures_root" >&2
    exit 1
fi

any_written=0
for type_dir in "${types[@]}"; do
    type_name="$(basename "$type_dir")"

    shopt -s nullglob
    files=("$type_dir"$glob)
    shopt -u nullglob

    if [[ ${#files[@]} -eq 0 ]]; then
        continue
    fi

    out_file="$docs_dir/$type_name.md"
    {
        echo "# Combined fixtures: $type_name ($glob)"
        echo
        for f in "${files[@]}"; do
            name="$(basename "$f" .mmd)"
            echo "## $name"
            echo
            echo "Source:"
            echo
            echo '```'
            cat "$f"
            echo '```'
            echo
            echo "Rendered:"
            echo
            echo '```mermaid'
            cat "$f"
            echo '```'
            echo
        done
    } > "$out_file"

    echo "Wrote $out_file" >&2
    any_written=1
done

if [[ "$any_written" -eq 0 ]]; then
    echo "combine_fixtures: no fixtures matched '$glob' in any mermaid_* directory under $fixtures_root" >&2
    exit 1
fi
