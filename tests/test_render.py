import re

from viewmd.render import render_divider, render_file_heading, render_markdown

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


def test_front_matter_renders_as_a_table_before_the_body():
    md = "---\ntitle: Hello\narea: [render, cli]\n---\n# Body heading\n\nbody text\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    assert "title" in out
    assert "Hello" in out
    assert "render, cli" in out
    assert "Body heading" in out
    assert "body text" in out
    # The table (and its divider) must come before the rendered body.
    assert out.index("Hello") < out.index("Body heading")


def test_file_without_front_matter_renders_unchanged():
    md = "# Just a heading\n\nsome text\n"
    with_check = render_markdown(md, width=80, color=False)
    assert with_check == render_markdown(md, width=80, color=False)
    assert "Just a heading" in strip_ansi(with_check)
    # No stray table artifacts (box-drawing characters) for a document with no front matter.
    assert "┌" not in with_check and "│" not in with_check


def test_unterminated_front_matter_block_renders_as_literal_body_text():
    md = "---\ntitle: Hello\n\n# Body\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    # No closing '---': not front matter, so 'title: Hello' shows up as ordinary body text,
    # not tabulated.
    assert "title: Hello" in out
    assert "Body" in out


def test_empty_front_matter_block_renders_only_the_body():
    md = "---\n---\n# Body\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    assert "Body" in out
    assert "┌" not in out


def test_empty_fields_are_omitted_from_the_table_by_default():
    md = "---\ntitle: Hello\naccepted_by:\nreason:\n---\n# Body\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    assert "title" in out
    assert "Hello" in out
    assert "accepted_by" not in out
    assert "reason" not in out


def test_full_front_matter_shows_empty_fields():
    md = "---\ntitle: Hello\naccepted_by:\nreason:\n---\n# Body\n"
    out = strip_ansi(render_markdown(md, width=80, color=False, full_front_matter=True))
    assert "title" in out
    assert "accepted_by" in out
    assert "reason" in out


def test_all_empty_fields_render_no_table_by_default_but_do_with_full_front_matter():
    md = "---\naccepted_by:\nreason:\n---\n# Body\n"
    default_out = strip_ansi(render_markdown(md, width=80, color=False))
    assert "┌" not in default_out
    assert "Body" in default_out

    full_out = strip_ansi(render_markdown(md, width=80, color=False, full_front_matter=True))
    assert "accepted_by" in full_out
    assert "reason" in full_out


# Rich's markdown.link_url style is underline + blue (SGR 4;34).
LINK_URL_ANSI = re.compile(r"\x1b\[4;34m")


def test_standard_markdown_link_uses_link_url_style():
    md = "see [hello](https://example.com) now"
    colored = render_markdown(md, width=80, color=True)
    plain = render_markdown(md, width=80, color=False)
    assert LINK_URL_ANSI.search(colored) is not None
    assert "hello" in strip_ansi(colored)
    assert ANSI_RE.search(plain) is None
    assert "hello" in plain


def test_converted_wikilink_uses_link_url_style():
    md = "see [[DELVE-0046]] and [[Target|Display text]] here"
    colored = render_markdown(md, width=80, color=True)
    plain = render_markdown(md, width=80, color=False)
    assert LINK_URL_ANSI.search(colored) is not None
    plain_text = strip_ansi(colored)
    assert "DELVE-0046" in plain_text
    assert "Display text" in plain_text
    assert "[[" not in plain_text
    assert "]]" not in plain_text
    assert ANSI_RE.search(plain) is None
    assert "DELVE-0046" in plain
    assert "Display text" in plain


def test_render_file_heading_shows_the_path():
    out = strip_ansi(render_file_heading("notes/one.md", width=80, color=False))
    assert "notes/one.md" in out


def test_render_file_heading_escapes_rich_markup_in_the_path():
    out = strip_ansi(render_file_heading("[weird].md", width=80, color=False))
    assert "[weird].md" in out


def test_render_divider_matches_the_front_matter_divider_style():
    md = "---\ntitle: Hello\n---\n# Body\n"
    front_matter_out = render_markdown(md, width=80, color=False)
    divider_out = render_divider(width=80, color=False)
    # Both use the same "═" double-line rule (VIEWMD-0004), reused here (VIEWMD-0013).
    assert "═" in front_matter_out
    assert divider_out.strip("\n") in front_matter_out


def test_long_code_block_line_is_truncated_not_wrapped():
    # VIEWMD-0019: a 120-char line at width 100 must stay one output line, hard-cropped.
    long_line = "x" * 120
    md = f"```\n{long_line}\n```\n"
    out = strip_ansi(render_markdown(md, width=100, color=False))
    content_lines = [line for line in out.splitlines() if line.strip()]
    assert len(content_lines) == 1, f"expected 1 content line, got {content_lines!r}"
    assert len(content_lines[0]) == 100
    assert content_lines[0] == "x" * 100
    assert "x" * 101 not in out


def test_wide_mermaid_diagram_keeps_natural_width():
    # VIEWMD-0018: each diagram row stays intact at the default width cap of 100.
    md = (
        "```mermaid\n"
        "sequenceDiagram\n"
        "    participant AAAAAAAAAA as First service with a long name\n"
        "    participant BBBBBBBBBB as Second service with a long name\n"
        "    participant CCCCCCCCCC as Third service with a long name\n"
        "    AAAAAAAAAA->>BBBBBBBBBB: do something\n"
        "    BBBBBBBBBB->>CCCCCCCCCC: forward it\n"
        "```\n"
    )
    out = strip_ansi(render_markdown(md, width=100, color=False))
    content_lines = [line for line in out.splitlines() if line.strip()]
    assert content_lines, "expected diagram output"
    assert any(len(line) > 100 for line in content_lines), (
        "expected at least one diagram row wider than 100, got lens="
        f"{[len(line) for line in content_lines]}"
    )
    # Actor labels must appear unbroken on a single row (not split across wrapped lines).
    intact = any(
        "First service with a long name" in line and "Third service with a long name" in line
        for line in content_lines
    )
    assert intact, f"expected all three actor labels on one intact row, got: {content_lines}"
    # No wrap-artifact: a line that is only the spilled tail of a label.
    assert not any(line.lstrip().startswith("with a long name") for line in content_lines)


def test_code_truncation_does_not_apply_to_mermaid_and_mermaid_bypass_does_not_widen_code():
    # Regression: the mermaid-rendered sentinel must discriminate the two paths.
    long_line = "y" * 120
    code_md = f"```\n{long_line}\n```\n"
    mermaid_md = (
        "```mermaid\n"
        "sequenceDiagram\n"
        "    participant AAAAAAAAAA as First service with a long name\n"
        "    participant BBBBBBBBBB as Second service with a long name\n"
        "    participant CCCCCCCCCC as Third service with a long name\n"
        "    AAAAAAAAAA->>BBBBBBBBBB: do something\n"
        "```\n"
    )
    code_out = strip_ansi(render_markdown(code_md, width=100, color=False))
    mermaid_out = strip_ansi(render_markdown(mermaid_md, width=100, color=False))

    code_lines = [line for line in code_out.splitlines() if line.strip()]
    assert len(code_lines) == 1
    assert len(code_lines[0]) == 100

    mermaid_lines = [line for line in mermaid_out.splitlines() if line.strip()]
    assert any(len(line) > 100 for line in mermaid_lines)
    assert "y" * 101 not in mermaid_out
