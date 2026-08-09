from viewmd.mermaid.preprocess import MERMAID_RENDERED_INFO, render_mermaid_blocks


def test_renders_a_sequence_diagram_fence_as_tagged_code():
    text = "before\n\n```mermaid\nsequenceDiagram\nA->>B: hi\n```\n\nafter\n"
    got = render_mermaid_blocks(text)
    assert "before" in got
    assert "after" in got
    assert "```mermaid\n" not in got
    assert f"```{MERMAID_RENDERED_INFO}\n" in got
    assert "┌───┐" in got


def test_unsupported_diagram_type_is_left_untouched():
    text = "```mermaid\nclassDiagram\n    Animal <|-- Duck\n```\n"
    assert render_mermaid_blocks(text) == text


def test_invalid_sequence_diagram_is_left_untouched():
    text = "```mermaid\nsequenceDiagram\nthis is not valid syntax !!\n```\n"
    assert render_mermaid_blocks(text) == text


def test_renders_a_flowchart_fence_as_tagged_code():
    text = "```mermaid\ngraph TD\n    A --> B\n```\n"
    got = render_mermaid_blocks(text)
    assert "```mermaid\n" not in got
    assert f"```{MERMAID_RENDERED_INFO}\n" in got
    assert "┌───┐" in got


def test_invalid_flowchart_is_left_untouched():
    text = "```mermaid\ngraph FOO\nA-->B\n```\n"
    assert render_mermaid_blocks(text) == text


def test_renders_an_er_diagram_fence_as_tagged_code():
    text = "```mermaid\nerDiagram\n    CUSTOMER ||--o{ ORDER : places\n```\n"
    got = render_mermaid_blocks(text)
    assert "```mermaid\n" not in got
    assert f"```{MERMAID_RENDERED_INFO}\n" in got
    assert "┌──────────┐" in got


def test_invalid_er_diagram_is_left_untouched():
    text = "```mermaid\nerDiagram\nthis is not valid syntax !!\n```\n"
    assert render_mermaid_blocks(text) == text


def test_unclosed_fence_is_left_untouched():
    text = "```mermaid\nsequenceDiagram\nA->>B: hi\n"
    assert render_mermaid_blocks(text) == text


def test_non_mermaid_fences_are_untouched():
    text = "```python\nprint('hi')\n```\n"
    assert render_mermaid_blocks(text) == text


def test_indented_fence_preserves_indentation():
    text = "- item\n  ```mermaid\n  sequenceDiagram\n  A->>B: hi\n  ```\n"
    got = render_mermaid_blocks(text)
    assert got.startswith(f"- item\n  ```{MERMAID_RENDERED_INFO}\n")
    assert got.rstrip("\n").endswith("```")


def test_tilde_fence_is_recognized():
    text = "~~~mermaid\nsequenceDiagram\nA->>B: hi\n~~~\n"
    got = render_mermaid_blocks(text)
    assert "~~~mermaid\n" not in got
    assert f"~~~{MERMAID_RENDERED_INFO}\n" in got
    assert "┌───┐" in got


def test_renders_a_pie_fence_as_bar_chart_by_default():
    # No `color=True` passed -- matches the default any caller gets.
    text = '```mermaid\npie\n    "A" : 1\n    "B" : 1\n```\n'
    got = render_mermaid_blocks(text)
    assert "```mermaid\n" not in got
    assert f"```{MERMAID_RENDERED_INFO}\n" in got
    assert "┃" in got  # bar-chart fallback glyph
    assert "\x1b[38;2;" not in got  # no circular-only truecolor escapes


def test_renders_a_pie_fence_as_circular_when_color_enabled():
    text = '```mermaid\npie\n    "A" : 1\n    "B" : 1\n```\n'
    got = render_mermaid_blocks(text, color=True)
    assert "```mermaid\n" not in got
    assert f"```{MERMAID_RENDERED_INFO}\n" in got
    assert "\x1b[38;2;" in got  # circular rendering's truecolor slice fill


def test_invalid_pie_diagram_is_left_untouched():
    text = '```mermaid\npie\n"bad"\n```\n'
    assert render_mermaid_blocks(text) == text
    assert render_mermaid_blocks(text, color=True) == text


def test_renders_a_packet_beta_fence_as_tagged_code():
    text = '```mermaid\npacket-beta\n0-15: "Source Port"\n16-31: "Destination Port"\n```\n'
    got = render_mermaid_blocks(text)
    assert "```mermaid\n" not in got
    assert f"```{MERMAID_RENDERED_INFO}\n" in got
    assert "╭" in got


def test_renders_a_bare_packet_fence_as_tagged_code():
    text = '```mermaid\npacket\n0-15: "Source Port"\n16-31: "Destination Port"\n```\n'
    got = render_mermaid_blocks(text)
    assert "```mermaid\n" not in got
    assert f"```{MERMAID_RENDERED_INFO}\n" in got
    assert "╭" in got


def test_invalid_packet_diagram_is_left_untouched():
    text = '```mermaid\npacket-beta\nnot a field line\n```\n'
    assert render_mermaid_blocks(text) == text
