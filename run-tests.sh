#!/usr/bin/env bash
# viewmd's development check gate, in one command, from any working directory.
#
#   ./run-tests.sh                 the whole gate: pytest, ruff (incl. security rules), pip-audit,
#                                   issues/ lint+index check, and completions/ freshness check.
#                                   Runs every step even if an earlier one fails, so one run shows
#                                   every problem, and exits non-zero if any step failed.
#   ./run-tests.sh <pytest args>   tight iteration: anything you pass is handed straight to
#                                   pytest, e.g. `./run-tests.sh -k render -x`.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"
py="$here/.venv/bin/python"
ruff="$here/.venv/bin/ruff"

if [[ ! -x "$py" ]]; then
    echo "run-tests: no virtualenv at $here/.venv" >&2
    echo "  create it with:  python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'" >&2
    exit 1
fi

# Fast path: forward args to pytest and stop there, for a focused edit-run loop.
if [[ $# -gt 0 ]]; then
    exec "$py" -m pytest "$@"
fi

failed=0

echo "== pytest =="
"$py" -m pytest || failed=1

echo "== ruff =="
"$ruff" check . || failed=1

echo "== pip-audit =="
# Fetch failure is a failed step: the gate must never report clean when it couldn't check
# (docs/SECURITY.md section 3). No --offline path.
"$py" -m pip_audit --progress-spinner off || failed=1

echo "== issues =="
"$py" tools/issues.py --check || failed=1

echo "== completions =="
"$py" tools/completions.py --check || failed=1

if [[ "$failed" -eq 0 ]]; then
    echo "run-tests: all green"
else
    echo "run-tests: FAILED" >&2
fi
exit "$failed"
