"""2D character-grid canvas: box/line drawing, wide-character-aware text
placement, and junction-merging composition. Ported from cmd/draw.go.

`Drawing` mirrors the Go port's `[][]string` exactly, including its
column-major indexing (`d[x][y]`) -- kept as-is rather than transposed, so the
port stays a direct line-for-line translation.
"""

from __future__ import annotations

from dataclasses import dataclass

from wcwidth import wcwidth

from viewmd.mermaid.grid.coords import (
    DOWN,
    LEFT,
    LOWER_LEFT,
    LOWER_RIGHT,
    RIGHT,
    UP,
    UPPER_LEFT,
    UPPER_RIGHT,
    DrawingCoord,
    determine_direction,
)
from viewmd.mermaid.grid.label import LABEL_LINE_GAP, GraphLabel
from viewmd.mermaid.textutil import width as _string_width

Drawing = list[list[str]]

JUNCTION_CHARS = frozenset("─│┌┐└┘├┤┬┴┼╴╵╶╷")

_JUNCTION_MAP: dict[str, dict[str, str]] = {
    "─": {"│": "┼", "┌": "┬", "┐": "┬", "└": "┴", "┘": "┴", "├": "┼", "┤": "┼", "┬": "┬", "┴": "┴"},
    "│": {"─": "┼", "┌": "├", "┐": "┤", "└": "├", "┘": "┤", "├": "├", "┤": "┤", "┬": "┼", "┴": "┼"},
    "┌": {"─": "┬", "│": "├", "┐": "┬", "└": "├", "┘": "┼", "├": "├", "┤": "┼", "┬": "┬", "┴": "┼"},
    "┐": {"─": "┬", "│": "┤", "┌": "┬", "└": "┼", "┘": "┤", "├": "┼", "┤": "┤", "┬": "┬", "┴": "┼"},
    "└": {"─": "┴", "│": "├", "┌": "├", "┐": "┼", "┘": "┴", "├": "├", "┤": "┼", "┬": "┼", "┴": "┴"},
    "┘": {"─": "┴", "│": "┤", "┌": "┼", "┐": "┤", "└": "┴", "├": "┼", "┤": "┤", "┬": "┼", "┴": "┴"},
    "├": {"─": "┼", "│": "├", "┌": "├", "┐": "┼", "└": "├", "┘": "┼", "┤": "┼", "┬": "┼", "┴": "┼"},
    "┤": {"─": "┼", "│": "┤", "┌": "┼", "┐": "┤", "└": "┼", "┘": "┤", "├": "┼", "┬": "┼", "┴": "┼"},
    "┬": {"─": "┬", "│": "┼", "┌": "┬", "┐": "┬", "└": "┼", "┘": "┼", "├": "┼", "┤": "┼", "┴": "┼"},
    "┴": {"─": "┴", "│": "┼", "┌": "┼", "┐": "┼", "└": "┴", "┘": "┴", "├": "┼", "┤": "┼", "┬": "┼"},
}


def _rune_width(ch: str) -> int:
    w = wcwidth(ch)
    return w if w and w > 0 else 1


def ceil_div(x: int, y: int) -> int:
    return x // y if x % y == 0 else x // y + 1


def mk_drawing(x: int, y: int) -> Drawing:
    return [[" "] * (y + 1) for _ in range(x + 1)]


def get_drawing_size(d: Drawing) -> tuple[int, int]:
    return len(d) - 1, len(d[0]) - 1


def copy_canvas(d: Drawing) -> Drawing:
    x, y = get_drawing_size(d)
    return mk_drawing(x, y)


def increase_size(d: Drawing, x: int, y: int) -> Drawing:
    cur_x, cur_y = get_drawing_size(d)
    new_d = mk_drawing(max(x, cur_x), max(y, cur_y))
    for i in range(len(d)):
        for j in range(len(d[0])):
            new_d[i][j] = d[i][j]
    return new_d


def draw_text(d: Drawing, start: DrawingCoord, text: str) -> Drawing:
    text_width = _string_width(text)
    d = increase_size(d, start.x + text_width, start.y)
    text_x = start.x
    for ch in text:
        rune_w = _rune_width(ch)
        d[text_x][start.y] = ch
        for offset in range(1, rune_w):
            d[text_x + offset][start.y] = ""
        text_x += rune_w
    return d


def draw_text_on_line(d: Drawing, line: list[DrawingCoord], label: str) -> Drawing:
    min_x, max_x = sorted((line[0].x, line[1].x))
    min_y, max_y = sorted((line[0].y, line[1].y))
    middle_x = min_x + (max_x - min_x) // 2
    middle_y = min_y + (max_y - min_y) // 2
    label_len = len(label.encode("utf-8"))
    start = DrawingCoord(middle_x - label_len // 2, middle_y)
    return draw_text(d, start, label)


_UNICODE_LINE_CHARS = {
    UP: "│",
    DOWN: "│",
    LEFT: "─",
    RIGHT: "─",
    UPPER_LEFT: "╲",
    LOWER_RIGHT: "╲",
    UPPER_RIGHT: "╱",
    LOWER_LEFT: "╱",
}
_ASCII_LINE_CHARS = {
    UP: "|",
    DOWN: "|",
    LEFT: "-",
    RIGHT: "-",
    UPPER_LEFT: "\\",
    LOWER_RIGHT: "\\",
    UPPER_RIGHT: "/",
    LOWER_LEFT: "/",
}


def draw_line(
    d: Drawing,
    from_: DrawingCoord,
    to: DrawingCoord,
    offset_from: int,
    offset_to: int,
    use_ascii: bool,
) -> list[DrawingCoord]:
    direction = determine_direction(from_, to)
    char = (_ASCII_LINE_CHARS if use_ascii else _UNICODE_LINE_CHARS).get(direction)
    drawn: list[DrawingCoord] = []
    if char is None:
        return drawn

    if direction == UP:
        for y in range(from_.y - offset_from, to.y - offset_to - 1, -1):
            drawn.append(DrawingCoord(from_.x, y))
            d[from_.x][y] = char
    elif direction == DOWN:
        for y in range(from_.y + offset_from, to.y + offset_to + 1):
            drawn.append(DrawingCoord(from_.x, y))
            d[from_.x][y] = char
    elif direction == LEFT:
        for x in range(from_.x - offset_from, to.x - offset_to - 1, -1):
            drawn.append(DrawingCoord(x, from_.y))
            d[x][from_.y] = char
    elif direction == RIGHT:
        for x in range(from_.x + offset_from, to.x + offset_to + 1):
            drawn.append(DrawingCoord(x, from_.y))
            d[x][from_.y] = char
    elif direction == UPPER_LEFT:
        x, y = from_.x, from_.y - offset_from
        while x >= to.x - offset_to and y >= to.y - offset_to:
            drawn.append(DrawingCoord(x, y))
            d[x][y] = char
            x, y = x - 1, y - 1
    elif direction == UPPER_RIGHT:
        x, y = from_.x, from_.y - offset_from
        while x <= to.x + offset_to and y >= to.y - offset_to:
            drawn.append(DrawingCoord(x, y))
            d[x][y] = char
            x, y = x + 1, y - 1
    elif direction == LOWER_LEFT:
        x, y = from_.x, from_.y + offset_from
        while x >= to.x - offset_to and y <= to.y + offset_to:
            drawn.append(DrawingCoord(x, y))
            d[x][y] = char
            x, y = x - 1, y + 1
    elif direction == LOWER_RIGHT:
        x, y = from_.x, from_.y + offset_from
        while x <= to.x + offset_to and y <= to.y + offset_to:
            drawn.append(DrawingCoord(x, y))
            d[x][y] = char
            x, y = x + 1, y + 1

    return drawn


def merge_junctions(c1: str, c2: str) -> str:
    return _JUNCTION_MAP.get(c1, {}).get(c2, c1)


def is_junction_char(c: str) -> bool:
    return c in JUNCTION_CHARS


def merge_drawings(
    base: Drawing, merge_coord: DrawingCoord, *drawings: Drawing, use_ascii: bool
) -> Drawing:
    max_x, max_y = get_drawing_size(base)
    for d in drawings:
        dx, dy = get_drawing_size(d)
        max_x = max(max_x, dx + merge_coord.x)
        max_y = max(max_y, dy + merge_coord.y)

    merged = mk_drawing(max_x, max_y)
    base_x, base_y = len(base), len(base[0])
    for x in range(max_x + 1):
        for y in range(max_y + 1):
            if x < base_x and y < base_y:
                merged[x][y] = base[x][y]

    for d in drawings:
        for x in range(len(d)):
            for y in range(len(d[0])):
                c = d[x][y]
                if c == " ":
                    continue
                mx, my = x + merge_coord.x, y + merge_coord.y
                current = merged[mx][my]
                if not use_ascii and is_junction_char(c) and is_junction_char(current):
                    merged[mx][my] = merge_junctions(current, c)
                else:
                    merged[mx][my] = c

    return merged


def drawing_to_string(d: Drawing) -> str:
    max_x, max_y = get_drawing_size(d)
    lines = []
    for y in range(max_y + 1):
        lines.append("".join(d[x][y] for x in range(max_x + 1)))
    return "\n".join(lines)


def _parse_hex(color_hex: str) -> tuple[int, int, int] | None:
    hex_ = color_hex.lstrip("#")
    if len(hex_) == 3:
        hex_ = "".join(ch * 2 for ch in hex_)
    if len(hex_) != 6:
        return None
    try:
        return int(hex_[0:2], 16), int(hex_[2:4], 16), int(hex_[4:6], 16)
    except ValueError:
        return None


def wrap_text_in_color(text: str, color_hex: str) -> str:
    """CLI-only (viewmd has no HTML render mode): true-colour ANSI wrap,
    matching gookit/color's `HEX(c).Sprint(text)`."""
    if not color_hex:
        return text
    rgb = _parse_hex(color_hex)
    if rgb is None:
        return text
    r, g, b = rgb
    return f"\x1b[38;2;{r};{g};{b}m{text}\x1b[0m"


def wrap_text_bold(text: str) -> str:
    """Raw ANSI bold wrap, sibling to wrap_text_in_color -- same
    embed-the-escape-in-plain-text approach (VIEWMD-0043), a text-weight
    attribute rather than a color."""
    if not text:
        return text
    return f"\x1b[1m{text}\x1b[0m"


def wrap_text_italic(text: str) -> str:
    """Raw ANSI italic wrap (SGR 3), sibling to wrap_text_bold -- a text-style
    attribute rather than a color (VIEWMD-0045 mindmap markdown labels)."""
    if not text:
        return text
    return f"\x1b[3m{text}\x1b[0m"


def apply_color_spans(chars: list[str], spans: list[tuple[int, int, str]]) -> str:
    """Wrap non-overlapping `(start, end_exclusive, color_hex)` column ranges
    of a plain single-char-per-index row in true-colour ANSI, post-hoc. For a
    renderer (gitGraph, VIEWMD-0042) that builds a plain character grid first
    -- for layout logic (column placement, junction-merging) that needs every
    cell to stay a single plain character -- then colorizes specific ranges
    only after that grid is final, rather than embedding escape codes during
    placement itself. (`viewmd/mermaid/gantt/renderer.py`'s own
    `_colorize_spans`, VIEWMD-0032, is the same idea, written before this one
    existed to share -- a candidate to fold together in a later cleanup.)"""
    if not spans:
        return "".join(chars)
    out: list[str] = []
    pos = 0
    for start, end, hex_ in sorted(spans):
        if start > pos:
            out.append("".join(chars[pos:start]))
        out.append(wrap_text_in_color("".join(chars[max(start, pos):end]), hex_))
        pos = max(pos, end)
    out.append("".join(chars[pos:]))
    return "".join(out)


def wrap_text_styled(text: str, *, fg: str | None = None, bg: str | None = None,
                      bold: bool = False, italic: bool = False,
                      underline: bool = False) -> str:
    """Combined true-colour fg/bg + bold/italic/underline ANSI wrap in a single
    escape/reset pair (VIEWMD-0047, `underline` added by VIEWMD-0034, `italic`
    by VIEWMD-0045) -- sibling to wrap_text_in_color/wrap_text_bold/
    wrap_text_italic, for a caller (the quadrant chart's per-quadrant
    background fill; the kanban board's underlined `ticket` field; mindmap
    markdown `***bold italic***` spans) that needs more than one SGR attribute
    on the same span. Nesting the existing wrappers instead would still work
    (SGR codes accumulate additively until a `0` reset), just with a redundant
    extra reset per nesting level."""
    if not text:
        return text
    codes = []
    if bold:
        codes.append("1")
    if italic:
        codes.append("3")
    if underline:
        codes.append("4")
    if fg:
        rgb = _parse_hex(fg)
        if rgb:
            codes.append(f"38;2;{rgb[0]};{rgb[1]};{rgb[2]}")
    if bg:
        rgb = _parse_hex(bg)
        if rgb:
            codes.append(f"48;2;{rgb[0]};{rgb[1]};{rgb[2]}")
    if not codes:
        return text
    return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"


def draw_box(
    width: int,
    height: int,
    label: GraphLabel,
    color_hex: str,
    use_ascii: bool,
    shape: str = "rectangle",
) -> Drawing:
    """Box is always 3x3 on the grid; `width`/`height` are the caller's
    pixel-space column/row-width sums for that node's two content columns/rows
    (ported from cmd/draw.go's `drawBox`). Shape glyphs beyond the rectangle
    baseline are VIEWMD-0022. A diamond (VIEWMD-0038) is drawn by this same
    uniform-border-box mechanism as every other shape -- it is no longer a
    true tapered rhombus -- with a single `◇`-style marker glyph placed in
    the middle of an otherwise flat top/bottom border.

    `shape` is a `NodeShape` value string (`"rectangle"`, `"round"`, …) kept as
    plain `str` here so `grid` does not import the flowchart package.
    """
    if shape in ("parallelogram", "parallelogram_alt"):
        return _draw_parallelogram(
            width, height, label, color_hex, use_ascii, mirrored=shape == "parallelogram_alt"
        )

    from_ = DrawingCoord(0, 0)
    to = DrawingCoord(width, height)
    d = mk_drawing(max(from_.x, to.x), max(from_.y, to.y))

    glyphs = _box_glyphs(shape, use_ascii)
    bw = border_width(shape)
    for x in range(from_.x + 1, to.x):
        d[x][from_.y] = glyphs.h_top
        d[x][to.y] = glyphs.h_bot
    for y in range(from_.y + 1, to.y):
        for lx in range(from_.x, min(from_.x + bw, to.x + 1)):
            d[lx][y] = glyphs.v_left
        for rx in range(max(to.x - bw + 1, from_.x), to.x + 1):
            d[rx][y] = glyphs.v_right
    d[from_.x][from_.y] = glyphs.tl
    d[to.x][from_.y] = glyphs.tr
    d[from_.x][to.y] = glyphs.bl
    d[to.x][to.y] = glyphs.br

    if shape == "diamond":
        # Centre marker must land on the exact UP/DOWN attachment-cell
        # centre (`graph._grid_to_drawing_coord`'s middle-column formula),
        # which this mirrors -- see VIEWMD-0038 design notes.
        center_x = 1 + (width - 1) // 2
        if from_.x < center_x < to.x:
            d[center_x][from_.y] = glyphs.v_left
            d[center_x][to.y] = glyphs.v_right

    line_gap = 0 if shape == "diamond" else LABEL_LINE_GAP
    _place_label(d, from_, width, height, label, color_hex, line_gap=line_gap)
    return d


def _draw_parallelogram(
    width: int,
    height: int,
    label: GraphLabel,
    color_hex: str,
    use_ascii: bool,
    mirrored: bool,
) -> Drawing:
    """`[/Text/]` (VIEWMD-0039): unlike every other shape, each row is offset
    one column from the row above it -- `mirrored=False` (`/`) shifts left
    going down, `mirrored=True` (`\\`) shifts right going down, per the
    requester's own worked example. `width`/`height` follow `draw_box`'s
    usual convention (same caller, same node-box-size formula), but with the
    per-row shift budget (`height` extra columns, VIEWMD-0039 req. 6)
    already folded into `width` by `graph._set_column_width`'s extra column
    reservation for these two shapes -- `nominal_width` below recovers the
    real (unshifted) per-row span by subtracting that budget back out.
    """
    d = mk_drawing(max(width, 0), max(height, 0))
    if width <= 0 or height <= 0:
        return d

    nominal_width = width - height
    glyph = "\\" if mirrored else "/"
    h_char = "-" if use_ascii else "─"

    def shift(y: int) -> int:
        return y if mirrored else height - y

    for y in range(height + 1):
        left = shift(y)
        right = left + nominal_width
        d[left][y] = glyph
        d[right][y] = glyph
        if y == 0 or y == height:
            for x in range(left + 1, right):
                d[x][y] = h_char

    content_top = 1
    for line_idx, line in enumerate(label.lines):
        text_y = content_top + line_idx * (LABEL_LINE_GAP + 1)
        if text_y >= height:
            break
        text_width = _string_width(line)
        text_x = shift(text_y) + nominal_width // 2 - ceil_div(text_width, 2) + 1
        for ch in line:
            rune_w = _rune_width(ch)
            if 0 <= text_x <= width and 0 <= text_y <= height:
                d[text_x][text_y] = wrap_text_in_color(ch, color_hex)
                for offset in range(1, rune_w):
                    if text_x + offset <= width:
                        d[text_x + offset][text_y] = ""
            text_x += rune_w
    return d


def border_width(shape: str) -> int:
    """Left/right border strip width, in pixel-columns. Only `subroutine`
    doubles its side bars (VIEWMD-0038 req. 4, keeping the existing 1-space
    label padding column intact rather than reusing it) -- every other shape
    keeps the single-pixel border strip every shape has always used."""
    return 2 if shape == "subroutine" else 1


@dataclass(frozen=True)
class _BoxGlyphs:
    tl: str
    tr: str
    bl: str
    br: str
    h_top: str
    h_bot: str
    v_left: str
    v_right: str


def _box_glyphs(shape: str, use_ascii: bool) -> _BoxGlyphs:
    """Per-shape border glyphs from the VIEWMD-0022 proposal (subroutine/
    cylinder/diamond glyphs updated by VIEWMD-0038). ASCII mode keeps the
    baseline `+`/`-`/`|` set for every shape except diamond, whose four
    attachment-marker sides need an ASCII-safe substitute for `◇`
    (VIEWMD-0038 req. 9) -- distinguishable unicode is otherwise a
    unicode-mode-only concern."""
    if shape == "diamond":
        marker = "*" if use_ascii else "◇"
        corner = "+" if use_ascii else None
        h = "-" if use_ascii else "─"
        if use_ascii:
            return _BoxGlyphs(corner, corner, corner, corner, h, h, marker, marker)
        return _BoxGlyphs("╭", "╮", "╰", "╯", h, h, marker, marker)

    if use_ascii:
        return _BoxGlyphs("+", "+", "+", "+", "-", "-", "|", "|")

    if shape == "round":
        return _BoxGlyphs("╭", "╮", "╰", "╯", "─", "─", "│", "│")
    if shape == "stadium":
        return _BoxGlyphs("(", ")", "(", ")", "─", "─", "(", ")")
    if shape == "circle":
        return _BoxGlyphs("╔", "╗", "╚", "╝", "═", "═", "║", "║")
    if shape == "subroutine":
        return _BoxGlyphs("┌", "┐", "└", "┘", "─", "─", "│", "│")
    if shape == "cylinder":
        return _BoxGlyphs("╭", "╮", "╰", "╯", "═", "─", "│", "│")
    # RECTANGLE and any unknown fall through to the VIEWMD-0015 baseline.
    return _BoxGlyphs("┌", "┐", "└", "┘", "─", "─", "│", "│")


def _place_label(
    d: Drawing,
    from_: DrawingCoord,
    width: int,
    height: int,
    label: GraphLabel,
    color_hex: str,
    *,
    center_bias: int = 1,
    line_gap: int = LABEL_LINE_GAP,
) -> None:
    inner_top = from_.y + 1
    inner_height = height - 1
    content_height = len(label.lines) + (len(label.lines) - 1) * line_gap if label.lines else 0
    content_top = inner_top + (inner_height - content_height) // 2
    for line_idx, line in enumerate(label.lines):
        text_y = content_top + line_idx * (line_gap + 1)
        text_width = _string_width(line)
        text_x = from_.x + width // 2 - ceil_div(text_width, 2) + center_bias
        for ch in line:
            rune_w = _rune_width(ch)
            if 0 <= text_x <= width and 0 <= text_y <= height:
                d[text_x][text_y] = wrap_text_in_color(ch, color_hex)
                for offset in range(1, rune_w):
                    if text_x + offset <= width:
                        d[text_x + offset][text_y] = ""
            text_x += rune_w


def draw_subgraph(width: int, height: int, use_ascii: bool) -> Drawing:
    if width <= 0 or height <= 0:
        return mk_drawing(0, 0)
    from_ = DrawingCoord(0, 0)
    to = DrawingCoord(width, height)
    d = mk_drawing(width, height)

    h_char, v_char = ("-", "|") if use_ascii else ("─", "│")
    for x in range(from_.x + 1, to.x):
        d[x][from_.y] = h_char
        d[x][to.y] = h_char
    for y in range(from_.y + 1, to.y):
        d[from_.x][y] = v_char
        d[to.x][y] = v_char
    corner = "+" if use_ascii else None
    if use_ascii:
        d[from_.x][from_.y] = d[to.x][from_.y] = d[from_.x][to.y] = d[to.x][to.y] = corner
    else:
        d[from_.x][from_.y] = "┌"
        d[to.x][from_.y] = "┐"
        d[from_.x][to.y] = "└"
        d[to.x][to.y] = "┘"
    return d


def draw_subgraph_label(width: int, height: int, label: GraphLabel) -> Drawing:
    if width <= 0 or height <= 0:
        return mk_drawing(0, 0)
    d = mk_drawing(width, height)
    for line_idx, line in enumerate(label.lines):
        label_y = 1 + line_idx * (LABEL_LINE_GAP + 1)
        label_x = width // 2 - _string_width(line) // 2
        if label_x < 1:
            label_x = 1
        for ch in line:
            rune_w = _rune_width(ch)
            if label_x < width:
                d[label_x][label_y] = ch
            offset = 1
            while offset < rune_w and label_x + offset < width:
                d[label_x + offset][label_y] = ""
                offset += 1
            label_x += rune_w
    return d
