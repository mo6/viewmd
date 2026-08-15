"""block-beta diagram renderer (VIEWMD-0040).

No upstream reference implementation to port from (mermaid-ascii has no
block-beta support), so this is hand-written against the maintainer-supplied
reference examples in the issue -- same posture as the pie/quadrant/kanban
renderers. Individual boxes and the one supported `-->` arrowhead reuse the
flowchart primitives (`canvas.draw_box`, `Graph._UNICODE_ARROWHEADS` /
`_ASCII_ARROWHEADS`); the new work is grid placement (columns / span / wrap)
and per-column width equalization.
"""

from __future__ import annotations

from dataclasses import dataclass

from viewmd.mermaid.block.parser import Block, BlockDiagram
from viewmd.mermaid.flowchart.graph import Graph
from viewmd.mermaid.flowchart.parser import BOX_BORDER_PADDING
from viewmd.mermaid.grid import canvas
from viewmd.mermaid.grid.coords import LEFT, RIGHT, Direction, DrawingCoord
from viewmd.mermaid.grid.label import LABEL_LINE_GAP, GraphLabel, new_graph_label
from viewmd.mermaid.textutil import width as string_width

__all__ = ["render"]

# Maintainer sign-off (a), 2026-08-15: 4-column gap, 1 blank line between rows.
_GAP = 4
_ROW_GAP = 1
# Leading pad matching the four reference examples' two-space indent.
_PAD_X = 2
# Requirement 8: inner content width is max(10, label_width + 2 * padding).
_MIN_INNER_WIDTH = 10


@dataclass
class _Placed:
    block: Block
    label: GraphLabel
    col: int
    row: int
    span: int
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


@dataclass
class _Section:
    columns: int | None
    placed: list[_Placed]


def _natural_box_width(label_width: int) -> int:
    """Requirement 8: outer box width (borders included) from a label's
    display width. Inner = max(10, label_width + 2 * box_border_padding);
    outer adds the two border columns."""
    inner = max(_MIN_INNER_WIDTH, label_width + 2 * BOX_BORDER_PADDING)
    return inner + 2


def _box_height(label: GraphLabel) -> int:
    # Top border + label content (with flowchart's inter-line gap) + bottom.
    return 1 + label.content_height() + 1


def _sections(diagram: BlockDiagram) -> list[_Section]:
    """Split declared blocks into runs sharing one `columns` setting. A new
    `columns N` directive starts a new section even when N is unchanged, so
    width equalization never crosses a directive (requirement 9: "under the
    currently active columns N count")."""
    sections: list[_Section] = []
    for block in diagram.blocks:
        if not sections or sections[-1].columns != block.columns:
            sections.append(_Section(columns=block.columns, placed=[]))
        sections[-1].placed.append(
            _Placed(
                block=block,
                label=new_graph_label(block.label),
                col=0,
                row=0,
                span=block.span,
            )
        )
    return sections


def _place_in_grid(section: _Section) -> None:
    """Left-to-right, top-to-bottom wrap (requirements 4-6)."""
    col = 0
    row = 0
    limit = section.columns
    for p in section.placed:
        if limit is not None and col + p.span > limit:
            row += 1
            col = 0
        p.col = col
        p.row = row
        col += p.span


def _column_widths(section: _Section) -> list[int]:
    """Requirement 9: each grid column is as wide as the widest span-1 block
    occupying it. Requirement 10: a spanning block's own label does not
    grow the columns it spans, so span>1 blocks are ignored here."""
    n_cols = section.columns
    if n_cols is None:
        n_cols = max((p.col + p.span for p in section.placed), default=0)
    widths = [_natural_box_width(0)] * n_cols  # min outer width (inner 10)
    for p in section.placed:
        if p.span != 1:
            continue
        widths[p.col] = max(widths[p.col], _natural_box_width(p.label.width))
    return widths


def _row_heights(section: _Section) -> dict[int, int]:
    heights: dict[int, int] = {}
    for p in section.placed:
        heights[p.row] = max(heights.get(p.row, 0), _box_height(p.label))
    return heights


def _spanned_width(col_widths: list[int], col: int, span: int) -> int:
    """Requirement 10: sum of spanned column widths plus the gaps between
    each pair of spanned columns."""
    return sum(col_widths[col : col + span]) + _GAP * (span - 1)


def _layout_section(section: _Section, y0: int) -> int:
    """Assign pixel x/y/width/height for every placed block. Returns the
    y-coordinate just past this section (not including a following row-gap)."""
    _place_in_grid(section)
    col_widths = _column_widths(section)
    row_heights = _row_heights(section)

    col_x = [_PAD_X]
    for w in col_widths[:-1]:
        col_x.append(col_x[-1] + w + _GAP)

    row_y = {0: y0} if row_heights else {}
    for r in sorted(row_heights):
        if r not in row_y:
            prev = r - 1
            row_y[r] = row_y[prev] + row_heights[prev] + _ROW_GAP

    for p in section.placed:
        p.x = col_x[p.col]
        p.y = row_y[p.row]
        p.width = _spanned_width(col_widths, p.col, p.span)
        p.height = row_heights[p.row]

    if not row_heights:
        return y0
    last = max(row_heights)
    return row_y[last] + row_heights[last]


def _arrowhead(direction: Direction, use_ascii: bool) -> str:
    table = Graph._ASCII_ARROWHEADS if use_ascii else Graph._UNICODE_ARROWHEADS
    return table[direction]


def _blocks_between(placed: list[_Placed], a: _Placed, b: _Placed) -> bool:
    """True if another block on the same row sits strictly between a and b
    horizontally -- a connector would overwrite it."""
    if a.x < b.x:
        gap_lo, gap_hi = a.x + a.width, b.x
    else:
        gap_lo, gap_hi = b.x + b.width, a.x
    for p in placed:
        if p is a or p is b or p.row != a.row:
            continue
        if p.x < gap_hi and p.x + p.width > gap_lo:
            return True
    return False


def _draw_edge(d: canvas.Drawing, src: _Placed, dst: _Placed, use_ascii: bool) -> None:
    """Horizontal connector filling the gap between two same-row blocks,
    arrowhead at the destination (requirement 7). Vertical / non-same-row
    edges are a Non-goal and are skipped."""
    if src.row != dst.row or src.y != dst.y:
        return
    mid_y = src.y + src.height // 2
    if src.x + src.width <= dst.x:
        start = DrawingCoord(src.x + src.width, mid_y)
        end = DrawingCoord(dst.x - 1, mid_y)
        direction: Direction = RIGHT
    elif dst.x + dst.width <= src.x:
        start = DrawingCoord(src.x - 1, mid_y)
        end = DrawingCoord(dst.x + dst.width, mid_y)
        direction = LEFT
    else:
        return
    if start.x == end.x and start.y == end.y:
        d[end.x][end.y] = _arrowhead(direction, use_ascii)
        return
    drawn = canvas.draw_line(d, start, end, 0, 0, use_ascii)
    if drawn:
        last = drawn[-1]
        d[last.x][last.y] = _arrowhead(direction, use_ascii)


def _place_label(d: canvas.Drawing, p: _Placed) -> canvas.Drawing:
    """Center each label line inside `p`'s box: extra column of padding on
    the right when the remainder is odd (requirement 8)."""
    inner_width = p.width - 2
    inner_height = p.height - 2
    content_height = p.label.content_height()
    top = p.y + 1 + max(inner_height - content_height, 0) // 2
    for i, line in enumerate(p.label.lines):
        lw = string_width(line)
        left = max(inner_width - lw, 0) // 2
        d = canvas.draw_text(
            d, DrawingCoord(p.x + 1 + left, top + i * (LABEL_LINE_GAP + 1)), line
        )
    return d


def render(diagram: BlockDiagram, *, use_ascii: bool = False) -> str:
    sections = _sections(diagram)
    y = 0
    for i, section in enumerate(sections):
        if i:
            y += _ROW_GAP
        y = _layout_section(section, y)

    placed = [p for s in sections for p in s.placed]
    if not placed:
        return ""

    max_x = max(p.x + p.width - 1 for p in placed)
    max_y = max(p.y + p.height - 1 for p in placed)
    d = canvas.mk_drawing(max_x, max_y)

    blank = GraphLabel(lines=[""], width=0)
    for p in placed:
        # Borders from flowchart's draw_box; label placement is requirement 8's
        # own floor-left/ceil-right split, which agrees with draw_box's
        # `_place_label` on the reference examples' widths but not on every
        # equalized-column width (the widen fixture).
        box = canvas.draw_box(
            p.width - 1,
            p.height - 1,
            blank,
            "",
            use_ascii,
        )
        d = canvas.merge_drawings(d, DrawingCoord(p.x, p.y), box, use_ascii=use_ascii)
        d = _place_label(d, p)

    by_id = {p.block.id: p for p in placed}
    for edge in diagram.edges:
        src = by_id.get(edge.src)
        dst = by_id.get(edge.dst)
        if src is None or dst is None:
            continue
        if _blocks_between(placed, src, dst):
            continue
        _draw_edge(d, src, dst, use_ascii)

    text = canvas.drawing_to_string(d)
    return "\n".join(line.rstrip() for line in text.split("\n"))
