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
