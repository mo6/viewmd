"""Unit tests for VIEWMD-0025: A* corner cost participates in path selection."""

from viewmd.mermaid.grid.astar import _CORNER, _STEP, find_path, merge_path
from viewmd.mermaid.grid.coords import GridCoord, determine_direction


def _corners(path: list[GridCoord]) -> int:
    if len(path) < 3:
        return 0
    count = 0
    for i in range(len(path) - 2):
        if determine_direction(path[i], path[i + 1]) != determine_direction(
            path[i + 1], path[i + 2]
        ):
            count += 1
    return count


def test_equal_length_paths_prefer_fewer_corners():
    """Open grid: (0,0)→(3,2) has many 5-step routes; the minimum is one corner
    (e.g. right×3 then down×2), never a staircase of three+ corners."""
    path = find_path(GridCoord(0, 0), GridCoord(3, 2), lambda _c: True)
    assert path is not None
    assert len(path) - 1 == 5
    assert _corners(merge_path(path)) == 1


def test_step_cost_dominates_any_corner_savings():
    """VIEWMD-0025 req. 2: `_STEP` must exceed any plausible corner-count
    difference so a longer Manhattan path cannot beat a shorter one on corners
    alone. 100 extra corners on a 4-step path still loses to a 5-step straight."""
    assert 4 * _STEP + 100 * _CORNER < 5 * _STEP


def test_blocked_edge_keeps_shortest_length():
    """With (1,0) blocked, (0,0)→(2,0) must take a 4-step detour — never a
    longer go-around, even though both need corners."""
    blocked = {GridCoord(1, 0)}

    def is_free(c: GridCoord) -> bool:
        return c not in blocked and c.x >= 0 and c.y >= 0

    path = find_path(GridCoord(0, 0), GridCoord(2, 0), is_free)
    assert path is not None
    assert len(path) - 1 == 4


def test_unique_shortest_path_unchanged_shape():
    """Only one shortest path exists (straight line); corner cost must not
    alter it — the regression case for VIEWMD-0025 req. 3."""
    path = find_path(GridCoord(0, 0), GridCoord(5, 0), lambda _c: True)
    assert path == [
        GridCoord(0, 0),
        GridCoord(1, 0),
        GridCoord(2, 0),
        GridCoord(3, 0),
        GridCoord(4, 0),
        GridCoord(5, 0),
    ]
    assert _corners(path) == 0
