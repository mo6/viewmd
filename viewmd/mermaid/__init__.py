"""Render Mermaid diagrams to ASCII/Unicode box-drawing art.

A from-scratch Python port of github.com/AlexanderGrooff/mermaid-ascii (Go, MIT
licensed; see /THIRD_PARTY_NOTICES.md) -- ported rather than shelled out to, to
avoid bundling a per-platform compiled binary in a pure-Python CLI tool. Only
sequence diagrams are supported so far; other Mermaid diagram types raise
`UnsupportedDiagramError`.
"""

from __future__ import annotations

from viewmd.mermaid.sequence.parser import ParseError
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
        except ParseError as e:
            raise MermaidError(str(e)) from e
        return _render_sequence(diagram, use_ascii=use_ascii)
    raise UnsupportedDiagramError("not a recognized (or not yet supported) Mermaid diagram type")
