"""Ordered pipeline of text-level Markdown preprocessors, run before the body
reaches `rich.markdown.Markdown`.

Rich has no public extension point for custom Markdown syntax, so every viewmd
extension -- wikilinks, Mermaid diagrams, and any future one -- works by
rewriting the raw Markdown text first (see wikilinks.py and
mermaid/preprocess.py for the details of each). Add a new preprocessor by
appending it to PREPROCESSORS below; each runs in order, text in and text out.
"""

from __future__ import annotations

from collections.abc import Callable

from viewmd.mermaid.preprocess import render_mermaid_blocks
from viewmd.wikilinks import rewrite_wikilinks

Preprocessor = Callable[[str], str]

PREPROCESSORS: list[Preprocessor] = [
    rewrite_wikilinks,
    render_mermaid_blocks,
]


def preprocess(text: str) -> str:
    for step in PREPROCESSORS:
        text = step(text)
    return text
