"""A* pathfinding over the integer grid, used to route flowchart edges around
node obstacles. Ported from cmd/arrow.go's `getPath`/`heuristic`, then extended
by VIEWMD-0025 so corner count participates in the real cost (not only the
heuristic's search-order bias).

When several equal-cost paths exist, which one A* returns depends on the
priority queue's exact pop order for tied priorities. Go's `priorityQueue`
(container/heap) breaks ties purely by heap array structure -- it has no
secondary comparison key -- so Python's `heapq` (a different, though also
standard, binary heap implementation) can pop equal-priority items in a
different order and silently pick a different, equally-valid route. `_GoHeap`
below ports container/heap's own push/pop/up/down algorithm verbatim so the
exact sequence of comparisons -- and thus tie-break outcomes -- matches.
"""

from __future__ import annotations

from viewmd.mermaid.grid.coords import GridCoord

_NEIGHBOR_OFFSETS = (GridCoord(1, 0), GridCoord(-1, 0), GridCoord(0, 1), GridCoord(0, -1))

# Cost encoding: one grid step costs `_STEP`, a direction change costs
# `_CORNER` on top. `_STEP` is larger than any plausible corner-count
# difference on a flowchart grid, so a longer Manhattan path can never beat a
# shorter one just by taking fewer turns (VIEWMD-0025 req. 2) -- corners only
# tie-break among equal-length candidates.
_STEP = 10_000
_CORNER = 1

# Heap / came_from / cost_so_far carry the inbound step direction alongside the
# coordinate: arriving at the same cell going straight vs via a turn are
# different states with different continuation costs. Heap items are
# `(priority, path_cost, coord, direction)` so stale entries (same state
# reached later at a worse cost) can be skipped on pop.
_HeapItem = tuple[int, int, GridCoord, GridCoord | None]
_State = tuple[GridCoord, GridCoord | None]


class _GoHeap:
    """Direct port of Go's `container/heap` push/pop, operating on
    `(priority, path_cost, coord, direction)` items and comparing only
    `priority` (matching the upstream `priorityQueue.Less`, which has no
    secondary key)."""

    def __init__(self) -> None:
        self.items: list[_HeapItem] = []

    def push(self, item: _HeapItem) -> None:
        self.items.append(item)
        self._up(len(self.items) - 1)

    def pop(self) -> _HeapItem:
        n = len(self.items) - 1
        self.items[0], self.items[n] = self.items[n], self.items[0]
        self._down(0, n)
        return self.items.pop()

    def __len__(self) -> int:
        return len(self.items)

    def _less(self, i: int, j: int) -> bool:
        return self.items[i][0] < self.items[j][0]

    def _up(self, j: int) -> None:
        while True:
            # Go's `(j-1)/2` truncates toward zero, so j==0 gives i=0 (not -1
            # as Python's floor-dividing `//` would, which would then index
            # `items[-1]` -- the array's *last* element -- instead of
            # recognizing the root has no parent.
            i = (j - 1) // 2 if j > 0 else 0
            if i == j or not self._less(j, i):
                break
            self.items[i], self.items[j] = self.items[j], self.items[i]
            j = i

    def _down(self, i0: int, n: int) -> None:
        i = i0
        while True:
            j1 = 2 * i + 1
            if j1 >= n or j1 < 0:
                break
            j = j1
            j2 = j1 + 1
            if j2 < n and self._less(j2, j1):
                j = j2
            if not self._less(j, i):
                break
            self.items[i], self.items[j] = self.items[j], self.items[i]
            i = j


def heuristic(a: GridCoord, b: GridCoord) -> int:
    """Admissible, consistent estimate in the same units as `find_path`'s cost
    (`_STEP` per grid step). Corner preference lives entirely in the real cost
    function (VIEWMD-0025); the old +1 off-axis bias is gone."""
    return (abs(a.x - b.x) + abs(a.y - b.y)) * _STEP


def find_path(start: GridCoord, goal: GridCoord, is_free) -> list[GridCoord] | None:
    """`is_free(coord) -> bool` reports whether a grid cell is free to route
    through; the goal cell is always treated as reachable even if occupied
    (it's inside the target node's own border)."""
    heap = _GoHeap()
    start_state: _State = (start, None)
    heap.push((0, 0, start, None))
    cost_so_far: dict[_State, int] = {start_state: 0}
    came_from: dict[_State, _State | None] = {start_state: None}

    while len(heap) > 0:
        _, path_cost, current, current_dir = heap.pop()
        current_state: _State = (current, current_dir)
        if path_cost > cost_so_far[current_state]:
            continue

        if current == goal:
            path: list[GridCoord] = []
            state: _State | None = current_state
            while state is not None:
                path.append(state[0])
                state = came_from[state]
            path.reverse()
            return path

        for offset in _NEIGHBOR_OFFSETS:
            nxt = GridCoord(current.x + offset.x, current.y + offset.y)
            if not is_free(nxt) and nxt != goal:
                continue
            turn = 0 if current_dir is None or current_dir == offset else _CORNER
            new_cost = path_cost + _STEP + turn
            nxt_state: _State = (nxt, offset)
            if nxt_state not in cost_so_far or new_cost < cost_so_far[nxt_state]:
                cost_so_far[nxt_state] = new_cost
                priority = new_cost + heuristic(nxt, goal)
                heap.push((priority, new_cost, nxt, offset))
                came_from[nxt_state] = current_state

    return None


def merge_path(path: list[GridCoord]) -> list[GridCoord]:
    """Collapse consecutive colinear steps into one. Ported from cmd/arrow.go's
    `mergePath`."""
    if len(path) <= 2:
        return path
    from viewmd.mermaid.grid.coords import determine_direction

    indices_to_remove: set[int] = set()
    step0, step1 = path[0], path[1]
    for idx, step2 in enumerate(path[2:]):
        prev_dir = determine_direction(step0, step1)
        dir_ = determine_direction(step1, step2)
        if prev_dir == dir_:
            indices_to_remove.add(idx + 1)
        step0, step1 = step1, step2
    return [step for idx, step in enumerate(path) if idx not in indices_to_remove]
