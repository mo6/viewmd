"""Grid/drawing coordinates and the 8-way direction vectors used to route
edges around obstacles, ported from cmd/direction.go and the coordinate types
in cmd/graph.go."""

from __future__ import annotations

from typing import NamedTuple


class GridCoord(NamedTuple):
    x: int
    y: int


class DrawingCoord(NamedTuple):
    x: int
    y: int


class Direction(NamedTuple):
    x: int
    y: int


UP = Direction(1, 0)
DOWN = Direction(1, 2)
LEFT = Direction(0, 1)
RIGHT = Direction(2, 1)
UPPER_RIGHT = Direction(2, 0)
UPPER_LEFT = Direction(0, 0)
LOWER_RIGHT = Direction(2, 2)
LOWER_LEFT = Direction(0, 2)
MIDDLE = Direction(1, 1)

_OPPOSITE = {
    UP: DOWN,
    DOWN: UP,
    LEFT: RIGHT,
    RIGHT: LEFT,
    UPPER_RIGHT: LOWER_LEFT,
    UPPER_LEFT: LOWER_RIGHT,
    LOWER_RIGHT: UPPER_LEFT,
    LOWER_LEFT: UPPER_RIGHT,
    MIDDLE: MIDDLE,
}


def opposite(d: Direction) -> Direction:
    return _OPPOSITE[d]


def grid_offset(c: GridCoord, d: Direction) -> GridCoord:
    return GridCoord(c.x + d.x, c.y + d.y)


def drawing_offset(c: DrawingCoord, d: Direction) -> DrawingCoord:
    return DrawingCoord(c.x + d.x, c.y + d.y)


def determine_direction(from_: tuple[int, int], to: tuple[int, int]) -> Direction:
    """The 8-way direction from `from_` to `to`. Ported from cmd/draw.go's
    `determineDirection` -- works on either grid or drawing coordinates."""
    if from_[0] == to[0]:
        return DOWN if from_[1] < to[1] else UP
    if from_[1] == to[1]:
        return RIGHT if from_[0] < to[0] else LEFT
    if from_[0] < to[0]:
        return LOWER_RIGHT if from_[1] < to[1] else UPPER_RIGHT
    return LOWER_LEFT if from_[1] < to[1] else UPPER_LEFT


def self_reference_direction(
    graph_direction: str,
) -> tuple[Direction, Direction, Direction, Direction]:
    """Start/end attachment directions for a self-referencing (node-to-itself)
    edge. Ported from cmd/direction.go's `selfReferenceDirection`."""
    if graph_direction == "LR":
        return RIGHT, DOWN, DOWN, RIGHT
    return DOWN, RIGHT, RIGHT, DOWN


def determine_start_and_end_dir(
    graph_direction: str, from_coord: GridCoord, to_coord: GridCoord
) -> tuple[Direction, Direction, Direction, Direction]:
    """Preferred/alternative start+end attachment directions for an edge
    between two distinct nodes. Ported verbatim (including its acknowledged
    rough edges -- see the TODOs in the upstream source) from cmd/direction.go's
    `determineStartAndEndDir`; self-referencing edges are handled separately by
    the caller via `self_reference_direction`."""
    d = determine_direction(from_coord, to_coord)

    is_backwards: bool
    if graph_direction == "LR":
        is_backwards = d in (LEFT, UPPER_LEFT, LOWER_LEFT)
    else:
        is_backwards = d in (UP, UPPER_LEFT, UPPER_RIGHT)

    if d == LOWER_RIGHT:
        if graph_direction == "LR":
            return DOWN, LEFT, RIGHT, UP
        return RIGHT, UP, DOWN, LEFT
    if d == UPPER_RIGHT:
        if graph_direction == "LR":
            return UP, LEFT, RIGHT, DOWN
        return RIGHT, DOWN, UP, LEFT
    if d == LOWER_LEFT:
        if graph_direction == "LR":
            return DOWN, DOWN, LEFT, UP
        return LEFT, UP, DOWN, RIGHT
    if d == UPPER_LEFT:
        if graph_direction == "LR":
            return DOWN, DOWN, LEFT, DOWN
        return RIGHT, RIGHT, UP, RIGHT

    if is_backwards:
        if graph_direction == "LR" and d == LEFT:
            return DOWN, DOWN, LEFT, RIGHT
        if graph_direction == "TD" and d == UP:
            return RIGHT, RIGHT, UP, DOWN
        preferred_opposite = opposite(d)
        return d, preferred_opposite, d, preferred_opposite

    preferred_opposite = opposite(d)
    return d, preferred_opposite, d, preferred_opposite
