"""Render Mermaid diagrams to ASCII/Unicode box-drawing art.

A from-scratch Python port of github.com/AlexanderGrooff/mermaid-ascii (Go, MIT
licensed; see /THIRD_PARTY_NOTICES.md) -- ported rather than shelled out to, to
avoid bundling a per-platform compiled binary in a pure-Python CLI tool.
Sequence diagrams and flowcharts are supported; other Mermaid diagram types
raise `UnsupportedDiagramError`.
"""

from __future__ import annotations

from viewmd.mermaid.flowchart.parser import ParseError as _FlowchartParseError
from viewmd.mermaid.flowchart.parser import parse as _parse_flowchart
from viewmd.mermaid.flowchart.parser import sniff as _is_flowchart_diagram
from viewmd.mermaid.flowchart.renderer import render as _render_flowchart
from viewmd.mermaid.sequence.parser import ParseError as _SequenceParseError
from viewmd.mermaid.sequence.parser import parse as _parse_sequence
from viewmd.mermaid.sequence.parser import sniff as _is_sequence_diagram
from viewmd.mermaid.sequence.renderer import render as _render_sequence

__all__ = ["UnsupportedDiagramError", "MermaidError", "render"]


class MermaidError(Exception):
    """A Mermaid code block was recognized but could not be parsed or rendered."""


class UnsupportedDiagramError(MermaidError):
    """The Mermaid code block's diagram type isn't supported yet."""


def render(text: str, *, use_ascii: bool = False) -> str:
    """Render Mermaid source `text` to a box-drawing ASCII/Unicode string.

    Raises `UnsupportedDiagramError` if `text` isn't a diagram type this module
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
    raise UnsupportedDiagramError("not a recognized (or not yet supported) Mermaid diagram type")
