"""Render Markdown text to an ANSI string using Rich."""

import io

from rich.console import Console
from rich.markdown import Markdown


def render_markdown(text: str, *, width: int, color: bool) -> str:
    """Render `text` to an ANSI string, `width` columns wide.

    Rendering is pure (writes to an in-memory buffer, never real stdout) so callers decide
    separately whether/how to display the result (see pager.py).
    """
    buffer = io.StringIO()
    console = Console(
        file=buffer,
        force_terminal=color,
        no_color=not color,
        color_system="truecolor" if color else None,
        width=width,
        highlight=False,
    )
    console.print(Markdown(text, code_theme="monokai"))
    return buffer.getvalue()
