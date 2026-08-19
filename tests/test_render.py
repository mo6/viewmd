import re

from viewmd.mermaid.preprocess import MERMAID_RENDERED_INFO
from viewmd.render import (
    render_directory_listing,
    render_divider,
    render_file_heading,
    render_front_matter_block,
    render_markdown,
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m|\x1b\]8;[^\x1b]*\x1b\\")


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


def test_front_matter_block_matches_render_markdown_prefix():
    md = "---\ntitle: Hello\narea: [pager]\n---\n# Body heading\n\nbody text\n"
    block = render_front_matter_block(md, width=80, color=False)
    full = render_markdown(md, width=80, color=False, toc=False)
    assert block
    assert full.startswith(block)
    assert "═" in block
    assert "Body heading" not in block


def test_front_matter_block_empty_when_no_table_would_render():
    assert render_front_matter_block("# Body\n", width=80, color=False) == ""
    assert render_front_matter_block("---\n---\n# Body\n", width=80, color=False) == ""
    assert render_front_matter_block("---\ntitle: Hello\n# Body\n", width=80, color=False) == ""
    assert render_front_matter_block(
        "---\naccepted_by:\n---\n# Body\n", width=80, color=False
    ) == ""


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


def test_render_directory_listing_links_subdirectory_rows(tmp_path):
    (tmp_path / "sub dir").mkdir()
    (tmp_path / "a.md").write_text("# A\n")

    colored = render_directory_listing(str(tmp_path), width=80, color=True)

    assert "viewmd-dir:sub%20dir" in colored
    # A subdirectory row's href is scheme-tagged (`_DIR_ANCHOR_SCHEME`, resolved by
    # `_resolve_dir_target`); an `.md` file row's own href (VIEWMD-0093) is a plain relative path
    # with no such prefix (resolved by `_resolve_link_target` instead), so it never matches this
    # scheme-qualified string.
    assert "viewmd-dir:a.md" not in colored


def test_render_directory_listing_no_dir_link_without_color(tmp_path):
    (tmp_path / "sub").mkdir()

    out = render_directory_listing(str(tmp_path), width=80, color=False)

    assert "viewmd-dir:" not in out
    assert "sub" in out


def test_render_directory_listing_links_md_file_rows(tmp_path):
    # VIEWMD-0093: a `.md` file row now carries a clickable target too, a plain (percent-encoded)
    # relative path -- not the `_DIR_ANCHOR_SCHEME`-tagged form subdirectory rows use, since it
    # needs to resolve through `_resolve_link_target` like an ordinary in-document link.
    (tmp_path / "a file.md").write_text("# A\n")

    colored = render_directory_listing(str(tmp_path), width=80, color=True)

    assert "a%20file.md" in colored
    assert "viewmd-dir:a%20file.md" not in colored


def test_render_directory_listing_no_file_link_without_color(tmp_path):
    (tmp_path / "a.md").write_text("# A\n")

    out = render_directory_listing(str(tmp_path), width=80, color=False)

    assert "\x1b]8;" not in out
    assert "a.md" in out


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


def _toc_line(level: int, text: str) -> str:
    """ToC row matching Rich's bullet-list marker and 3-column nest (VIEWMD-0068)."""
    return " " * (3 * (level - 1)) + " • " + text


def _toc_more(omitted: int) -> str:
    return f"... {omitted} more"


def _toc_entries(md: str) -> list[str]:
    """ToC lines: non-empty rstripped lines in toc=True that are not in toc=False, in order."""
    on_out = strip_ansi(render_markdown(md, width=80, color=False, toc=True))
    off_out = strip_ansi(render_markdown(md, width=80, color=False, toc=False))
    on = [line for line in _rstripped(on_out) if line]
    off = [line for line in _rstripped(off_out) if line]
    extra = []
    j = 0
    for line in on:
        if j < len(off) and line == off[j]:
            j += 1
        else:
            extra.append(line)
    return extra


def _headings_md(entries: list[tuple[int, str]]) -> str:
    body = "\n\n".join("#" * level + " " + title for level, title in entries)
    return body + "\n\nbody text\n"


def _is_centered(line: str, text: str) -> bool:
    return line.strip() == text and line != text


def test_toc_renders_under_the_leading_h1_without_repeating_it():
    out = strip_ansi(render_markdown(TOC_MD, width=80, color=False))
    lines = _rstripped(out)
    nonempty = [line for line in lines if line]
    assert _is_centered(nonempty[0], "Title")
    assert nonempty[1] == _toc_line(2, "Section")
    assert nonempty[2] == _toc_line(3, "Nested")
    # Title is not a flush-left ToC line, and is not repeated as a second centered heading.
    assert "Title" not in [line for line in nonempty[1:] if line.strip() == "Title"]
    assert "body text" in out
    toc = _toc_entries(TOC_MD)
    assert toc == [_toc_line(2, "Section"), _toc_line(3, "Nested")]


def test_toc_placed_after_front_matter_and_title_before_rest_of_body():
    md = "---\ntitle: Hello\n---\n# Alpha\n\n## Beta\n\nbody text\n"
    out = strip_ansi(render_markdown(md, width=80, color=False))
    lines = [line for line in _rstripped(out) if line]
    hello_at = next(i for i, line in enumerate(lines) if "Hello" in line)
    divider_at = next(i for i, line in enumerate(lines) if "═" in line)
    title_at = next(i for i, line in enumerate(lines) if _is_centered(line, "Alpha"))
    toc_at = lines.index(_toc_line(2, "Beta"))
    body_at = next(i for i, line in enumerate(lines) if "body text" in line)
    assert hello_at < divider_at < title_at < toc_at < body_at
    # Alpha is the title, not a ToC row; ToC starts on the next nonempty line.
    assert "Alpha" not in lines[:title_at]
    assert toc_at == title_at + 1
    assert lines[toc_at] == _toc_line(2, "Beta")


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
    off = render_markdown(TOC_MD, width=80, color=False, toc=False)
    on = render_markdown(TOC_MD, width=80, color=False, toc=True)
    assert _toc_entries(TOC_MD) == [_toc_line(2, "Section"), _toc_line(3, "Nested")]
    assert "Section" in strip_ansi(off)
    assert strip_ansi(off).count("Title") >= 1
    # --no-toc is the body-only render; with-toc is longer because of the outline.
    assert len(on) > len(off)


def test_h4_and_deeper_are_absent_from_toc_but_present_in_body():
    md = "# A\n\n## B\n\n#### Deep\n\n### C\n"
    toc = _toc_entries(md)
    assert toc == [_toc_line(2, "B"), _toc_line(3, "C")]
    out = strip_ansi(render_markdown(md, width=80, color=False))
    assert "Deep" in out
    assert not any("Deep" in line for line in toc)


def test_irregular_heading_nesting_is_rendered_as_it_appears():
    md = "### First h3\n\n# Later h1\n\n## Mid\n"
    toc = _toc_entries(md)
    assert toc == [_toc_line(3, "First h3"), _toc_line(1, "Later h1"), _toc_line(2, "Mid")]


def test_toc_precedes_the_whole_body_when_there_is_no_leading_h1():
    md = "## First\n\n### Nested\n\nbody text\n"
    out = strip_ansi(render_markdown(md, width=80, color=False, toc=True))
    lines = [line for line in _rstripped(out) if line]
    assert lines[0] == _toc_line(2, "First")
    assert lines[1] == _toc_line(3, "Nested")
    body_h2 = next(i for i, line in enumerate(lines) if line == "First")
    assert body_h2 > 1
    assert any("body text" in line for line in lines[body_h2:])


def test_toc_entries_use_the_same_heading_styles_as_the_body():
    md = "# Hello\n\n## World\n\n### Nested\n"
    colored = render_markdown(md, width=80, color=True)
    lines = [line for line in colored.splitlines() if line.strip()]
    # Leading h1 is the title (centered, bold+underline), then ToC h2/h3.
    assert "\x1b[1;4mHello\x1b[0m" in lines[0]
    assert _is_centered(strip_ansi(lines[0]), "Hello")
    assert "\x1b[4;35mWorld\x1b[0m" in lines[1]
    assert strip_ansi(lines[1]) == _toc_line(2, "World")
    assert "\x1b[1;35mNested\x1b[0m" in lines[2]
    assert strip_ansi(lines[2]) == _toc_line(3, "Nested")
    body_h2 = [line for line in lines[3:] if "World" in strip_ansi(line)]
    body_h3 = [line for line in lines[3:] if "Nested" in strip_ansi(line)]
    assert body_h2 and "\x1b[4;35mWorld\x1b[0m" in body_h2[0]
    assert body_h3 and "\x1b[1;35mNested\x1b[0m" in body_h3[0]
    # Title is not repeated below the ToC.
    assert not any("Hello" in strip_ansi(line) for line in lines[1:])


def test_toc_entries_are_osc8_links_to_their_own_heading():
    # VIEWMD-0077: each ToC entry carries a real OSC8 hyperlink around just its heading text
    # (not the bullet), targeting the viewmd-toc: scheme by occurrence-rank + heading text.
    md = "# Title\n\n## Section\n\n### Nested\n"
    colored = render_markdown(md, width=80, color=True)
    assert "\x1b]8;" in colored
    assert "viewmd-toc:0:Section" in colored
    assert "viewmd-toc:0:Nested" in colored
    # The bullet marker itself is not wrapped in the link -- only the heading text.
    bullet_line = next(line for line in colored.splitlines() if "Section" in line)
    link_start = bullet_line.index("\x1b]8;")
    assert "•" not in bullet_line[link_start:]


def test_toc_duplicate_heading_text_gets_distinct_ranked_hrefs():
    # Regression (found in review): two different headings sharing the exact same text must not
    # both link to the same "first match wins" target -- each gets its own occurrence rank.
    md = "# Title\n\n## Overview\n\nfirst\n\n## Details\n\nmid\n\n## Overview\n\nsecond\n"
    colored = render_markdown(md, width=80, color=True)
    assert "viewmd-toc:0:Overview" in colored
    assert "viewmd-toc:1:Overview" in colored


def test_toc_entries_visible_text_unchanged_by_the_link_wrapper():
    # VIEWMD-0077 requirement 2: the OSC8 wrapper must not change the entry's own visible
    # text/styling -- diffing everything except the OSC8 bytes against the pre-link rendering.
    md = "# Title\n\n## Section\n\n### Nested\n"
    colored = render_markdown(md, width=80, color=True)
    plain = render_markdown(md, width=80, color=False)
    assert strip_ansi(colored) == plain


def test_toc_anchor_scheme_not_present_when_toc_is_off():
    md = "# Title\n\n## Section\n"
    colored = render_markdown(md, width=80, color=True, toc=False)
    assert "viewmd-toc:" not in colored


def test_toc_uses_plain_text_of_inline_markup_in_headings():
    md = "# With **bold** title\n\n## With **bold** and `code` and [link](http://x)\n"
    toc = _toc_entries(md)
    assert toc == [_toc_line(2, "With bold and code and link")]
    out = strip_ansi(render_markdown(md, width=80, color=False))
    assert any(_is_centered(line, "With bold title") for line in _rstripped(out))


def test_toc_title_resolves_reference_links_defined_later_in_the_document():
    md = "# See [foo]\n\n## Section\n\n[foo]: http://example.com\n"
    on = strip_ansi(render_markdown(md, width=80, color=False, toc=True))
    off = strip_ansi(render_markdown(md, width=80, color=False, toc=False))
    on_title = next(line for line in _rstripped(on) if line.strip())
    off_title = next(line for line in _rstripped(off) if line.strip())
    assert on_title == off_title
    assert _is_centered(on_title, "See foo")
    assert "See [foo]" not in on
    colored_title = next(
        line for line in render_markdown(md, width=80, color=True, toc=True).splitlines()
        if line.strip()
    )
    assert "http://example.com" in colored_title


def test_hash_comment_inside_a_fence_is_not_a_toc_entry():
    md = "```\n# not a heading\n```\n\n# Real\n\n## Also real\n"
    toc = _toc_entries(md)
    assert toc == [_toc_line(2, "Also real")]
    assert not any("not a heading" in line for line in toc)


def test_toc_keeps_all_three_levels_at_exactly_20_displayed_entries():
    # Title h1 is not a ToC line. 1 h2 + 19 h3 = 20 displayed; cap allows 20.
    entries = [(1, "Top"), (2, "Mid")] + [(3, f"Leaf {i}") for i in range(19)]
    lines = _toc_entries(_headings_md(entries))
    assert len(lines) == 20
    assert lines[0] == _toc_line(2, "Mid")
    assert lines[1] == _toc_line(3, "Leaf 0")
    assert lines[-1] == _toc_line(3, "Leaf 18")
    assert not any(line.startswith("...") for line in lines)


def test_toc_drops_h3_when_displayed_outline_exceeds_20_entries():
    # Title "One" is not in the ToC. Displayed: Two + 2 h2 + 18 h3 = 21, so drop h3.
    entries = [
        (1, "One"), (2, "One-a"), (3, "deep-a"),
        (1, "Two"), (2, "Two-a"),
    ] + [(3, f"Leaf {i}") for i in range(17)]
    lines = _toc_entries(_headings_md(entries))
    assert lines == [_toc_line(2, "One-a"), _toc_line(1, "Two"), _toc_line(2, "Two-a")]
    assert not any(line.startswith("...") for line in lines)
    assert not any("Leaf" in line or "deep-a" in line for line in lines)
    body = strip_ansi(render_markdown(_headings_md(entries), width=80, color=False))
    assert "deep-a" in body
    assert "Leaf 0" in body


def test_toc_drops_h2_when_h1_h2_still_exceeds_20_entries():
    # Title A omitted. Displayed: 19 h2 + B + C = 21, so drop to remaining h1s.
    entries = [(1, "A")] + [(2, f"A-{i}") for i in range(19)] + [(1, "B"), (1, "C")]
    lines = _toc_entries(_headings_md(entries))
    assert lines == [_toc_line(1, "B"), _toc_line(1, "C")]
    assert not any(line.startswith("...") for line in lines)


def test_toc_truncates_overflowing_h1s_to_20_with_more_note():
    # Title is Chapter 0. 21 remaining h1s: depth-stepping cannot shrink further.
    entries = [(1, f"Chapter {i}") for i in range(22)]
    lines = _toc_entries(_headings_md(entries))
    assert lines[:20] == [_toc_line(1, f"Chapter {i}") for i in range(1, 21)]
    assert lines[20] == _toc_more(1)
    assert len(lines) == 21
    assert _toc_line(1, "Chapter 21") not in lines
    body = strip_ansi(render_markdown(_headings_md(entries), width=80, color=False))
    assert "Chapter 21" in body


def test_toc_truncates_overflowing_h3s_when_there_is_no_shallower_outline():
    # 21 h3s, no h1/h2: dropping a level would empty the ToC, so keep then truncate.
    entries = [(3, f"Note {i}") for i in range(21)]
    lines = _toc_entries(_headings_md(entries))
    assert lines[:20] == [_toc_line(3, f"Note {i}") for i in range(20)]
    assert lines[20] == _toc_more(1)
    assert len(lines) == 21


def test_toc_truncates_flat_h2_outline_past_20_entries():
    # CHANGELOG.md's shape: one title h1 + many h2s, no h3s. Depth-stepping is a
    # no-op or would empty the list, so truncate to 20 and note the rest.
    entries = [(1, "Changelog")] + [(2, f"Version {i}") for i in range(50)]
    lines = _toc_entries(_headings_md(entries))
    assert lines[:20] == [_toc_line(2, f"Version {i}") for i in range(20)]
    assert lines[20] == _toc_more(30)
    assert len(lines) == 21
    assert _toc_line(2, "Version 20") not in lines
    body = strip_ansi(render_markdown(_headings_md(entries), width=80, color=False))
    assert "Version 20" in body
    assert "Version 49" in body


def test_toc_list_marker_matches_body_bullet_lists():
    body = strip_ansi(render_markdown("- one\n  - two\n    - three\n", width=80, color=False))
    body_lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    assert len(body_lines) == 3

    def prefix(line: str, text: str) -> str:
        return line[: line.index(text)]

    assert prefix(body_lines[0], "one") == prefix(_toc_line(1, "one"), "one")
    assert prefix(body_lines[1], "two") == prefix(_toc_line(2, "two"), "two")
    assert prefix(body_lines[2], "three") == prefix(_toc_line(3, "three"), "three")
    md = "### three\n\n## two\n\n# one\n"
    toc = _toc_entries(md)
    assert toc == [_toc_line(3, "three"), _toc_line(2, "two"), _toc_line(1, "one")]


def test_toc_one_remaining_h1_after_depth_cap_is_still_rendered():
    # Title Only + later h1 Rest + 20 h3s. Displayed 1 h1 + 20 h3 = 21, drop h3
    # to the remaining h1. Requirement 7 checked the full extract (22 headings).
    entries = [(1, "Only"), (1, "Rest")] + [(3, f"Leaf {i}") for i in range(20)]
    lines = _toc_entries(_headings_md(entries))
    assert lines == [_toc_line(1, "Rest")]
    assert not any(line.startswith("...") for line in lines)


def test_toc_more_note_is_not_heading_styled():
    entries = [(1, "Top")] + [(2, f"S{i}") for i in range(21)]
    colored = render_markdown(_headings_md(entries), width=80, color=True)
    more = next(line for line in colored.splitlines() if "more" in strip_ansi(line))
    assert strip_ansi(more).strip() == _toc_more(1)
    # Heading styles (h2 magenta-underline, h3 magenta-bold) must not apply to the note.
    assert "\x1b[4;35m" not in more
    assert "\x1b[1;35m" not in more
    assert "•" not in strip_ansi(more)
