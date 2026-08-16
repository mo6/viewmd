import re

from viewmd.mermaid.preprocess import MERMAID_RENDERED_INFO
from viewmd.render import (
    render_directory_listing,
    render_divider,
    render_file_heading,
    render_markdown,
)

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


def test_converted_wikilink_with_space_in_target_still_renders_as_a_link():
    # A bare `(wikilink:Getting Started)` destination is invalid CommonMark (unescaped space),
    # so Rich would otherwise fall back to printing the raw "[text](url)" markdown untouched.
    md = "see [[Getting Started]] here"
    colored = render_markdown(md, width=80, color=True)
    plain_text = strip_ansi(colored)
    assert LINK_URL_ANSI.search(colored) is not None
    assert "Getting Started" in plain_text
    assert "[[" not in plain_text
    assert "](" not in plain_text


def test_render_file_heading_shows_the_path():
    out = strip_ansi(render_file_heading("notes/one.md", width=80, color=False))
    assert "notes/one.md" in out


def test_render_file_heading_escapes_rich_markup_in_the_path():
    out = strip_ansi(render_file_heading("[weird].md", width=80, color=False))
    assert "[weird].md" in out


def test_render_directory_listing_shows_title_and_type(tmp_path):
    (tmp_path / "a.md").write_text("---\ntitle: My Note\n---\n\nbody\n")
    (tmp_path / "sub").mkdir()

    out = strip_ansi(render_directory_listing(str(tmp_path), width=80, color=False))

    assert "a.md" in out
    assert "My Note" in out
    assert "sub" in out


def test_render_directory_listing_falls_back_to_heading_then_filename(tmp_path):
    (tmp_path / "heading-only.md").write_text("# Heading Title\n\nbody\n")
    (tmp_path / "plain.md").write_text("just a paragraph, no heading\n")

    out = strip_ansi(render_directory_listing(str(tmp_path), width=80, color=False))

    assert "Heading Title" in out
    assert "plain.md" in out


def test_render_directory_listing_excludes_non_markdown_files(tmp_path):
    (tmp_path / "notes.txt").write_text("not markdown\n")

    out = strip_ansi(render_directory_listing(str(tmp_path), width=80, color=False))

    assert "notes.txt" not in out


def test_render_directory_listing_escapes_rich_markup_in_names_and_titles(tmp_path, monkeypatch):
    import viewmd.render as render_module

    # Faked entries rather than real files/dirs on disk bearing "[...]" in their names: some
    # sandboxes deny filesystem writes whose path contains a literal "[...]" (glob-class
    # interposition on the allow-list), which is an artifact of the test's own execution
    # environment, unrelated to the escaping behavior under test.
    monkeypatch.setattr(render_module.os, "listdir",
                        lambda d: ["[red]evil[/red].md", "[bold]dir[/bold]"])
    monkeypatch.setattr(render_module.os.path, "isdir",
                        lambda p: p.endswith("[bold]dir[/bold]"))
    monkeypatch.setattr(render_module.os.path, "isfile",
                        lambda p: p.endswith("[red]evil[/red].md"))
    monkeypatch.setattr(render_module, "_markdown_title", lambda p: "[link=x]y[/link]")
    monkeypatch.setattr(render_module.os.path, "getmtime", lambda p: 0)

    out = render_directory_listing(str(tmp_path), width=80, color=False)

    assert "[red]evil[/red].md" in out
    assert "[link=x]y[/link]" in out
    assert "[bold]dir[/bold]" in out


def test_markdown_title_ignores_hash_comment_inside_a_code_fence(tmp_path):
    from viewmd.render import _markdown_title

    path = tmp_path / "note.md"
    path.write_text("```python\n# comment not a heading\n```\n\n# Real Heading\n")

    assert _markdown_title(str(path)) == "Real Heading"


def test_render_directory_listing_does_not_recurse(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.md").write_text("# Nested\n")

    out = strip_ansi(render_directory_listing(str(tmp_path), width=80, color=False))

    assert "nested.md" not in out


def test_render_divider_matches_the_front_matter_divider_style():
    md = "---\ntitle: Hello\n---\n# Body\n"
    front_matter_out = render_markdown(md, width=80, color=False)
    divider_out = render_divider(width=80, color=False)
    # Both use the same "═" double-line rule (VIEWMD-0004), reused here (VIEWMD-0013).
    assert "═" in front_matter_out
    assert divider_out.strip("\n") in front_matter_out


def test_long_code_block_line_is_not_truncated_or_wrapped():
    # VIEWMD-0019 (revised): a line longer than the render width stays intact on one output
    # line -- neither folded onto a second line nor cropped away -- so it scrolls horizontally
    # in the pager (less -S) rather than losing content, matching how mermaid art already
    # behaves (VIEWMD-0018).
    long_line = "x" * 120
    md = f"```\n{long_line}\n```\n"
    out = strip_ansi(render_markdown(md, width=100, color=False))
    content_lines = [line for line in out.splitlines() if line.strip()]
    assert len(content_lines) == 1, f"expected 1 content line, got {content_lines!r}"
    assert long_line in out


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


def test_mermaid_sentinel_still_discriminates_code_and_diagram_render_paths():
    # Regression: both an ordinary code fence and a mermaid fence now preserve full-width
    # content (neither truncates), but the mermaid-rendered sentinel must still route them
    # through different renderers -- Syntax (highlighted, padded) for code, raw Segments
    # (unhighlighted, unpadded) for diagram art -- rather than collapsing into one path.
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

    # Both preserve full content -- neither loses the wide content.
    assert long_line in code_out
    assert "First service with a long name" in mermaid_out
    assert "Third service with a long name" in mermaid_out

    # Code still gets Syntax's padding=1 (a blank line above/below); mermaid art doesn't.
    code_lines = code_out.splitlines()
    assert code_lines[0].strip() == "" and code_lines[-1].strip() == ""
    mermaid_lines = mermaid_out.splitlines()
    assert mermaid_lines[0].strip() != "" and mermaid_lines[-1].strip() != ""

    # The sentinel info-string itself never leaks into rendered output.
    assert MERMAID_RENDERED_INFO not in mermaid_out


def test_pie_chart_renders_circular_when_color_enabled_end_to_end():
    # VIEWMD-0043: color must reach Mermaid rendering itself, not just Rich's
    # own styling -- render_markdown(..., color=True) all the way through
    # preprocess() and render_mermaid_blocks() to the pie renderer.
    md = '```mermaid\npie\n    "A" : 1\n    "B" : 1\n```\n'
    out_color = render_markdown(md, width=80, color=True)
    out_nocolor = render_markdown(md, width=80, color=False)
    assert ANSI_RE.search(out_color) is not None
    assert ANSI_RE.search(out_nocolor) is None


def test_pie_chart_bar_fallback_has_zero_ansi_when_color_disabled():
    md = '```mermaid\npie title Split\n    "A" : 60\n    "B" : 40\n```\n'
    out = render_markdown(md, width=80, color=False)
    assert ANSI_RE.search(out) is None
    assert "┃" in out


def test_pie_chart_circular_size_respects_render_width():
    # Regression: the pie's default sizing used to query the raw terminal
    # size directly, ignoring --width entirely -- two renders at very
    # different widths came out byte-identical. `width` must reach the pie
    # renderer the same way `color` does.
    md = '```mermaid\npie title Pets\n    "Dogs" : 386\n    "Cats" : 85\n    "Rats" : 15\n```\n'
    narrow = strip_ansi(render_markdown(md, width=60, color=True))
    wide = strip_ansi(render_markdown(md, width=200, color=True))
    assert narrow != wide
    narrow_max = max(len(line) for line in narrow.splitlines())
    wide_max = max(len(line) for line in wide.splitlines())
    assert narrow_max < wide_max


def test_quadrant_chart_box_size_respects_render_width():
    # Same regression shape as the pie chart above (VIEWMD-0047 requirement
    # 7): `width` must reach the quadrant renderer, not a freshly-queried
    # raw terminal size.
    md = (
        '```mermaid\nquadrantChart\ntitle Campaigns\nx-axis Low --> High\n'
        'y-axis Low --> High\nA: [0.2, 0.8]\n```\n'
    )
    narrow = render_markdown(md, width=60, color=False)
    wide = render_markdown(md, width=200, color=False)
    assert narrow != wide
    narrow_max = max(len(line) for line in narrow.splitlines())
    wide_max = max(len(line) for line in wide.splitlines())
    assert narrow_max < wide_max


def test_quadrant_chart_is_colored_only_when_color_enabled():
    md = (
        '```mermaid\nquadrantChart\nx-axis Low --> High\ny-axis Low --> High\n'
        'quadrant-1 Q1\nquadrant-2 Q2\nquadrant-3 Q3\nquadrant-4 Q4\nA: [0.2, 0.8]\n```\n'
    )
    plain = render_markdown(md, width=80, color=False)
    colored = render_markdown(md, width=80, color=True)
    assert ANSI_RE.search(plain) is None
    assert ANSI_RE.search(colored) is not None
    assert strip_ansi(colored) == plain


def test_xychart_plot_size_respects_render_width():
    # Same plumbing regression as pie/quadrant (VIEWMD-0048 requirement 8):
    # `width` must reach the xychart renderer, not a freshly-queried raw
    # terminal size.
    md = (
        '```mermaid\nxychart-beta\n    title Sales\n    x-axis [Q1, Q2, Q3, Q4]\n'
        '    y-axis 0 --> 100\n    bar [40, 55, 70, 90]\n```\n'
    )
    narrow = render_markdown(md, width=40, color=False)
    wide = render_markdown(md, width=80, color=False)
    assert narrow != wide


# Rich's Style(dim=True, strike=True) is SGR 2 (dim) + 9 (strikethrough).
DIM_STRIKE_ANSI = re.compile(r"\x1b\[2;9m")

# Pre-VIEWMD-0058 output of a plain bullet list at width=80, color=False -- the
# task-list override must not change a non-task item's rendering at all.
PLAIN_BULLET_LIST_MD = "- item one\n- item two\n"
PLAIN_BULLET_LIST_NO_COLOR = (
    "\n • item one                                                                     \n"
    " • item two                                                                     \n"
)


def test_gfm_task_list_renders_checkbox_glyphs():
    md = "- [x] Write the draft\n- [x] Review it\n- [ ] Publish\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    assert out.count("✅") == 2
    assert out.count("⬜") == 1
    assert "[x]" not in out
    assert "[ ]" not in out
    assert "Write the draft" in out
    assert "Review it" in out
    assert "Publish" in out
    # `[X]` is the same checked marker as `[x]`.
    upper = strip_ansi(render_markdown("- [X] Upper\n", width=80, color=False))
    assert "✅" in upper
    assert "[X]" not in upper
    assert "Upper" in upper


def test_gfm_task_list_checked_items_are_dimmed_and_struck():
    md = "- [x] Write the draft\n- [x] Review it\n- [ ] Publish\n"
    plain = render_markdown(md, width=80, color=False)
    assert ANSI_RE.search(plain) is None
    out = render_markdown(md, width=80, color=True)
    checked = [
        line
        for line in out.splitlines()
        if "Write the draft" in strip_ansi(line) or "Review it" in strip_ansi(line)
    ]
    unchecked = [line for line in out.splitlines() if "Publish" in strip_ansi(line)]
    assert len(checked) == 2
    assert len(unchecked) == 1
    for line in checked:
        assert DIM_STRIKE_ANSI.search(line) is not None
    for line in unchecked:
        assert DIM_STRIKE_ANSI.search(line) is None
        assert "\x1b[9m" not in line
        assert "\x1b[2m" not in line


def test_plain_bullet_list_rendering_is_unchanged():
    out = render_markdown(PLAIN_BULLET_LIST_MD, width=80, color=False)
    assert out == PLAIN_BULLET_LIST_NO_COLOR


def test_gfm_task_list_unknown_marker_renders_as_plain_text():
    out = strip_ansi(render_markdown("- [y] not a task\n- [x]no-space\n", width=80, color=False))
    assert "•" in out
    assert "✅" not in out
    assert "⬜" not in out
    assert "[y] not a task" in out
    assert "[x]no-space" in out


def _rstripped(text: str) -> list[str]:
    return [line.rstrip() for line in text.splitlines()]


TOC_MD = "# Title\n\n## Section\n\n### Nested\n\nbody text\n"


def test_toc_renders_indented_h1_h2_h3_in_document_order():
    out = strip_ansi(render_markdown(TOC_MD, width=80, color=False))
    lines = _rstripped(out)
    assert lines[0] == "Title"
    assert lines[1] == "  Section"
    assert lines[2] == "    Nested"
    assert "body text" in out
    # Body h1 is centered; ToC h1 is flush left -- both texts appear.
    assert lines[0] == "Title"
    centered = [line for line in lines if line.strip() == "Title" and line != "Title"]
    assert centered, f"expected a centered body h1, got {lines!r}"


def test_toc_placed_after_front_matter_before_body():
    md = "---\ntitle: Hello\n---\n# Alpha\n\n## Beta\n\nbody text\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    lines = _rstripped(out)
    toc_at = lines.index("Alpha")
    before = lines[:toc_at]
    after = lines[toc_at + 2:]
    assert any("Hello" in line for line in before)
    assert any("═" in line for line in before)
    assert lines[toc_at + 1] == "  Beta"
    assert any("body text" in line for line in after)


def test_toc_omitted_for_a_single_heading():
    md = "# Only one\n\nbody\n"
    default = render_markdown(md, width=80, color=False)
    off = render_markdown(md, width=80, color=False, toc=False)
    assert default == off
    lines = [line for line in _rstripped(strip_ansi(default)) if line.strip()]
    # The only "Only one" is the centered body heading, not a flush-left ToC line.
    assert lines[0] != "Only one"
    assert "Only one" in lines[0]


def test_toc_omitted_for_no_headings():
    md = "just a paragraph\n"
    default = render_markdown(md, width=80, color=False)
    off = render_markdown(md, width=80, color=False, toc=False)
    assert default == off


def test_no_toc_leaves_the_body_unchanged():
    on = render_markdown(TOC_MD, width=80, color=False, toc=True)
    off = render_markdown(TOC_MD, width=80, color=False, toc=False)
    assert on.endswith(off)
    assert len(on) > len(off)
    assert _rstripped(strip_ansi(on))[0] == "Title"
    assert _rstripped(strip_ansi(off))[0] != "Title"


def test_h4_and_deeper_are_absent_from_toc_but_present_in_body():
    md = "# A\n\n## B\n\n#### Deep\n\n### C\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    lines = _rstripped(out)
    assert lines[0] == "A"
    assert lines[1] == "  B"
    assert lines[2] == "    C"
    assert "Deep" in out
    # "Deep" is not a ToC line (would be indented three steps if h4 were included).
    toc_block = lines[:3]
    assert not any("Deep" in line for line in toc_block)


def test_irregular_heading_nesting_is_rendered_as_it_appears():
    md = "### First h3\n\n# Later h1\n\n## Mid\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    lines = _rstripped(out)
    assert lines[0] == "    First h3"
    assert lines[1] == "Later h1"
    assert lines[2] == "  Mid"


def test_toc_entries_use_the_same_heading_styles_as_the_body():
    md = "# Hello\n\n## World\n\n### Nested\n"
    colored = render_markdown(md, width=80, color=True)
    lines = [line for line in colored.splitlines() if line.strip()]
    # ToC first, then body. Same SGR as the body's headings (bold+underline,
    # magenta+underline, magenta+bold -- Rich's markdown.h1/h2/h3).
    assert "\x1b[1;4mHello\x1b[0m" in lines[0]
    assert "\x1b[4;35mWorld\x1b[0m" in lines[1]
    assert "\x1b[1;35mNested\x1b[0m" in lines[2]
    body_h1 = [line for line in lines[3:] if "Hello" in strip_ansi(line)]
    body_h2 = [line for line in lines[3:] if "World" in strip_ansi(line)]
    body_h3 = [line for line in lines[3:] if "Nested" in strip_ansi(line)]
    assert body_h1 and "\x1b[1;4mHello\x1b[0m" in body_h1[0]
    assert body_h2 and "\x1b[4;35mWorld\x1b[0m" in body_h2[0]
    assert body_h3 and "\x1b[1;35mNested\x1b[0m" in body_h3[0]


def test_toc_uses_plain_text_of_inline_markup_in_headings():
    md = "# With **bold** and `code` and [link](http://x)\n\n## Second\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    lines = _rstripped(out)
    assert lines[0] == "With bold and code and link"
    assert lines[1] == "  Second"


def test_hash_comment_inside_a_fence_is_not_a_toc_entry():
    md = "```\n# not a heading\n```\n\n# Real\n\n## Also real\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    lines = _rstripped(out)
    assert lines[0] == "Real"
    assert lines[1] == "  Also real"
    assert not any(line.lstrip() == "not a heading" for line in lines[:4])


def _toc_prefix_lines(md: str) -> list[str]:
    """ToC lines only: the prefix of a toc=True render that is not in toc=False."""
    on = render_markdown(md, width=80, color=False, toc=True)
    off = render_markdown(md, width=80, color=False, toc=False)
    assert on.endswith(off)
    prefix = strip_ansi(on[: len(on) - len(off)])
    return [line for line in _rstripped(prefix) if line]


def _headings_md(entries: list[tuple[int, str]]) -> str:
    body = "\n\n".join("#" * level + " " + title for level, title in entries)
    return body + "\n\nbody text\n"


def test_toc_keeps_all_three_levels_at_exactly_20_entries():
    # 1 h1 + 1 h2 + 18 h3 = 20. The cap is "more than 20", so h3s stay.
    entries = [(1, "Top"), (2, "Mid")] + [(3, f"Leaf {i}") for i in range(18)]
    lines = _toc_prefix_lines(_headings_md(entries))
    assert len(lines) == 20
    assert lines[0] == "Top"
    assert lines[1] == "  Mid"
    assert lines[2] == "    Leaf 0"
    assert lines[-1] == "    Leaf 17"


def test_toc_drops_h3_when_h1_h2_h3_would_exceed_20_entries():
    # 2 h1 + 2 h2 + 17 h3 = 21. Dropping h3 leaves 4 entries.
    entries = [
        (1, "One"), (2, "One-a"), (3, "deep-a"),
        (1, "Two"), (2, "Two-a"),
    ] + [(3, f"Leaf {i}") for i in range(16)]
    lines = _toc_prefix_lines(_headings_md(entries))
    assert lines == ["One", "  One-a", "Two", "  Two-a"]
    assert not any("Leaf" in line or "deep-a" in line for line in lines)
    # Dropped headings still render in the body.
    body = strip_ansi(render_markdown(_headings_md(entries), width=80, color=False))
    assert "deep-a" in body
    assert "Leaf 0" in body


def test_toc_drops_h2_when_h1_h2_still_exceeds_20_entries():
    # 3 h1 + 18 h2 = 21. After dropping h3 (none), still 21, so drop to h1-only.
    entries = [(1, "A"), (2, "A-1")] + [(2, f"A-{i}") for i in range(2, 19)]
    entries += [(1, "B"), (1, "C")]
    lines = _toc_prefix_lines(_headings_md(entries))
    assert lines == ["A", "B", "C"]


def test_toc_keeps_every_h1_even_past_20_entries():
    entries = [(1, f"Chapter {i}") for i in range(21)]
    lines = _toc_prefix_lines(_headings_md(entries))
    assert lines == [f"Chapter {i}" for i in range(21)]
    assert len(lines) == 21


def test_toc_keeps_overflowing_h3s_when_there_is_no_shallower_outline():
    # 21 h3s, no h1/h2: dropping a level would empty the ToC, so keep the h3s.
    entries = [(3, f"Note {i}") for i in range(21)]
    lines = _toc_prefix_lines(_headings_md(entries))
    assert lines == [f"    Note {i}" for i in range(21)]
    assert len(lines) == 21


def test_toc_one_h1_after_depth_cap_is_still_rendered():
    # 1 h1 + 20 h3s = 21. Cap drops to h1-only. Requirement 7's "fewer than two"
    # check is against the extracted outline (21 headings), so the remaining
    # single h1 still prints as a one-line ToC.
    entries = [(1, "Only")] + [(3, f"Leaf {i}") for i in range(20)]
    lines = _toc_prefix_lines(_headings_md(entries))
    assert lines == ["Only"]
