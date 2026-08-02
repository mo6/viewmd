import re

from viewmd.render import render_markdown

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def test_header_renders_as_plain_text_without_markdown_syntax():
    out = render_markdown("# Hello there", width=80, color=False)
    assert "Hello there" in out
    assert "#" not in out


def test_header_is_colored_when_color_is_true():
    out = render_markdown("# Hello there", width=80, color=True)
    assert ANSI_RE.search(out) is not None


def test_no_color_output_has_no_ansi_escapes():
    out = render_markdown("# Hello\n\n**bold** and *italic*", width=80, color=False)
    assert ANSI_RE.search(out) is None


def test_table_renders_cell_contents():
    md = "| a | b |\n| - | - |\n| 1 | 2 |\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    assert "a" in out and "b" in out
    assert "1" in out and "2" in out


def test_code_block_with_language_is_colored():
    md = "```python\nprint('hi')\n```\n"
    colored = render_markdown(md, width=80, color=True)
    plain = render_markdown(md, width=80, color=False)
    assert ANSI_RE.search(colored) is not None
    assert ANSI_RE.search(plain) is None


def test_ascii_art_code_block_preserves_relative_spacing():
    art_lines = ["  /\\_/\\", " ( o.o )", "  > ^ <"]
    md = "```\n" + "\n".join(art_lines) + "\n```\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    rendered_lines = [line for line in out.splitlines() if line.strip()]
    for original in art_lines:
        stripped = original.rstrip()
        assert any(stripped in line for line in rendered_lines), (
            f"expected a rendered line containing {stripped!r}, got: {rendered_lines}"
        )


def test_blockquote_and_list_render_content():
    md = "> a quoted line\n\n- item one\n- item two\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    assert "a quoted line" in out
    assert "item one" in out
    assert "item two" in out
