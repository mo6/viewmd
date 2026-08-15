---
title: How A* pathfinding works
author: viewmd
tags: [algorithms, astar, showcase]
status: draft
---

# How A* pathfinding works

A* is the search algorithm viewmd's flowchart renderer uses to route edges around obstacles on
the grid (`viewmd/mermaid/grid/astar.py`, see `VIEWMD-0025`). This note explains the algorithm
itself, independent of that code, with a small worked example.

View this file with `./viewmd.sh docs/astar-algorithm.md`.

## The idea

A* finds the shortest path between a start node and a goal node by combining two things at every
step:

- **`g(n)`** -- the actual cost of the path from the start to `n` (known exactly, since it's
  already been walked)
- **`h(n)`** -- a heuristic *estimate* of the remaining cost from `n` to the goal (a guess, e.g.
  straight-line or Manhattan distance)

Every candidate node is scored `f(n) = g(n) + h(n)`, and the algorithm always expands whichever
node in its frontier has the lowest `f`. This makes it greedy toward the most *promising overall*
route, not just the closest-so-far (that's Dijkstra, which ignores where the goal is) and not
just the closest-looking-to-goal (plain greedy best-first, which ignores sunk cost).

## The algorithm

1. Put the start node in an **open set** (a priority queue ordered by `f`), with `g = 0`.
2. Loop:
   - Pop the node with the lowest `f` -- call it `current`.
   - If `current` is the goal, reconstruct the path from stored parent pointers and stop.
   - Otherwise move `current` into a **closed set** (visited).
   - For each neighbor of `current`, compute a tentative `g = g(current) + cost(current, neighbor)`.
     If that's better than any previously known `g` for that neighbor, record it, set the
     neighbor's parent to `current`, and push/update it in the open set with `f = g + h`.
3. If the open set empties before the goal is reached, no path exists.

**Why the heuristic matters:** with `h(n) = 0` everywhere, A* degenerates into Dijkstra's
algorithm -- correct, but explores in every direction equally. A good heuristic steers the search
toward the goal instead. For A* to still guarantee the optimal path, `h` must be **admissible**
(never overestimate the true remaining cost); if it's also **consistent**, closed nodes never
need to be reopened.

## Worked example

A 4x4 grid, moving up/down/left/right at cost 1 per step (no diagonals), with a wall blocking
column 1 in rows 1-2:

```
Grid:                Heuristic h(r,c) = Manhattan distance to G
S . . .               6 5 4 3
. # . .               5 . 3 2
. # . .               4 . 2 1
. . . G               3 2 1 0
```

`S = (0,0)`, `G = (3,3)`, `#` = wall. `f = g + h` at every node.

| Step | Pop node | g | h | f | New neighbors pushed |
|---|---|---|---|---|---|
| 1 | (0,0) | 0 | 6 | 6 | (0,1) f6, (1,0) f6 |
| 2 | (0,1) | 1 | 5 | 6 | (0,2) f6 |
| 3 | (1,0) | 1 | 5 | 6 | (2,0) f6 |
| 4 | (0,2) | 2 | 4 | 6 | (0,3) f6, (1,2) f6 |
| 5 | (2,0) | 2 | 4 | 6 | (3,0) f6 |
| 6 | (0,3) | 3 | 3 | 6 | (1,3) f6 |
| 7 | (1,2) | 3 | 3 | 6 | (2,2) f6 |
| 8 | (3,0) | 3 | 3 | 6 | (3,1) f6 |
| 9 | (1,3) | 4 | 2 | 6 | (2,3) f6 |
| 10 | (2,2) | 4 | 2 | 6 | (3,2) f6 |
| 11 | (3,1) | 4 | 2 | 6 | (dead end -- wall/visited) |
| 12 | (2,3) | 5 | 1 | 6 | **(3,3) = G**, f6 |
| 13 | pop G | 6 | 0 | 6 | goal reached, stop |

Every node on the frontier stays at `f = 6` throughout -- the heuristic is a perfect estimate
here, so A* never wastes effort exploring a worse-looking direction. It still explores two
roughly parallel branches (go right first vs. go down first) because they're genuinely tied, but
it never touches the wall cells or loops back on itself.

Reconstructing the path by following parent pointers back from `G`:

```
(0,0) -> (0,1) -> (0,2) -> (0,3) -> (1,3) -> (2,3) -> (3,3)=G
```

```
* * * *
. # . *
. # . *
. . . *
```

Total cost is 6, matching the straight-line Manhattan distance from `S` to `G` -- confirming this
route is optimal.

## Real case: routing `B -> D` around `C`

The worked example above is a clean, single-obstacle grid. viewmd's flowchart router faces a
messier version of the same problem on every diagram, and one real instance is worth walking
through because it shows a tie that neither the base algorithm nor `VIEWMD-0025`'s corner cost
actually resolves on its own -- something else has to.

Source (`tests/fixtures/mermaid_flowchart/obstacle_routing.mmd`):

```
graph TD
  A --> B
  A --> C
  B --> D
  C --> D
  A --> D
```

`B`, `C`, `D` sit in a row below `A`. Routing `B -> D` has to get around `C`'s box, which sits
directly between them, and the grid has open space both above that row (up near `A`'s edges) and
below it (empty, nothing there). Two candidate routes are equally short -- 10 grid steps, 4
corners each:

```
above C (weaves up past A -> C's line)     below C (loops through empty space)
                                          
  B ┐                                       B ┐
    └───────┐                                 │
            │                                 └───────┐
        ┌───┼───┐                          ┌───┬───┐  │
        │   C   │                          │   C   │  │
        └───┼───┘                          └───┴───┘  │
            │                                         │
            └──► D                           ┌────────┘
                                             └──► D
```

`viewmd/mermaid/grid/astar.py`'s cost function (as of `VIEWMD-0025` plus the tie-break described
below) charges, per step:

```
_STEP     = 1,000,000   # every grid step
_CORNER   = 100          # step direction differs from the previous step
_BACKWARD = 1            # step direction is "north" (the graph's TD layout runs top-to-bottom,
                          # so north is the one axis that runs against the flow)
```

Both candidate routes take the same 10 steps and the same 4 turns, so `_STEP` and `_CORNER`
contribute identically to each: `10 x 1,000,000 + 4 x 100 = 10,000,400`. The difference is meant
to come from `_BACKWARD` -- except here it doesn't discriminate between these two shapes either:
the "above" route goes north twice to get past `C`, then south twice to come back down into `D`'s
row; the "below" route goes south twice to get past `C`, then north twice to come back up into
`D`'s row. Both incur the north penalty exactly twice, so **both routes cost exactly
`10,000,402`** -- a genuine, exact tie, all the way down to the last unit.

This is the case the base algorithm (and even `VIEWMD-0025`'s corner cost) was never going to
settle: `f` cannot distinguish two candidates whose true cost is identical. What decides the
outcome instead is *discovery order* -- `find_path`'s inner loop only replaces a state's recorded
cost when a **strictly** cheaper path to it turns up (`new_cost < cost_so_far[state]`); an
equal-cost arrival is silently discarded. So whichever of the two mirror-image routes A* happens
to finish exploring *first* is the one that sticks, and every term in the cost function --
`_STEP`, `_CORNER`, and `_BACKWARD` alike -- shapes the priority queue's pop order and therefore
that exploration order, even among states whose final tied cost none of those terms actually
separates. Adding `_BACKWARD` shifted that order enough to flip which mirror-image route wins,
without ever making one route cheaper than the other on paper.

The payoff is that the winning shape is the nicer one to read: the "below" route stays clear of
the row `A`'s other edges (`A -> C`, `A -> D`) already occupy, instead of crowding past them. That
was a happy consequence of nudging the search, not something the cost function was able to price
in directly -- see the last takeaway below.

Rendered (`./viewmd.sh docs/mermaid-flowchart.md`, `obstacle_routing` fixture):

```
┌───┐
│ A ├─────┬───────┐
└─┬─┘     │       │
  │       │       │
  ▼       ▼       ▼
┌───┐   ┌───┐   ┌───┐
│ B ├─┐ │ C ├─┬►│ D │
└───┘ │ └───┘ │ └───┘
      │       │
      └───────┘
```

## Takeaways

- Ties in `f` are common and harmless -- any tie-break order still finds a shortest-length path,
  just possibly a different specific route among equal-length candidates.
- A blocked cell is simply never generated as a neighbor -- A* doesn't need special-case wall
  handling beyond that.
- A node's `g` is only updated (and re-pushed) when a cheaper path to it is found; in this example
  every node was reached optimally on its first visit, so no updates were needed.
- `f` alone doesn't distinguish between equal-length paths with different *shapes* (e.g. fewer
  corners) -- that requires folding a shape preference into the cost function itself, which is
  exactly what `VIEWMD-0025` does for flowchart edge routing.
- Folding a preference into the cost function only helps when it actually prices two candidates
  differently. When it doesn't (the `B -> D` case above), the tie is still broken -- just
  indirectly, through the same "first exact-cost arrival wins" mechanism that resolves any other
  A* tie, with the cost function's terms only steering *when* each candidate gets discovered.
