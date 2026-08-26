#!/usr/bin/env bash
# Point this repo's git hooks at the version-controlled tools/hooks/ directory, so the pre-push
# gate (./run-tests.sh) is active without a manual, easy-to-forget `.git/hooks/` copy step.
#
#   ./tools.sh install_hooks
#
# core.hooksPath is a repo-level (not worktree-level) config, and a relative value is resolved
# against each worktree's own top-level directory when its hooks run -- so running this once, from
# any worktree, activates tools/hooks/pre-push in every worktree of this repo. Safe to re-run.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

git -C "$here" config core.hooksPath tools/hooks
echo "install_hooks: core.hooksPath set to tools/hooks (applies to every worktree of this repo)" >&2
