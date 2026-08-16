#!/usr/bin/env python3
"""Proof of concept for VIEWMD-0048 (Mermaid xychart-beta charts).

Not part of the shipped `viewmd` package -- a throwaway script used to generate the
step/staircase-line and eighth-block-bar mockups in the issue file
(../../issues/VIEWMD-0048-mermaid-xy-charts.md) programmatically instead of drawing them by hand.
A hand-drawn attempt at the 13-category real-data mockup silently dropped a whole riser transition
and only got caught on review; a small script implementing requirement 7's rules exactly (rounded
corners at value transitions, row-centered eighth-block bar fill) doesn't make that kind of mistake.

    python3 poc/xychart/xychart_poc.py combo
    python3 poc/xychart/xychart_poc.py line
    python3 poc/xychart/xychart_poc.py nvda

Each subcommand hardcodes one of the issue's mockup datasets (`combo`: the "Sales vs Target"
bar+line combo, `line`: the "Revenue Trend" line-only chart, `nvda`:
docs/nvidia-stock-xychart.md's 13-category real data) and prints the rendered mockup plus a couple
of debug numbers (rounded values, row count) to stderr-equivalent trailing lines. Not wired into
`./run-tests.sh` or `./tools.sh` -- this is scratch tooling for authoring the issue, not a fixture
generator for the eventual `viewmd/mermaid/xychart/` implementation.
"""

from __future__ import annotations

import sys


def build_line_grid(values, y_min, y_max, step, col_width, ascii_corners=False):
    """Render a `line` dataset as an orthogonal step/staircase (requirement 7).

    Returns `(grid, total_width, levels)` where `grid` maps each row's value to a list of
    characters, `levels` is the list of row values from `y_max` down to (excluding) `y_min` --
    `y_min` itself is the axis baseline, drawn separately by `render()`.
    """
    n = len(values)
    total_w = n * col_width
    levels = list(range(y_max, y_min, -step))
    grid = {lv: [' '] * total_w for lv in levels}

    tl, tr, bl, br = ('+', '+', '+', '+') if ascii_corners else ('╭', '╮', '╰', '╯')

    # Runs of consecutive equal values merge into one flat span with no riser between them.
    runs = []
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[j + 1] == values[i]:
            j += 1
        runs.append((i, j + 1, values[i]))  # [start_idx, end_idx), value
        i = j + 1

    for ridx, (a, b, v) in enumerate(runs):
        left_start = a * col_width if a == 0 else a * col_width + 1
        right_end = b * col_width if b == n else b * col_width
        for c in range(left_start, right_end):
            grid[v][c] = '─'
        if a > 0:
            prev_v = runs[ridx - 1][2]
            col = a * col_width
            grid[v][col] = tl if v > prev_v else bl
            lo, hi = min(v, prev_v), max(v, prev_v)
            for lv in levels:
                if lo < lv < hi:
                    grid[lv][col] = '│'
        if b < n:
            next_v = runs[ridx + 1][2]
            col = b * col_width
            grid[v][col] = br if next_v > v else tr
    return grid, total_w, levels


def build_bar_fill(bar_values, y_min, y_max, step, col_width, n):
    """Render a `bar` dataset with row-centered eighth-block fill (requirement 7).

    A tick row labeled `V` represents the band `[V - step/2, V + step/2)` -- the same band a
    `line` value of `V` would be drawn centered on -- not a band ending at `V`. A bar landing
    exactly on a tick therefore shows a half-block (`▄`), not a clean full top.
    """
    total_w = n * col_width
    levels = list(range(y_max, y_min, -step))
    eighths = ' ▁▂▃▄▅▆▇█'
    grid = {lv: [' '] * total_w for lv in levels}
    for i, h in enumerate(bar_values):
        col0, col1 = i * col_width, (i + 1) * col_width
        for lv in levels:
            lo, hi = lv - step / 2, lv + step / 2
            if hi <= h:
                ch = '█'
            elif lo <= h < hi:
                level = round((h - lo) / step * 8)
                ch = eighths[level]
                if ch == ' ':
                    continue
            else:
                continue
            for c in range(col0, col1):
                grid[lv][c] = ch
    return grid


def merge(bar_grid, line_grid):
    """Overlay a line grid on a bar grid -- the line dataset wins wherever both draw a cell."""
    merged = {}
    for lv in line_grid:
        row = list(bar_grid.get(lv, [' '] * len(line_grid[lv])))
        for c, ch in enumerate(line_grid[lv]):
            if ch != ' ':
                row[c] = ch
        merged[lv] = row
    return merged


def render(levels, total_w, grid, cats, col_width, label_width, y_min):
    lines = []
    for lv in levels:
        row = ''.join(grid[lv])
        lines.append(f"{str(lv).rjust(label_width)} │{row}")
    axis = '└' + ('┬' + '─' * (col_width - 1)) * len(cats)
    lines.append(f"{str(y_min).rjust(label_width)} {axis}")
    label_line = ' ' * (label_width + 1)
    for c in cats:
        label_line += c.ljust(col_width)
    lines.append(label_line.rstrip())
    return '\n'.join(lines)


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else ''

    if which == 'combo':
        cats = ['Q1', 'Q2', 'Q3', 'Q4']
        bar_vals = [40, 60, 80, 100]
        line_vals = [60, 80, 100, 120]
        y_min, y_max, step = 0, 120, 5
        col_width = 10
        line_grid, total_w, levels = build_line_grid(line_vals, y_min, y_max, step, col_width)
        bar_grid = build_bar_fill(bar_vals, y_min, y_max, step, col_width, len(cats))
        merged = merge(bar_grid, line_grid)
        print(render(levels, total_w, merged, cats, col_width, 3, y_min))

    elif which == 'line':
        cats = ['Q1', 'Q2', 'Q3', 'Q4']
        line_vals = [40, 60, 20, 100]
        y_min, y_max, step = 0, 100, 5
        col_width = 10
        line_grid, total_w, levels = build_line_grid(line_vals, y_min, y_max, step, col_width)
        print(render(levels, total_w, line_grid, cats, col_width, 3, y_min))

    elif which == 'nvda':
        cats = ['Aug25', 'Sep25', 'Oct25', 'Nov25', 'Dec25', 'Jan26', 'Feb26', 'Mar26',
                'Apr26', 'May26', 'Jun26', 'Jul26', 'Aug26']
        raw = [173.95, 186.34, 202.23, 176.77, 186.27, 190.90, 176.97, 174.20, 199.34,
               210.89, 200.09, 200.75, 225.16]
        step = 3
        y_min, y_max = 150, 230
        # Round relative to y_min so every rounded value lands on a row the grid actually has
        # (rounding relative to zero would put values on a different residue class mod step).
        vals = [y_min + round((v - y_min) / step) * step for v in raw]
        y_max_aligned = y_min + ((y_max - y_min) // step) * step
        col_width = 7
        line_grid, total_w, levels = build_line_grid(vals, y_min, y_max_aligned, step, col_width)
        print(render(levels, total_w, line_grid, cats, col_width, 3, y_min))
        print()
        print('rounded values:', vals, 'num data rows:', len(levels),
              'y_max_aligned:', y_max_aligned)

    else:
        print(f"usage: {sys.argv[0]} {{combo|line|nvda}}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
