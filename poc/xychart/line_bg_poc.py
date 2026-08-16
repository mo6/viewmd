#!/usr/bin/env python3
"""Proof of concept for VIEWMD-0066 (line-over-bar background fill in XY-chart combo charts).

Not part of the shipped `viewmd` package -- a throwaway script that renders the exact chart from
the issue's motivating report (`tools/demo-pages/16-xychart.md`'s "Sales vs Target" combo) two
ways, in real ANSI true-color, so the maintainer can see the actual difference in a terminal
rather than squinting at a substitute-glyph Markdown mockup (Markdown can't show real color, the
way ../../issues/archive/VIEWMD-0064-xychart-per-bar-color-and-spacing.md's own mockup had to use
`░`/`▒`/`▓`/`█` stand-ins for what were really four identical glyphs in four different hues).

"BEFORE" calls the real, currently-shipped `viewmd.mermaid.xychart.renderer.render` unmodified --
wherever the line dataset draws a cell, it fully replaces whatever the bar dataset drew there
(`_merge`), so a line segment crossing through a bar's height shows as a thin colored line on the
terminal's plain background, with no trace of the bar's own color behind it.

"AFTER" reimplements just enough of `render`'s tail (the per-row colorizing step) to additionally
wrap a line-glyph cell that has a bar underneath it in `wrap_text_styled(fg=line_color,
bg=bar_color)` instead of `wrap_text_in_color(line_color)` -- using the real `_build_bar_grid`/
`_build_line_grid`/`_plot_geometry`/`_bar_color`/`_LINE_COLOR` from the shipped renderer for every
number and glyph, so the only thing this script adds is the proposed background-fill rule itself.

    python3 poc/xychart/line_bg_poc.py

Run in a true-color terminal to see the difference; not wired into `./run-tests.sh` or
`./tools.sh` -- this is scratch tooling for authoring VIEWMD-0066, not a fixture generator.
"""

from __future__ import annotations

import pathlib
import re

from viewmd.mermaid.grid.canvas import wrap_text_in_color, wrap_text_styled
from viewmd.mermaid.xychart import parser
from viewmd.mermaid.xychart import renderer as R

DEMO_PAGE = pathlib.Path(__file__).resolve().parents[2] / "tools/demo-pages/16-xychart.md"


def _load_chart_src() -> str:
    """Pull the "Sales vs Target" ```mermaid fence straight out of the demo page, so this
    script can never drift from the chart the issue actually references."""
    text = DEMO_PAGE.read_text(encoding="utf-8")
    m = re.search(r"```mermaid\n(xychart-beta.*?)\n```", text, re.DOTALL)
    if not m:
        raise SystemExit(f"no xychart-beta fence found in {DEMO_PAGE}")
    return m.group(1)


def render_after(chart) -> str:
    """Same layout math as `renderer.render`, but a line-glyph cell that has a bar fill
    underneath gets `bg=` that bar's color instead of losing the bar's color outright.

    Only meaningful for a combo chart -- unlike `renderer.render`, this scratch script doesn't
    handle a bar-only or line-only `chart` (nothing to demonstrate there)."""
    if chart.bar is None or chart.line is None:
        raise SystemExit("line_bg_poc: only demonstrates a combo (bar + line) chart")
    g = R._UNICODE
    values = [*chart.bar, *chart.line]
    y_min, y_max = R._auto_range(values) if chart.y_min is None else (chart.y_min, chart.y_max)
    min_col = max(R._MIN_COL, max(R.string_width(c) for c in chart.categories) + 1)
    col_width, plot_w, target_rows = R._plot_geometry(len(chart.categories), min_col, 100)
    span = y_max - y_min
    step = R._nice_step(span / target_rows)
    n_rows = max(1, __import__("math").ceil(span / step - 1e-9))
    levels = [y_min + step * i for i in range(n_rows, 0, -1)]

    bar_grid = R._build_bar_grid(chart.bar, levels, step, col_width, use_ascii=False)
    line_grid = R._build_line_grid(chart.line, [*levels, y_min], step, col_width, g)

    bar_chars = R._bar_chars(g)
    line_chars = R._line_chars(g)

    decimals = R._tick_decimals(step)
    tick_labels = [R._format_tick(lv, decimals) for lv in levels]
    label_w = max(R.string_width(t) for t in (*tick_labels, R._format_tick(y_min, decimals)))

    lines = []
    total_w = label_w + 2 + plot_w
    lines.append(" " * max(0, (total_w - R.string_width(chart.title)) // 2) + chart.title)
    lines.append("")

    for lv, tick in zip(levels, tick_labels, strict=True):
        pad = " " * (label_w - R.string_width(tick))
        bar_row = bar_grid[lv]
        line_row = line_grid[lv]
        out = []
        for c in range(plot_w):
            bar_ch, line_ch = bar_row[c], line_row[c]
            cat_i = c // col_width
            if line_ch in line_chars:
                if bar_ch in bar_chars:
                    # The proposed rule: keep the line glyph on top, but fill the cell's
                    # background with the bar color it would otherwise have shown.
                    out.append(wrap_text_styled(line_ch, fg=R._LINE_COLOR,
                                                 bg=R._bar_color(cat_i)))
                else:
                    out.append(wrap_text_in_color(line_ch, R._LINE_COLOR))
            elif bar_ch in bar_chars:
                out.append(wrap_text_in_color(bar_ch, R._bar_color(cat_i)))
            else:
                out.append(" ")
        lines.append(f"{pad}{tick} {g.v}{''.join(out)}")

    axis_chars = list(g.bl + (g.tee_d + g.h * (col_width - 1)) * len(chart.categories))
    baseline = line_grid.get(y_min)
    if baseline is not None:
        for c, ch in enumerate(baseline):
            if ch != " ":
                axis_chars[c + 1] = ch
    lines.append(f"{' ' * label_w}{R._format_tick(y_min, decimals)} {''.join(axis_chars)}")

    label_line = " " * (label_w + 1)
    for cat in chart.categories:
        label_line += cat + " " * (col_width - R.string_width(cat))
    lines.append(label_line.rstrip())
    return "\n".join(lines)


def main() -> None:
    chart = parser.parse(_load_chart_src())

    print("BEFORE (shipped): line replaces the bar's color outright where it crosses one\n")
    print(R.render(chart, color=True, width=100))

    print("\nAFTER (VIEWMD-0066 proposal): line keeps the bar's color as its background\n")
    print(render_after(chart))


if __name__ == "__main__":
    main()
