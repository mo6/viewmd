"""gitGraph LR renderer (VIEWMD-0042).

No upstream reference implementation to port from (see parser.py's module
docstring), so this is hand-authored directly against the maintainer-supplied
reference examples in the issue -- fixtures here are hand-verified against
those, not differentially tested against an oracle.

Layout model: one text row-triple (tag/connector row, dash+marker row, id-
label row) per lane (branch), in first-appearance order, plus one leading
blank line. Every `commit`/`merge`/`cherry-pick` claims the next timeline
column; each lane's marker row draws its own commits as `●` connected by
`─`, and a `GitConnector` (from parser.py) draws a vertical `│` between two
lanes at a single column, merging into `┼`/`├`/`┤` via
`viewmd.mermaid.grid.canvas`'s existing junction table wherever it crosses a
lane's own horizontal content, the same reuse the sequence renderer makes of
that machinery for its fixed lifelines.
"""

from __future__ import annotations

from viewmd.mermaid.gitgraph.parser import GitBranch, GitGraph
from viewmd.mermaid.grid.canvas import is_junction_char, merge_junctions

# Two leading indent columns before the branch-name prefix, one column
# separating the (possibly padded) name from the lane's dash line, and a
# minimum 2-column lead-in of dashes before the very first commit on the
# lane that owns timeline column 0 (always the first-declared branch).
_INDENT = 2
_MIN_LEADIN = 2
_MIN_SPACING = 6

__all__ = ["render"]


def render(graph: GitGraph, *, use_ascii: bool = False) -> str:
    if not graph.branches:
        raise ValueError("no branches")

    dash, vbar, marker = ("-", "|", "o") if use_ascii else ("─", "│", "●")

    def merge_v(existing: str) -> str:
        """Overlay a vertical connector glyph onto `existing`, merging into a
        junction where it crosses horizontal content (unicode mode only --
        ASCII has no directional junction alphabet, so it just overwrites)."""
        if not use_ascii and is_junction_char(existing):
            return merge_junctions(existing, vbar)
        return vbar

    # --- column layout -----------------------------------------------------
    commits_by_column: dict[int, tuple[GitBranch, int]] = {}  # column -> (branch, index)
    for b in graph.branches:
        for idx, c in enumerate(b.commits):
            commits_by_column[c.column] = (b, idx)
    n_columns = len(commits_by_column)

    def _label_and_tag(column: int) -> tuple[str, str | None]:
        b, idx = commits_by_column[column]
        c = b.commits[idx]
        return c.label, c.tag

    def _slot_width(column: int) -> int:
        label, tag = _label_and_tag(column)
        w = len(label)
        if tag:
            w = max(w, len(tag) + 2)  # "[tag]"
        return w

    def _extent(w: int) -> tuple[int, int]:
        left = w // 2
        right = w - 1 - w // 2
        return left, right

    max_name_len = max(len(b.name) for b in graph.branches)
    prefix_width = _INDENT + max_name_len + 1

    centers: list[int] = [0] * n_columns
    for col in range(n_columns):
        w = _slot_width(col)
        if col == 0:
            left0, _ = _extent(w)
            centers[0] = prefix_width + max(_MIN_LEADIN, 1 + left0)
        else:
            _, right_prev = _extent(_slot_width(col - 1))
            left_cur, _ = _extent(w)
            _, tag = _label_and_tag(col)
            gap = 4 if tag else 3
            spacing = max(_MIN_SPACING, gap + right_prev + left_cur)
            centers[col] = centers[col - 1] + spacing

    # --- text-row bookkeeping ------------------------------------------------
    # Each lane (branch, in first-appearance order) owns 3 consecutive output
    # lines: a top row (blank, or this lane's commit tags), a dash/marker row,
    # and an id-label row -- preceded by one fixed leading blank line.
    def top_line(row: int) -> int:
        return 1 + 3 * row

    def dash_line(row: int) -> int:
        return 2 + 3 * row

    def id_line(row: int) -> int:
        return 3 + 3 * row

    n_lines = 1 + 3 * len(graph.branches)
    total_width = (centers[-1] if centers else prefix_width) + 2
    grid: list[list[str]] = [[" "] * total_width for _ in range(n_lines)]

    def ensure_width(w: int) -> None:
        nonlocal total_width, grid
        if w <= total_width:
            return
        for row in grid:
            row.extend(" " * (w - total_width))
        total_width = w

    def place(line: int, col: int, text: str) -> None:
        if col < 0:
            text = text[-col:]
            col = 0
        ensure_width(col + len(text))
        for i, ch in enumerate(text):
            grid[line][col + i] = ch

    # --- per-lane touched columns (own commits + connector passthroughs) ---
    touched: list[set[int]] = [set() for _ in graph.branches]
    for b in graph.branches:
        for c in b.commits:
            touched[b.row].add(c.column)
    for conn in graph.connectors:
        lo, hi = sorted((conn.owner_row, conn.other_row))
        for row in range(lo, hi + 1):
            if row != conn.owner_row:
                touched[row].add(conn.column)

    # --- draw each lane's prefix + dash background --------------------------
    for b in graph.branches:
        dl = dash_line(b.row)
        place(dl, 0, " " * _INDENT + b.name.ljust(max_name_len) + " ")
        cols = touched[b.row]  # timeline column indices, not grid columns
        if not cols:
            continue
        own_cols = {c.column for c in b.commits}
        grid_cols = {centers[c] for c in cols}
        if b.row == 0:
            min_col = prefix_width
        else:
            min_col = centers[min(own_cols)] if own_cols else min(grid_cols)
        max_col = max(grid_cols)
        # A trailing dash extends one column past the lane's own rightmost
        # commit; a passthrough junction (not this lane's own commit) gets no
        # trailing dash, matching the reference examples.
        max_fill = max_col + 1 if max(cols) in own_cols else max_col
        ensure_width(max_fill + 1)
        for col in range(min_col, max_fill + 1):
            grid[dl][col] = dash

    # --- draw commit markers, id labels, tags --------------------------------
    for b in graph.branches:
        dl, il, tl = dash_line(b.row), id_line(b.row), top_line(b.row)
        for c in b.commits:
            grid_col = centers[c.column]
            ensure_width(grid_col + 1)
            grid[dl][grid_col] = marker
            if c.label:
                place(il, grid_col - len(c.label) // 2, c.label)
            if c.tag:
                bracket = f"[{c.tag}]"
                place(tl, grid_col - len(bracket) // 2, bracket)

    # --- draw connectors ------------------------------------------------------
    for conn in graph.connectors:
        col = centers[conn.column]
        owner_dl = dash_line(conn.owner_row)
        other_dl = dash_line(conn.other_row)
        lo_line, hi_line = sorted((owner_dl, other_dl))
        for line in range(lo_line, hi_line + 1):
            if line == owner_dl:
                continue  # the owner's own marker already sits here
            ensure_width(col + 1)
            cell = grid[line][col]
            # Only merge into background (blank, or an existing junction/dash
            # from this line's own horizontal content) -- never clobber real
            # text, which happens when this column also happens to be the
            # owner's own tag/id-label column (both centered on the same
            # column as the marker).
            if cell == " " or (not use_ascii and is_junction_char(cell)) or cell in (dash, vbar):
                grid[line][col] = merge_v(cell)

    lines = ["".join(row).rstrip(" ") for row in grid]
    return "\n".join(lines) + "\n"
