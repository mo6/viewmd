#!/usr/bin/env bash
# Run one of the tools/ scripts from the repo's virtualenv, from any working directory.
#
#   ./tools.sh <tool> [args...]
#   ./tools.sh                     list the available tools
#
# <tool> is a script's name under tools/, with or without its .py suffix and with - or _
# interchangeably. Everything after it is passed through verbatim, e.g. `./tools.sh issues --check`.
set -euo pipefail

# Resolve BASH_SOURCE through any symlink chain (macOS's readlink has no -f), so this still
# finds the real project directory when invoked through a symlink.
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
tools_dir="$here/tools"

if [[ ! -x "$py" ]]; then
    echo "tools: no virtualenv at $here/.venv" >&2
    echo "  create it with:  python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'" >&2
    exit 1
fi

list_tools() {
    for f in "$tools_dir"/*.py; do
        name="$(basename "$f" .py)"
        [[ "$name" == __init__ || "$name" == _* ]] && continue
        summary="$("$py" - "$f" <<'EOF'
import ast, sys
tree = ast.parse(open(sys.argv[1]).read())
doc = ast.get_docstring(tree) or ""
print(doc.splitlines()[0] if doc else "")
EOF
)"
        printf '  %-16s %s\n' "$name" "$summary"
    done
}

if [[ $# -eq 0 ]]; then
    echo "usage: ./tools.sh <tool> [args...]" >&2
    echo "available tools:" >&2
    list_tools >&2
    exit 1
fi

tool="$1"; shift
tool="${tool%.py}"
tool="${tool//-/_}"

script="$tools_dir/$tool.py"
if [[ ! -f "$script" ]]; then
    echo "tools: no such tool '$tool' (looked for $script)" >&2
    echo "available tools:" >&2
    list_tools >&2
    exit 1
fi

exec "$py" "$script" "$@"
