"""Mindmap diagram renderer (VIEWMD-0045).

No upstream reference implementation to port from (mermaid-ascii has no
mindmap support). The recursive-height-then-connect layout -- children fan
right of each parent, overflowing some root children to the left once the
fan would grow too tall -- follows termaid's `renderer/mindmap.py` as a
design reference (see the issue's Design notes), not a byte-for-byte oracle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from viewmd.mermaid.grid.canvas import wrap_text_bold, wrap_text_italic, wrap_text_styled
from viewmd.mermaid.mindmap.parser import MindmapDiagram, MindmapNode
from viewmd.mermaid.textutil import width as string_width

__all__ = ["render"]

# Labels may carry bold/italic SGR wraps; layout math must ignore them.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _visible_width(s: str) -> int:
    return string_width(_ANSI_RE.sub("", s))

# Requirement 6: once a single-direction fan-out would grow too tall, spill
# some root children to the left. Threshold mirrors termaid's own cutoff
# (design choice left open by the issue; Non-goals say we need not match
# termaid's exact split heuristic beyond "a second side is used at all").
_OVERFLOW_THRESHOLD = 6


@dataclass(frozen=True)
class _Glyphs:
    h: str
    v: str
    tl: str  # ╭ / +
    bl: str  # ╰ / +
    tee: str  # ├ / +
    tj: str  # ┤ mid-junction on a right-fan column
    tr: str  # ╮ (left-fan mirror)
    br: str  # ╯
    tee_l: str  # ┤ left-facing tee
    tj_l: str  # ├ mid-junction on a left-fan column


_UNICODE = _Glyphs(
    h="─", v="│", tl="╭", bl="╰", tee="├", tj="┤",
    tr="╮", br="╯", tee_l="┤", tj_l="├",
)
_ASCII = _Glyphs(
    h="-", v="|", tl="+", bl="+", tee="+", tj="+",
    tr="+", br="+", tee_l="+", tj_l="+",
)


def _format_label(node: MindmapNode) -> str:
    """ANSI-wrap a node's markdown spans (requirement 8). Bold/italic are
    text styling, not color -- applied even when `color=False`."""
    parts: list[str] = []
    for text, bold, italic in node.segments:
        if not text:
            continue
        if bold and italic:
            parts.append(wrap_text_styled(text, bold=True, italic=True))
        elif bold:
            parts.append(wrap_text_bold(text))
        elif italic:
            parts.append(wrap_text_italic(text))
        else:
            parts.append(text)
    return "".join(parts) if parts else node.plain


def _pad_to(line: str, target: int, *, right: bool) -> str:
    """Pad `line` to visible display-width `target` (ANSI SGR ignored)."""
    gap = max(target - _visible_width(line), 0)
    if right:
        return (" " * gap) + line
    return line + (" " * gap)


def _split_children(
    children: list[MindmapNode],
) -> tuple[list[MindmapNode], list[MindmapNode]]:
    if len(children) <= _OVERFLOW_THRESHOLD:
        return [], list(children)
    n_left = max(1, min(len(children) // 3, len(children) - 1))
    return children[:n_left], children[n_left:]


def _render_subtree_right(node: MindmapNode, g: _Glyphs) -> tuple[list[str], int]:
    if not node.children:
        return [_format_label(node)], 0

    child_block, child_conn = _stack_right(node.children, g)
    suffix = " " + g.h + g.h
    connector = _format_label(node) + suffix
    pad = (" " * string_width(node.plain)) + (" " * string_width(suffix))
    result: list[str] = []
    for i, line in enumerate(child_block):
        result.append((connector if i == child_conn else pad) + line)
    return result, child_conn


def _stack_right(children: list[MindmapNode], g: _Glyphs) -> tuple[list[str], int]:
    if len(children) == 1:
        sub, sc = _render_subtree_right(children[0], g)
        result = []
        for i, line in enumerate(sub):
            if i == sc:
                result.append(g.h + g.h + " " + line)
            else:
                result.append("   " + line)
        return result, sc

    blocks = [_render_subtree_right(child, g) for child in children]
    result: list[str] = []
    conn_rows: list[int] = []

    for idx, (block, bc) in enumerate(blocks):
        is_first = idx == 0
        is_last = idx == len(blocks) - 1
        base = len(result)
        for li, line in enumerate(block):
            if li == bc:
                conn_rows.append(base + li)
                if is_first:
                    result.append(g.tl + g.h + " " + line)
                elif is_last:
                    result.append(g.bl + g.h + " " + line)
                else:
                    result.append(g.tee + g.h + " " + line)
            else:
                result.append(g.v + "  " + line)

    first_conn, last_conn = conn_rows[0], conn_rows[-1]
    for i in range(0, first_conn):
        if result[i].startswith(g.v):
            result[i] = " " + result[i][1:]
    for i in range(last_conn + 1, len(result)):
        if result[i].startswith(g.v):
            result[i] = " " + result[i][1:]

    mid = (first_conn + last_conn) // 2
    if mid not in conn_rows and result[mid].startswith(g.v):
        result[mid] = g.tj + result[mid][1:]

    return result, mid


def _render_subtree_left(node: MindmapNode, g: _Glyphs) -> tuple[list[str], int]:
    if not node.children:
        return [_format_label(node)], 0

    child_block, child_conn = _stack_left(node.children, g)
    child_width = max(_visible_width(line) for line in child_block)
    child_block = [_pad_to(line, child_width, right=True) for line in child_block]

    prefix = g.h + g.h + " "
    connector = prefix + _format_label(node)
    pad = (" " * string_width(prefix)) + (" " * string_width(node.plain))
    result: list[str] = []
    for i, line in enumerate(child_block):
        result.append(line + (connector if i == child_conn else pad))
    return result, child_conn


def _stack_left(children: list[MindmapNode], g: _Glyphs) -> tuple[list[str], int]:
    if len(children) == 1:
        sub, sc = _render_subtree_left(children[0], g)
        w = max(_visible_width(line) for line in sub)
        result = []
        for i, line in enumerate(sub):
            padded = _pad_to(line, w, right=True)
            if i == sc:
                result.append(padded + " " + g.h + g.h)
            else:
                result.append(padded + "   ")
        return result, sc

    blocks = [_render_subtree_left(child, g) for child in children]
    max_w = max(max(_visible_width(line) for line in block) for block, _ in blocks)
    result: list[str] = []
    conn_rows: list[int] = []

    for idx, (block, bc) in enumerate(blocks):
        is_first = idx == 0
        is_last = idx == len(blocks) - 1
        base = len(result)
        for li, line in enumerate(block):
            padded = _pad_to(line, max_w, right=True)
            if li == bc:
                conn_rows.append(base + li)
                if is_first:
                    result.append(padded + " " + g.h + g.tr)
                elif is_last:
                    result.append(padded + " " + g.h + g.br)
                else:
                    result.append(padded + " " + g.h + g.tee_l)
            else:
                # Keep a 3-column suffix on every row so the fan column stays
                # aligned with connection rows (`" " + h + corner`).
                if is_last:
                    result.append(padded + "   ")
                else:
                    result.append(padded + "  " + g.v)

    first_conn, last_conn = conn_rows[0], conn_rows[-1]
    for i in range(0, first_conn):
        if result[i].endswith(g.v):
            result[i] = result[i][:-1] + " "
    for i in range(last_conn + 1, len(result)):
        if result[i].endswith(g.v):
            result[i] = result[i][:-1] + " "

    mid = (first_conn + last_conn) // 2
    if mid not in conn_rows and result[mid].endswith(g.v):
        result[mid] = result[mid][:-1] + g.tj_l

    return result, mid


def _render_both_sides(
    root: MindmapNode,
    left_children: list[MindmapNode],
    right_children: list[MindmapNode],
    g: _Glyphs,
) -> list[str]:
    right_block, _ = _stack_right(right_children, g)
    left_block, _ = _stack_left(left_children, g)

    left_width = max((_visible_width(line) for line in left_block), default=0)
    rh, lh = len(right_block), len(left_block)
    total = max(rh, lh)
    r_off = (total - rh) // 2
    l_off = (total - lh) // 2
    root_row = total // 2

    mid = g.h + g.h + " " + _format_label(root) + " " + g.h + g.h
    pad = (
        (" " * 2)
        + " "
        + (" " * string_width(root.plain))
        + " "
        + (" " * 2)
    )

    result: list[str] = []
    for row in range(total):
        li = row - l_off
        left = (
            _pad_to(left_block[li], left_width, right=False)
            if 0 <= li < lh
            else " " * left_width
        )
        ri = row - r_off
        right = right_block[ri] if 0 <= ri < rh else ""
        center = mid if row == root_row else pad
        result.append(left + center + right)
    return result


def render(diagram: MindmapDiagram, *, use_ascii: bool = False) -> str:
    """Render a mindmap to Unicode (or ASCII) box-drawing art.

    Bold/italic label styling (requirement 8) is always applied -- it is text
    styling, not color, so it does not depend on the dispatch site's `color`
    flag.
    """
    if diagram.root is None:
        return ""

    g = _ASCII if use_ascii else _UNICODE
    root = diagram.root

    if not root.children:
        lines = [_format_label(root)]
    else:
        left_children, right_children = _split_children(root.children)
        if not left_children:
            # Fake a one-node tree so the root label sits left of its children.
            lines, _ = _render_subtree_right(
                MindmapNode(plain=root.plain, segments=root.segments, children=right_children),
                g,
            )
        else:
            lines = _render_both_sides(root, left_children, right_children, g)

    return "\n".join(lines)
