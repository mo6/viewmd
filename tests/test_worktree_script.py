"""Regression test for VIEWMD-0110: tools/worktree.sh's `worktree add` called
install_hooks.sh at the wrong path ($here/install_hooks.sh instead of
$here/tools/install_hooks.sh), so the hook silently never installed.

A live `./tools.sh worktree add` end-to-end run is exercised manually (per the
issue's acceptance criteria) rather than in this suite, since it bootstraps a
real .venv and is too slow for the pytest gate. This test instead pins the
script's referenced path to an actual file on disk, so any future path drift
is caught without needing a live worktree creation.
"""

import re
from pathlib import Path


def test_worktree_add_install_hooks_path_exists():
    root = Path(__file__).resolve().parent.parent
    script = (root / "tools" / "worktree.sh").read_text()

    match = re.search(r'"\$here(/\S*install_hooks\.sh)"', script)
    assert match, "tools/worktree.sh should call install_hooks.sh via $here/<path>"

    referenced_path = match.group(1).lstrip("/")
    assert (root / referenced_path).is_file(), (
        f"tools/worktree.sh references $here/{referenced_path}, "
        "but no such file exists relative to the repo root"
    )
