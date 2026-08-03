from viewmd.mermaid.preprocess import render_mermaid_blocks
from viewmd.preprocessors import PREPROCESSORS, preprocess
from viewmd.wikilinks import rewrite_wikilinks


def test_registry_contains_the_built_in_preprocessors_in_order():
    assert PREPROCESSORS == [rewrite_wikilinks, render_mermaid_blocks]


def test_preprocess_runs_every_registered_step():
    text = "See [[Home]].\n\n```mermaid\nsequenceDiagram\nA->>B: hi\n```\n"
    got = preprocess(text)
    assert "[Home](wikilink:Home)" in got
    assert "```mermaid" not in got
    assert "│" in got
