"""ER-diagram canvas, box placement, and connector routing, ported from
pkg/er/layout.go. Self-contained (VIEWMD-0016 req. 6): pkg/er/layout.go
implements its own canvas/routing rather than reusing the flowchart engine's
grid, so this port does the same instead of depending on `viewmd.mermaid.grid`."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto

from wcwidth import wcwidth

from viewmd.mermaid.er.charset import Glyphs
from viewmd.mermaid.er.parser import Cardinality, Entity, ErDiagram, Relationship
from viewmd.mermaid.textutil import width as string_width


def _rune_width(ch: str) -> int:
    w = wcwidth(ch)
    return w if w and w > 0 else 1


class Canvas:
    """A growable 2D grid of characters that boxes are stamped onto and
    connectors are drawn across."""

    def __init__(self) -> None:
        self.rows: list[list[str]] = []

    def _ensure(self, x: int, y: int) -> None:
        while len(self.rows) <= y:
            self.rows.append([])
        row = self.rows[y]
        while len(row) <= x:
            row.append(" ")

    def set(self, x: int, y: int, ch: str) -> None:
        if x < 0 or y < 0:
            return
        self._ensure(x, y)
        self.rows[y][x] = ch

    def at(self, x: int, y: int) -> str:
        if y < 0 or y >= len(self.rows) or x < 0 or x >= len(self.rows[y]):
            return " "
        return self.rows[y][x]

    def stamp(self, x0: int, y0: int, block: list[str]) -> None:
        """Place a block of pre-rendered lines with its top-left at (x0,y0).
        Characters advance by display width: a double-width character (CJK,
        emoji) occupies its cell plus a sentinel cell, keeping canvas columns
        aligned with what the terminal shows."""
        for dy, line in enumerate(block):
            x = x0
            for ch in line:
                self.set(x, y0 + dy, ch)
                w = _rune_width(ch)
                if w == 2:
                    self.set(x + 1, y0 + dy, "\0")
                x += w

    def render(self) -> str:
        out_lines = []
        for row in self.rows:
            line = "".join(ch for ch in row if ch != "\0")
            out_lines.append(line.rstrip(" "))
        return "\n".join(out_lines) + "\n"


class Side(Enum):
    TOP = auto()
    BOTTOM = auto()


@dataclass(eq=False)
class PlacedEntity:
    entity: Entity
    lines: list[str]
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    row: int = 0
    col: int = 0


@dataclass
class Layout:
    by_name: dict[str, PlacedEntity]
    placed: list[PlacedEntity]
    lanes: int
    gut_w: int
    v_gut_x: list[int]
    h_gut_y: list[int]

    def gutter_y(self, e: Endpoint, lane: int) -> int:
        """The horizontal gutter row an endpoint's stub reaches: the gutter
        below the box for bottom exits, above for top exits, offset by the
        relationship's own lane so distinct relationships never share a row."""
        if e.side is Side.BOTTOM:
            return self.h_gut_y[e.p.row + 1] + lane
        return self.h_gut_y[e.p.row] + lane

    def trunk_x(self, a: PlacedEntity, b: PlacedEntity, lane: int) -> int:
        """The vertical lane column a relationship travels along when its two
        gutter rows differ. All trunks form one family: the box-free gutter
        just right of the leftmost box's column, in the gutter's rightmost
        `lanes` band. That leaves the leftmost box's horizontal run at least a
        full label wide, and -- lanes being globally unique -- no two trunks
        ever share a column."""
        return self.v_gut_x[min(a.col, b.col) + 1] + self.gut_w - self.lanes + lane


def _block_width(lines: list[str]) -> int:
    w = 0
    for line in lines:
        lw = string_width(line)
        if lw > w:
            w = lw
    return w


def place_entities(d: ErDiagram, g: Glyphs, render_entity) -> Layout:
    """Render every entity and arrange the boxes in a near-square grid
    separated by lane-wide gutters."""
    n = len(d.entities)
    cols = math.ceil(math.sqrt(n)) if n else 1
    if cols < 1:
        cols = 1
    rows = (n + cols - 1) // cols

    lanes = len(d.relationships)
    if lanes < 1:
        lanes = 1

    # Vertical gutters hold one trunk lane per relationship AND must leave the
    # widest label room on a horizontal run. A relationship's longer run always
    # spans at least gutW-lane cells, so budgeting lanes+label keeps every
    # label whole whichever lane it lands in.
    max_label = 0
    for r in d.relationships:
        w = string_width(r.label)
        if w > max_label:
            max_label = w
    gut_w = lanes + max_label + 5

    # Boxes must be wide enough that every relationship touching them gets its
    # own attach column with clearance for a 2-cell crow's-foot token beside it
    # (attach spaces slots 4 apart). Self-loops additionally need both their
    # tokens on one row, and clearance from any other connector on the face.
    deg: dict[str, int] = {}
    self_loop: dict[str, bool] = {}
    for r in d.relationships:
        deg[r.left] = deg.get(r.left, 0) + 1
        deg[r.right] = deg.get(r.right, 0) + 1
        if r.left == r.right:
            self_loop[r.left] = True

    placed: list[PlacedEntity] = [None] * n  # type: ignore[list-item]
    for i, e in enumerate(d.entities):
        min_w = 4 * deg.get(e.name, 0) + 1
        if self_loop.get(e.name):
            min_w = 11
            if deg.get(e.name, 0) > 2:
                min_w = 4 * deg[e.name] + 9
        lines = render_entity(e, g, min_w - 2)
        placed[i] = PlacedEntity(
            entity=e, lines=lines, w=_block_width(lines), h=len(lines),
            row=i // cols, col=i % cols,
        )

    # Per-column width and per-row height.
    col_w = [0] * cols
    row_h = [0] * rows
    for p in placed:
        if p.w > col_w[p.col]:
            col_w[p.col] = p.w
        if p.h > row_h[p.row]:
            row_h[p.row] = p.h

    # X layout: [col0][gutter][col1]...[gutter]. No gutter left of column 0 --
    # trunks only ever run between columns or off the right edge.
    v_gut_x = [0] * (cols + 1)
    col_x = [0] * cols
    x = 0
    for c in range(cols):
        v_gut_x[c] = x
        if c > 0:
            x += gut_w
            col_x[c] = x
        else:
            col_x[0] = 0
        x += col_w[c]
    v_gut_x[cols] = x

    # Y layout: [row0][gutter][row1]...[gutter]. No gutter above row 0 --
    # nothing ever exits upward from the top row, so it would only be blank
    # space.
    h_gut_y = [0] * (rows + 1)
    row_y = [0] * rows
    y = 0
    for r in range(rows):
        h_gut_y[r] = y
        if r > 0:
            y += lanes
            row_y[r] = y
        else:
            row_y[0] = 0
        y += row_h[r]
    h_gut_y[rows] = y

    by_name: dict[str, PlacedEntity] = {}
    for p in placed:
        p.x, p.y = col_x[p.col], row_y[p.row]
        by_name[p.entity.name] = p
    return Layout(
        by_name=by_name, placed=placed, lanes=lanes, gut_w=gut_w, v_gut_x=v_gut_x, h_gut_y=h_gut_y,
    )


# ---- connector routing -------------------------------------------------------

# dir bits mark which neighbours a connector cell links to; the glyph for a
# cell is chosen from the union of its bits (so crossings become +, corners...).
D_N = 1
D_S = 2
D_E = 4
D_W = 8


@dataclass
class Overlay:
    """Accumulates connector line bits per cell (kept off the box canvas so
    junction glyphs can be computed once at the end). solid vs dashed is
    tracked separately so an identifying line stays solid where it doesn't
    cross a dashed one."""

    solid: dict[tuple[int, int], int] = field(default_factory=dict)
    dash: dict[tuple[int, int], int] = field(default_factory=dict)
    label: dict[tuple[int, int], str] = field(default_factory=dict)
    token: dict[tuple[int, int], str] = field(default_factory=dict)

    def bits(self, x: int, y: int) -> int:
        return self.solid.get((x, y), 0) | self.dash.get((x, y), 0)

    def polyline(self, pts: list[tuple[int, int]], solid: bool) -> None:
        """Set connector bits along an axis-aligned poly-line through pts."""
        m = self.solid if solid else self.dash
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            dx, dy = _sign(bx - ax), _sign(by - ay)
            x, y = ax, ay
            while x != bx or y != by:
                # outgoing link on the cell we leave -- never on the segment's
                # end, or corners would grow phantom arms and render as tees.
                bit = 0
                if dx > 0:
                    bit |= D_E
                elif dx < 0:
                    bit |= D_W
                if dy > 0:
                    bit |= D_S
                elif dy < 0:
                    bit |= D_N
                m[(x, y)] = m.get((x, y), 0) | bit
                x += dx
                y += dy
                # incoming link on the cell we enter
                bit = 0
                if dx > 0:
                    bit |= D_W
                elif dx < 0:
                    bit |= D_E
                if dy > 0:
                    bit |= D_N
                elif dy < 0:
                    bit |= D_S
                m[(x, y)] = m.get((x, y), 0) | bit


def _sign(n: int) -> int:
    if n > 0:
        return 1
    if n < 0:
        return -1
    return 0


def attach(p: PlacedEntity, s: Side, idx: int, total: int) -> tuple[int, int]:
    """Choose connection points along a box's top or bottom face: slots 4
    cells apart (a stub, its 2-cell crow's-foot token, and clearance), the
    group centred on the face -- place_entities sizes boxes so it always fits.
    Every slot is snapped to a per-face parity, bottom faces even columns and
    top faces odd, so stubs from boxes stacked in the same grid column can
    never share a canvas column and visually fuse into one line."""
    lo, hi = p.x + 1, p.x + p.w - 2
    x = lo + (hi - lo - 4 * (total - 1)) // 2 + 4 * idx
    if (s is Side.BOTTOM) == (x % 2 != 0):
        x += 1
    x = max(lo, min(x, hi))
    y = p.y + p.h - 1  # sideB
    if s is Side.TOP:
        y = p.y
    return x, y


@dataclass
class Endpoint:
    """A resolved connection: box side + on-canvas attach coordinate."""

    p: PlacedEntity
    side: Side
    x: int = 0
    y: int = 0
    card: Cardinality = Cardinality.ONLY_ONE


def sides_for(a: PlacedEntity, b: PlacedEntity) -> tuple[Side, Side]:
    """Pick each box's exit face. Connectors leave through the top/bottom
    faces so every relationship rides a horizontal gutter row -- the only
    rows where labels are guaranteed collision-free (each relationship owns a
    global lane). Boxes exit toward each other, with one exception:
    vertically-adjacent boxes in the same column would meet in their shared
    gutter as a straight vertical line with no horizontal run to carry tokens
    or a label, so the lower box exits bottom too and the path wraps round
    through the side gutter."""
    same_col_adjacent = a.col == b.col and abs(a.row - b.row) == 1
    if a.row < b.row:
        if same_col_adjacent:
            return Side.BOTTOM, Side.BOTTOM
        return Side.BOTTOM, Side.TOP
    if a.row > b.row:
        if same_col_adjacent:
            return Side.BOTTOM, Side.BOTTOM
        return Side.TOP, Side.BOTTOM
    return Side.BOTTOM, Side.BOTTOM  # same row (incl. self-relationships)


@dataclass
class RoutePlan:
    """One relationship's resolved geometry. Each endpoint drops (or rises)
    vertically from its box into a horizontal gutter row; if both stubs reach
    the same row the run merges into one straight span, otherwise a vertical
    trunk in a side gutter joins the two rows:

        {a.x,a.y} {a.x,ya} {tx,ya} {tx,yb} {b.x,yb} {b.x,b.y}
    """

    rel: Relationship
    a: Endpoint
    b: Endpoint
    ya: int
    yb: int
    tx: int = 0  # trunk column, valid only when not merged
    merged: bool = False  # both stubs meet one gutter row: single run, no trunk

    @staticmethod
    def new(lay: Layout, a: Endpoint, b: Endpoint, r: Relationship, lane: int) -> RoutePlan:
        ya, yb = lay.gutter_y(a, lane), lay.gutter_y(b, lane)
        p = RoutePlan(rel=r, a=a, b=b, ya=ya, yb=yb, merged=ya == yb)
        if not p.merged:
            p.tx = lay.trunk_x(a.p, b.p, lane)
        return p

    def draw_line(self, o: Overlay) -> None:
        """Draw the relationship's orthogonal line in its own lane, so
        distinct edges never overlap -- only genuine crossings share a cell."""
        if self.merged:
            o.polyline([
                (self.a.x, self.a.y), (self.a.x, self.ya),
                (self.b.x, self.ya), (self.b.x, self.b.y),
            ], self.rel.identifying)
            return
        o.polyline([
            (self.a.x, self.a.y), (self.a.x, self.ya), (self.tx, self.ya),
            (self.tx, self.yb), (self.b.x, self.yb), (self.b.x, self.b.y),
        ], self.rel.identifying)

    def decorate(self, o: Overlay) -> None:
        """Stamp the crow's-foot tokens and the label. Runs after every line
        is drawn so the label can dodge cells other relationships pass
        through."""
        if self.merged:
            _put_token(o, self.a, self.b.x, self.ya)
            _put_token(o, self.b, self.a.x, self.ya)
            if self.a.p is self.b.p:  # self-loop: the run is at most the box's
                # width, so the label sits beside the loop instead of inside it
                _write_label(o, self.rel.label, max(self.a.x, self.b.x) + 2, self.ya, -1)
            else:
                run = (min(self.a.x, self.b.x), max(self.a.x, self.b.x), self.ya)
                _put_label(o, self.rel.label, [run])
            return
        _put_token(o, self.a, self.tx, self.ya)
        _put_token(o, self.b, self.tx, self.yb)
        runs = [
            (min(self.a.x, self.tx), max(self.a.x, self.tx), self.ya),
            (min(self.b.x, self.tx), max(self.b.x, self.tx), self.yb),
        ]
        if runs[1][1] - runs[1][0] > runs[0][1] - runs[0][0]:
            runs[0], runs[1] = runs[1], runs[0]  # longest run first
        _put_label(o, self.rel.label, runs)


def _put_token(o: Overlay, ep: Endpoint, target_x: int, y: int) -> None:
    """Stamp a two-cell crow's-foot marker on the gutter row, next to the
    corner where the endpoint's stub turns toward target_x. Orientation is
    pure geometry: whichever way the run leaves the stub, the marker's foot
    character stays adjacent to the box and the pair reads left-to-right."""
    if ep.x < target_x:  # run leaves rightward
        for i, r in enumerate(_left_token(ep.card)):
            o.token[(ep.x + 1 + i, y)] = r
        return
    tok = _right_token(ep.card)
    for i, r in enumerate(tok):
        o.token[(ep.x - len(tok) + i, y)] = r


def _put_label(o: Overlay, s: str, runs: list[tuple[int, int, int]]) -> None:
    """Place a label on one of the candidate runs (each (x0,x1,y)), clipped 3
    cells at each end to clear the corner and crow's-foot token. Candidates
    arrive longest-first; the first run offering the label a spot clear of
    crossing lines wins, then the first it merely fits on."""
    if s == "":
        return
    lw = string_width(s)
    best_start = 0
    best_cost = -1
    best_y = 0
    best_hi = 0
    for x0, x1, y in runs:
        lo, hi = x0 + 3, x1 - 3
        if hi - lo + 1 < lw:
            continue
        start, cost = _label_start(o, lo, hi, lw, y)
        if best_cost < 0 or cost < best_cost:
            best_start, best_cost, best_y, best_hi = start, cost, y, hi
        if cost == 0:
            break
    if best_cost < 0:  # fits nowhere whole: clip on the longest run
        x0, x1, y = runs[0]
        lo, hi = x0 + 3, x1 - 3
        if lo > hi:
            return
        start, _cost = _label_start(o, lo, hi, lw, y)
        best_start, best_y, best_hi = start, y, hi
    _write_label(o, s, best_start, best_y, best_hi)


def _label_start(o: Overlay, lo: int, hi: int, lw: int, y: int) -> tuple[int, int]:
    """Pick where the label begins on [lo,hi]: centred, sliding outwards to
    the nearest spot crossing the fewest vertical lines. Returns the start and
    how many crossings the label will sit on (0 is a clean spot)."""
    centre = max(lo, lo + (hi - lo + 1 - lw) // 2)
    start, cost = centre, _v_crossings(o, centre, min(centre + lw - 1, hi), y)
    d = 1
    while d <= hi - lo and cost > 0:
        for c in (centre - d, centre + d):
            if c < lo or c + lw - 1 > hi:
                continue
            n = _v_crossings(o, c, c + lw - 1, y)
            if n < cost:
                start, cost = c, n
        d += 1
    return start, cost


def _v_crossings(o: Overlay, x0: int, x1: int, y: int) -> int:
    """Count cells in [x0,x1] at row y carrying a vertical line (a crossing
    another relationship's trunk or stub makes through here)."""
    n = 0
    for x in range(x0, x1 + 1):
        if o.bits(x, y) & (D_N | D_S) != 0:
            n += 1
    return n


def _write_label(o: Overlay, s: str, x: int, y: int, limit: int) -> None:
    """Write label characters from x, advancing by display width (reserving a
    sentinel cell after each double-width character so columns stay aligned).
    A limit >= 0 clips the label; -1 writes it whole. A space character over a
    crossing vertical line is not stamped, so word gaps never punch holes in
    other lines."""
    for c in s:
        w = _rune_width(c)
        if limit >= 0 and x + w - 1 > limit:
            return
        if c != " " or o.bits(x, y) & (D_N | D_S) == 0:
            o.label[(x, y)] = c
            if w == 2:
                o.label[(x + 1, y)] = "\0"
        x += w


def composite(c: Canvas, o: Overlay, g: Glyphs) -> None:
    """Render the overlay onto the canvas: line junctions first (only on blank
    cells so boxes stay intact), then labels and crow's-foot tokens on top."""
    seen: set[tuple[int, int]] = set()

    def mark(x: int, y: int) -> None:
        p = (x, y)
        if p in seen:
            return
        seen.add(p)
        bits = o.bits(x, y)
        if bits == 0:
            return
        if c.at(x, y) != " ":
            return  # don't scribble over a box
        c.set(x, y, _glyph_for(bits, o.solid.get(p, 0) != 0, g))

    for p in o.solid:
        mark(*p)
    for p in o.dash:
        mark(*p)
    for p, r in o.label.items():
        c.set(p[0], p[1], r)
    for p, r in o.token.items():
        c.set(p[0], p[1], r)


def _glyph_for(bits: int, solid: bool, g: Glyphs) -> str:
    """Map a set of direction bits to a box-drawing character."""
    if bits == D_N | D_S:
        return g.v if solid else g.vd
    if bits == D_E | D_W:
        return g.h if solid else g.hd
    if bits == D_N | D_E:
        return g.bl
    if bits == D_N | D_W:
        return g.br
    if bits == D_S | D_E:
        return g.tl
    if bits == D_S | D_W:
        return g.tr
    if bits == D_N | D_S | D_E:
        return g.tee_r
    if bits == D_N | D_S | D_W:
        return g.tee_l
    if bits == D_N | D_E | D_W:
        return g.tee_u
    if bits == D_S | D_E | D_W:
        return g.tee_d
    if bits == D_N | D_S | D_E | D_W:
        return g.cross
    if bits in (D_N, D_S):
        return g.v if solid else g.vd
    return g.h if solid else g.hd  # dE, dW, 0


def _left_token(c: Cardinality) -> str:
    """Crow's-foot cardinality markers, read toward the box."""
    if c is Cardinality.ONLY_ONE:
        return "||"
    if c is Cardinality.ZERO_OR_ONE:
        return "|o"
    if c is Cardinality.ZERO_OR_MORE:
        return "}o"
    return "}|"


def _right_token(c: Cardinality) -> str:
    if c is Cardinality.ONLY_ONE:
        return "||"
    if c is Cardinality.ZERO_OR_ONE:
        return "o|"
    if c is Cardinality.ZERO_OR_MORE:
        return "o{"
    return "|{"


def draw_connectors(c: Canvas, lay: Layout, d: ErDiagram, g: Glyphs) -> None:
    """Route every relationship and write the result onto c."""
    o = Overlay()

    # Decide each endpoint's side, then hand out attach slots per box-side so
    # multiple connectors on one face fan out instead of overlapping.
    ent_idx = {p: i for i, p in enumerate(lay.placed)}
    all_ends: list[tuple[Endpoint, Endpoint] | None] = [None] * len(d.relationships)
    slot_count: dict[tuple[int, int], int] = {}
    for i, r in enumerate(d.relationships):
        a, b = lay.by_name.get(r.left), lay.by_name.get(r.right)
        if a is None or b is None:
            continue
        sa, sb = sides_for(a, b)
        all_ends[i] = (
            Endpoint(p=a, side=sa, card=r.left_card), Endpoint(p=b, side=sb, card=r.right_card),
        )
        slot_count[(ent_idx[a], sa.value)] = slot_count.get((ent_idx[a], sa.value), 0) + 1
        slot_count[(ent_idx[b], sb.value)] = slot_count.get((ent_idx[b], sb.value), 0) + 1

    slot_used: dict[tuple[int, int], int] = {}
    self_seen: dict[int, int] = {}
    for i in range(len(all_ends)):
        pair = all_ends[i]
        if pair is None:
            continue
        ea, eb = pair
        for ep in (ea, eb):
            key = (ent_idx[ep.p], ep.side.value)
            ep.x, ep.y = attach(ep.p, ep.side, slot_used.get(key, 0), slot_count[key])
            slot_used[key] = slot_used.get(key, 0) + 1
        # A self-loop's two stubs share one face; evenly-spaced slots sit too
        # close together for the crow's-foot tokens, so spread them to the
        # ends (snapped to the bottom face's even-column parity). Each further
        # self-loop on the same entity nests one slot-pitch inside the last,
        # so no two loops ever share an attach column.
        if ea.p is eb.p:
            p = ea.p
            pidx = ent_idx[p]
            in_ = 4 * self_seen.get(pidx, 0)
            self_seen[pidx] = self_seen.get(pidx, 0) + 1
            x1, x2 = p.x + 1 + in_, p.x + p.w - 2 - in_
            if x1 % 2 != 0:
                x1 += 1
            if x2 % 2 != 0:
                x2 -= 1
            ea.x, eb.x = x1, x2

    plans: list[RoutePlan] = []
    for i, r in enumerate(d.relationships):
        pair = all_ends[i]
        if pair is None:
            continue
        plans.append(RoutePlan.new(lay, pair[0], pair[1], r, i))

    # Lines first, decorations second: label placement inspects the finished
    # line overlay so labels can dodge cells other relationships pass through.
    for p in plans:
        p.draw_line(o)
    for p in plans:
        p.decorate(o)

    composite(c, o, g)

    # Mark each attach point on the box border with a tee so the stub visibly
    # joins the box (composite itself never draws over box cells).
    for p in plans:
        _set_attach_tee(c, p.a, g)
        _set_attach_tee(c, p.b, g)


def _set_attach_tee(c: Canvas, ep: Endpoint, g: Glyphs) -> None:
    """Stamp tee-down/tee-up where a stub leaves a box; if the border cell
    already tees the other way (an attribute-table column rule), the two merge
    into a cross."""
    tee, opposite = g.tee_d, g.tee_u
    if ep.side is Side.TOP:
        tee, opposite = g.tee_u, g.tee_d
    if c.at(ep.x, ep.y) == opposite:
        tee = g.cross
    c.set(ep.x, ep.y, tee)
