"""Top-level flowchart render entry point, ported from cmd/draw.go's `drawMap`
and cmd/diagram.go's `GraphDiagram.Render`."""

from __future__ import annotations

from viewmd.mermaid.flowchart.graph import build
from viewmd.mermaid.flowchart.parser import GraphProperties, ParseError, parse, sniff
from viewmd.mermaid.grid.canvas import drawing_to_string

__all__ = ["ParseError", "sniff", "parse", "render"]


def render(properties: GraphProperties, *, use_ascii: bool = False) -> str:
    properties.use_ascii = use_ascii
    g = build(properties)
    return drawing_to_string(g.draw())
