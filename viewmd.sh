#!/usr/bin/env bash
# Run viewmd from the repo's virtualenv, from any working directory.
#
# The venv's python is used directly (no `activate` needed), so the launcher leaves no shell
# state behind. Arguments are passed through verbatim with "$@".
set -euo pipefail

# Resolve BASH_SOURCE through any symlink chain (macOS's readlink has no -f), so this still
# finds the real project directory when invoked through a symlink, e.g. ~/.local/bin/viewmd.
source="${BASH_SOURCE[0]}"
while [[ -L "$source" ]]; do
    target="$(readlink "$source")"
    if [[ "$target" == /* ]]; then
        source="$target"
    else
        source="$(dirname "$source")/$target"
    fi
done
here="$(cd "$(dirname "$source")" && pwd)"
py="$here/.venv/bin/python"

if [[ ! -x "$py" ]]; then
    echo "viewmd: no virtualenv at $here/.venv" >&2
    echo "  create it with:  python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'" >&2
    exit 1
fi

exec "$py" -m viewmd "$@"
