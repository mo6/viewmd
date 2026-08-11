"""Render Mermaid diagrams to ASCII/Unicode box-drawing art.

Sequence, flowchart, and entity-relationship diagrams are a from-scratch Python
port of github.com/AlexanderGrooff/mermaid-ascii (Go, MIT licensed; see
/THIRD_PARTY_NOTICES.md) -- ported rather than shelled out to, to avoid
bundling a per-platform compiled binary in a pure-Python CLI tool. Pie charts
(VIEWMD-0043) have no upstream reference to port from and are hand-written
directly against Mermaid's own syntax. Other Mermaid diagram types raise
`UnsupportedDiagramError`.
"""

from __future__ import annotations

from viewmd.mermaid.er.parser import ParseError as _ErParseError
from viewmd.mermaid.er.parser import parse as _parse_er
from viewmd.mermaid.er.parser import sniff as _is_er_diagram
from viewmd.mermaid.er.renderer import render as _render_er
from viewmd.mermaid.flowchart.parser import ParseError as _FlowchartParseError
from viewmd.mermaid.flowchart.parser import parse as _parse_flowchart
from viewmd.mermaid.flowchart.parser import sniff as _is_flowchart_diagram
from viewmd.mermaid.flowchart.renderer import render as _render_flowchart
from viewmd.mermaid.gitgraph.parser import ParseError as _GitgraphParseError
from viewmd.mermaid.gitgraph.parser import parse as _parse_gitgraph
from viewmd.mermaid.gitgraph.parser import sniff as _is_gitgraph_diagram
from viewmd.mermaid.gitgraph.renderer import render as _render_gitgraph
from viewmd.mermaid.kanban.parser import ParseError as _KanbanParseError
from viewmd.mermaid.kanban.parser import parse as _parse_kanban
from viewmd.mermaid.kanban.parser import sniff as _is_kanban_diagram
from viewmd.mermaid.kanban.renderer import render as _render_kanban
from viewmd.mermaid.packet.parser import ParseError as _PacketParseError
from viewmd.mermaid.packet.parser import parse as _parse_packet
from viewmd.mermaid.packet.parser import sniff as _is_packet_diagram
from viewmd.mermaid.packet.renderer import render as _render_packet
from viewmd.mermaid.pie.parser import ParseError as _PieParseError
from viewmd.mermaid.pie.parser import parse as _parse_pie
from viewmd.mermaid.pie.parser import sniff as _is_pie_diagram
from viewmd.mermaid.pie.renderer import render as _render_pie
from viewmd.mermaid.quadrant.parser import ParseError as _QuadrantParseError
from viewmd.mermaid.quadrant.parser import parse as _parse_quadrant
from viewmd.mermaid.quadrant.parser import sniff as _is_quadrant_diagram
from viewmd.mermaid.quadrant.renderer import render as _render_quadrant
from viewmd.mermaid.sequence.parser import ParseError as _SequenceParseError
from viewmd.mermaid.sequence.parser import parse as _parse_sequence
from viewmd.mermaid.sequence.parser import sniff as _is_sequence_diagram
from viewmd.mermaid.sequence.renderer import render as _render_sequence

__all__ = ["UnsupportedDiagramError", "MermaidError", "render"]


class MermaidError(Exception):
    """A Mermaid code block was recognized but could not be parsed or rendered."""


class UnsupportedDiagramError(MermaidError):
    """The Mermaid code block's diagram type isn't supported yet."""


def render(text: str, *, use_ascii: bool = False, color: bool = False,
           width: int | None = None) -> str:
    """Render Mermaid source `text` to a box-drawing ASCII/Unicode string.

    `color` and `width` (VIEWMD-0043) are currently read only by the pie and
    quadrant-chart renderers (VIEWMD-0047) -- every other diagram type
    ignores them, unaffected. `width` is the caller's resolved render width,
    not a hard cap (Mermaid diagrams are still allowed to render wider and
    scroll, VIEWMD-0018); it's what the pie chart's and quadrant chart's
    default sizing targets, so neither sizes itself independently of the
    document it's embedded in. Raises
    `UnsupportedDiagramError` if `text` isn't a diagram type this module
    supports, or `MermaidError` if it looks like a supported type but fails to
    parse.
    """
    if _is_sequence_diagram(text):
        try:
            diagram = _parse_sequence(text)
        except _SequenceParseError as e:
            raise MermaidError(str(e)) from e
        return _render_sequence(diagram, use_ascii=use_ascii)
    if _is_flowchart_diagram(text):
        try:
            properties = _parse_flowchart(text)
            return _render_flowchart(properties, use_ascii=use_ascii)
        except _FlowchartParseError as e:
            raise MermaidError(str(e)) from e
        except Exception as e:
            # The layout/routing engine is the most complex part of this port;
            # an internal failure on unusual input must still fall back to
            # showing the raw fence, never crash viewmd (VIEWMD-0015 req. 6).
            raise MermaidError(f"failed to render flowchart: {e}") from e
    if _is_er_diagram(text):
        try:
            diagram = _parse_er(text)
        except _ErParseError as e:
            raise MermaidError(str(e)) from e
        return _render_er(diagram, use_ascii=use_ascii)
    if _is_pie_diagram(text):
        try:
            chart = _parse_pie(text)
        except _PieParseError as e:
            raise MermaidError(str(e)) from e
        return _render_pie(chart, use_ascii=use_ascii, color=color, width=width)
    if _is_packet_diagram(text):
        try:
            diagram = _parse_packet(text)
        except _PacketParseError as e:
            raise MermaidError(str(e)) from e
        return _render_packet(diagram, use_ascii=use_ascii)
    if _is_quadrant_diagram(text):
        try:
            chart = _parse_quadrant(text)
        except _QuadrantParseError as e:
            raise MermaidError(str(e)) from e
        return _render_quadrant(chart, use_ascii=use_ascii, color=color, width=width)
    if _is_kanban_diagram(text):
        try:
            board = _parse_kanban(text)
        except _KanbanParseError as e:
            raise MermaidError(str(e)) from e
        return _render_kanban(board, use_ascii=use_ascii)
    if _is_gitgraph_diagram(text):
        try:
            graph = _parse_gitgraph(text)
        except _GitgraphParseError as e:
            raise MermaidError(str(e)) from e
        return _render_gitgraph(graph, use_ascii=use_ascii)
    raise UnsupportedDiagramError("not a recognized (or not yet supported) Mermaid diagram type")
