"""Entity-relationship diagram renderer, ported from pkg/er/renderer.go."""

from __future__ import annotations

from viewmd.mermaid.er import charset
from viewmd.mermaid.er.charset import Glyphs
from viewmd.mermaid.er.layout import Canvas, draw_connectors, place_entities
from viewmd.mermaid.er.parser import Entity, ErDiagram
from viewmd.mermaid.textutil import width as string_width

__all__ = ["render"]


def _render_entity(e: Entity, g: Glyphs, min_inner: int) -> list[str]:
    """Draw an entity as an attribute table: a name header above a grid of the
    attribute rows. Columns (type, name, key, comment) are included only when
    at least one attribute uses them, and are padded to a common width.
    min_inner is a lower bound on the box's inner width, used to guarantee
    every relationship touching the box gets its own attach column."""
    # No attributes -> a plain named box (no column grid, no divider rule).
    # This is the most common ER form (e.g. `CUSTOMER ||--o{ ORDER`).
    if not e.attributes:
        inner = max(string_width(e.display) + 2, min_inner)
        pad = inner - string_width(e.display)
        return [
            g.tl + g.h * inner + g.tr,
            g.v + " " * (pad // 2) + e.display + " " * (pad - pad // 2) + g.v,
            g.bl + g.h * inner + g.br,
        ]

    # Column cells per attribute row: type, name, keys, comment.
    rows: list[tuple[str, str, str, str]] = []
    has = [True, True, False, False]  # type/name always shown
    for a in e.attributes:
        row = (a.type, a.name, ",".join(a.keys), a.comment)
        rows.append(row)
        if row[2]:
            has[2] = True
        if row[3]:
            has[3] = True

    # Which columns are shown, and each shown column's width.
    cols = [c for c in range(4) if has[c]]
    col_width: dict[int, int] = {}
    for c in cols:
        for r in rows:
            w = string_width(r[c])
            if w > col_width.get(c, 0):
                col_width[c] = w

    # Inner width = sum of padded cells (" cell ") + separators between columns.
    inner = 0
    for i, c in enumerate(cols):
        inner += col_width[c] + 2  # one space padding each side
        if i > 0:
            inner += 1  # column separator
    # The header (entity name) may be wider than the columns -- as may the
    # required minimum width; grow the last column so everything lines up.
    need = max(string_width(e.display) + 2, min_inner)
    if need > inner and cols:
        col_width[cols[-1]] += need - inner
        inner = need

    def pad(s: str, w: int) -> str:
        return " " + s + " " * (w - string_width(s)) + " "

    def rule(left: str, mid: str, right: str) -> str:
        parts = [left]
        for i, c in enumerate(cols):
            if i > 0:
                parts.append(mid)
            parts.append(g.h * (col_width[c] + 2))
        parts.append(right)
        return "".join(parts)

    out: list[str] = []
    # Top border + centred name header + separator with column tees.
    out.append(g.tl + g.h * inner + g.tr)
    name_pad = inner - string_width(e.display)
    out.append(g.v + " " * (name_pad // 2) + e.display + " " * (name_pad - name_pad // 2) + g.v)
    out.append(rule(g.tee_r, g.tee_d, g.tee_l))
    # Attribute rows.
    for r in rows:
        parts = [g.v]
        for i, c in enumerate(cols):
            if i > 0:
                parts.append(g.v)
            parts.append(pad(r[c], col_width[c]))
        parts.append(g.v)
        out.append("".join(parts))
    out.append(rule(g.bl, g.tee_u, g.br))
    return out


def render(d: ErDiagram, *, use_ascii: bool = False) -> str:
    """Lay out the entity tables in 2D and draw the relationships between
    them."""
    g = charset.ASCII if use_ascii else charset.UNICODE
    lay = place_entities(d, g, _render_entity)

    c = Canvas()
    for p in lay.placed:
        c.stamp(p.x, p.y, p.lines)
    draw_connectors(c, lay, d, g)
    return c.render()
