"""Golden-file regression tests for the gitGraph renderer (VIEWMD-0042).

No upstream reference implementation to differentially test against (the
local mermaid-ascii Go oracle has no gitGraph support at all) -- these
fixtures are the maintainer-supplied reference examples from the issue,
hand-verified character-for-character against its own supplied output, same
posture as the pie/quadrant/kanban renderers' hand-authored fixtures.
"""

from pathlib import Path

import pytest

import viewmd.mermaid as mermaid
from viewmd.mermaid.gitgraph.parser import parse
from viewmd.mermaid.gitgraph.renderer import render

FIXTURES = Path(__file__).parent / "fixtures" / "mermaid_gitgraph"


def _cases():
    for mmd in sorted(FIXTURES.glob("*.mmd")):
        expected = mmd.with_suffix(".out")
        if expected.exists():
            yield pytest.param(mmd, expected, id=mmd.stem)


@pytest.mark.parametrize("mmd_path,expected_path", list(_cases()))
def test_matches_reference_example(mmd_path, expected_path):
    graph = parse(mmd_path.read_text())
    assert render(graph) == expected_path.read_text()


# ---------------------------------------------------------------------------
# Dispatch (viewmd/mermaid/__init__.py) fallback behavior -- requirement 10:
# a gitGraph fence that fails to parse must raise MermaidError (which
# preprocess.py catches to fall back to showing the raw fence), never crash.
# ---------------------------------------------------------------------------


def test_gitgraph_fence_is_recognized_and_rendered_end_to_end():
    out = mermaid.render('gitGraph\n    commit id: "A"\n')
    assert "main" in out
    assert "●" in out


@pytest.mark.parametrize("orientation", ["TB", "BT", "RL"])
def test_non_default_orientation_falls_back_to_mermaid_error(orientation):
    with pytest.raises(mermaid.MermaidError):
        mermaid.render(f'gitGraph {orientation}:\n    commit id: "A"\n')


@pytest.mark.parametrize(
    "source",
    [
        # merge referencing an undeclared branch
        'gitGraph\n    commit id: "A"\n    merge develop\n',
        # cherry-pick referencing an undeclared commit id
        'gitGraph\n    commit id: "A"\n    cherry-pick id: "nope"\n',
        # checkout of an undeclared branch
        "gitGraph\n    checkout develop\n",
    ],
)
def test_malformed_gitgraph_fence_falls_back_to_mermaid_error(source):
    with pytest.raises(mermaid.MermaidError):
        mermaid.render(source)
