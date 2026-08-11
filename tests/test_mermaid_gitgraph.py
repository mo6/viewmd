"""Golden-file regression tests for the gitGraph renderer (VIEWMD-0042).

No upstream reference implementation to differentially test against (the
local mermaid-ascii Go oracle has no gitGraph support at all) -- these
fixtures are the maintainer-supplied reference examples from the issue,
hand-verified character-for-character against its own supplied output, same
posture as the pie/quadrant/kanban renderers' hand-authored fixtures.
"""

import re
from pathlib import Path

import pytest

import viewmd.mermaid as mermaid
from viewmd.mermaid.gitgraph.parser import parse
from viewmd.mermaid.gitgraph.renderer import render

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)

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


# ---------------------------------------------------------------------------
# Coloring (maintainer review feedback, 2026-08-11): each branch gets its own
# hue, every commit id label shares one neutral hue regardless of branch,
# connectors/tags stay uncolored.
# ---------------------------------------------------------------------------

_MERGE_EXAMPLE = (
    'gitGraph\n'
    '    commit id: "1"\n'
    '    commit id: "2"\n'
    '    branch develop\n'
    '    commit id: "3"\n'
    '    commit id: "4"\n'
    '    checkout main\n'
    '    commit id: "5"\n'
    '    merge develop id: "6"\n'
)


def test_no_ansi_when_color_disabled():
    graph = parse(_MERGE_EXAMPLE)
    assert "\x1b[" not in render(graph, color=False)


def test_color_disabled_by_default():
    graph = parse(_MERGE_EXAMPLE)
    assert render(graph) == render(graph, color=False)


def test_color_output_strips_to_the_same_plain_text():
    graph = parse(_MERGE_EXAMPLE)
    assert _strip_ansi(render(graph, color=True)) == render(graph, color=False)


def test_each_branch_gets_its_own_hue():
    graph = parse(_MERGE_EXAMPLE)
    out = render(graph, color=True)
    main_line = next(ln for ln in out.splitlines() if "main" in ln)
    develop_line = next(ln for ln in out.splitlines() if "develop" in ln)
    main_hue = re.search(r"38;2;(\d+;\d+;\d+)", main_line).group(1)
    develop_hue = re.search(r"38;2;(\d+;\d+;\d+)", develop_line).group(1)
    assert main_hue != develop_hue


def test_commit_ids_all_share_one_hue_across_branches():
    graph = parse(_MERGE_EXAMPLE)
    out = render(graph, color=True)
    id_lines = [ln for ln in out.splitlines() if re.search(r"38;2;\d+;\d+;\d+m[1-6]\b", ln)]
    hues = {m.group(1) for ln in id_lines for m in re.finditer(r"38;2;(\d+;\d+;\d+)", ln)}
    assert len(hues) == 1


def test_connectors_and_tags_stay_uncolored():
    graph = parse('gitGraph\n    commit id: "init" tag: "v0.1"\n    commit id: "feat"\n')
    out = render(graph, color=True)
    tag_line = next(ln for ln in out.splitlines() if "[v0.1]" in ln)
    assert "\x1b[" not in tag_line
