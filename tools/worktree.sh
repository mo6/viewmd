#!/usr/bin/env bash
# Manage sibling git worktrees for working multiple VIEWMD-NNNN issues in parallel.
#
#   ./tools.sh worktree add VIEWMD-NNNN [bug|feature|story]
#       Create ../<repo>-VIEWMD-NNNN as a new git worktree on <kind>/VIEWMD-NNNN (default kind
#       "feature"), branched from develop, with its own .venv bootstrapped
#       (pip install -e '.[dev]') so ./run-tests.sh and ./tools.sh work standalone from it.
#
#   ./tools.sh worktree list
#       List every worktree, annotated with the VIEWMD-NNNN id its branch implies (if any).
#
#   ./tools.sh worktree remove VIEWMD-NNNN
#       Remove the worktree directory for VIEWMD-NNNN (refuses if it has uncommitted changes,
#       same as plain `git worktree remove`). Does NOT delete the branch -- that stays a
#       separate, explicit `git branch -d <branch>` once the work has actually landed.
#
# See AGENTS.md's "Working multiple issues in parallel" section for the surrounding workflow.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# The sibling-directory convention (../<repo>-VIEWMD-NNNN) is anchored on the *main* worktree,
# not wherever this script happens to be running from -- invoked via `./tools.sh worktree ...`
# from inside a linked worktree, $here would otherwise resolve to that worktree's own path (e.g.
# viewmd-VIEWMD-8888), silently drifting the naming convention for anything created from there.
common_dir="$(git -C "$here" rev-parse --git-common-dir)"
[[ "$common_dir" = /* ]] || common_dir="$here/$common_dir"
main_worktree="$(cd "$common_dir/.." && pwd)"
repo_name="$(basename "$main_worktree")"
siblings_dir="$(dirname "$main_worktree")"

usage() {
    echo "usage:" >&2
    echo "  ./tools.sh worktree add VIEWMD-NNNN [bug|feature|story]" >&2
    echo "  ./tools.sh worktree list" >&2
    echo "  ./tools.sh worktree remove VIEWMD-NNNN" >&2
    exit 1
}

# Prints the worktree path for VIEWMD-NNNN's branch (any of bug|feature|story), or nothing.
find_worktree_dir() {
    local id="$1" path="" branch=""
    while IFS= read -r line; do
        case "$line" in
            worktree\ *) path="${line#worktree }" ;;
            branch\ refs/heads/*)
                branch="${line#branch refs/heads/}"
                if [[ "$branch" =~ ^(bug|feature|story)/"$id"$ ]]; then
                    echo "$path"
                    return 0
                fi
                ;;
        esac
    done < <(git -C "$here" worktree list --porcelain)
    return 1
}

cmd="${1:-}"; shift || true

case "$cmd" in
    add)
        id="${1:-}"; kind="${2:-feature}"
        [[ "$id" =~ ^VIEWMD-[0-9]{4}$ ]] || { echo "worktree add: '$id' is not a VIEWMD-NNNN id" >&2; usage; }
        [[ "$kind" =~ ^(bug|feature|story)$ ]] || { echo "worktree add: kind must be bug, feature, or story, got '$kind'" >&2; usage; }

        branch="$kind/$id"
        worktree_dir="$siblings_dir/$repo_name-$id"

        if git -C "$here" show-ref --verify --quiet "refs/heads/$branch"; then
            echo "worktree add: branch '$branch' already exists" >&2
            exit 1
        fi
        if [[ -e "$worktree_dir" ]]; then
            echo "worktree add: '$worktree_dir' already exists" >&2
            exit 1
        fi

        git -C "$here" worktree add -b "$branch" "$worktree_dir" develop

        venv="$worktree_dir/.venv"
        if [[ -x "$venv/bin/python" ]]; then
            echo "worktree add: .venv already present at $venv, skipping bootstrap" >&2
        else
            echo "worktree add: bootstrapping $venv" >&2
            python3 -m venv "$venv"
            "$venv/bin/pip" install -q --upgrade pip
            "$venv/bin/pip" install -q -e "$worktree_dir[dev]"
        fi

        "$here/install_hooks.sh"

        echo "worktree add: ready at $worktree_dir on branch $branch" >&2
        echo "  cd '$worktree_dir' && ./run-tests.sh" >&2
        ;;

    list)
        path="" branch="" id=""
        while IFS= read -r line; do
            case "$line" in
                worktree\ *)
                    [[ -n "$path" ]] && printf '  %-55s %s\n' "$path" "${id:-(no VIEWMD id)}"
                    path="${line#worktree }"; branch=""; id=""
                    ;;
                branch\ refs/heads/*)
                    branch="${line#branch refs/heads/}"
                    if [[ "$branch" =~ ^(bug|feature|story)/(VIEWMD-[0-9]{4})$ ]]; then
                        id="${BASH_REMATCH[2]} ($branch)"
                    fi
                    ;;
            esac
        done < <(git -C "$here" worktree list --porcelain)
        [[ -n "$path" ]] && printf '  %-55s %s\n' "$path" "${id:-(no VIEWMD id)}"
        ;;

    remove)
        id="${1:-}"
        [[ "$id" =~ ^VIEWMD-[0-9]{4}$ ]] || { echo "worktree remove: '$id' is not a VIEWMD-NNNN id" >&2; usage; }

        worktree_dir="$(find_worktree_dir "$id")" || {
            echo "worktree remove: no worktree found with a bug|feature|story/$id branch" >&2
            exit 1
        }
        branch="$(git -C "$worktree_dir" rev-parse --abbrev-ref HEAD)"

        git -C "$here" worktree remove "$worktree_dir"

        echo "worktree remove: removed $worktree_dir" >&2
        echo "  branch '$branch' is untouched -- delete it yourself once the work has landed:" >&2
        echo "    git branch -d '$branch'" >&2
        ;;

    *)
        usage
        ;;
esac
