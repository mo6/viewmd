from viewmd.frontmatter import drop_empty, parse_front_matter, split_front_matter


def test_split_returns_none_when_no_leading_dashes():
    text = "# Hello\n\nno front matter here\n"
    raw, body = split_front_matter(text)
    assert raw is None
    assert body == text


def test_split_returns_none_when_unterminated():
    text = "---\ntitle: Hello\n\n# Body\n"
    raw, body = split_front_matter(text)
    assert raw is None
    assert body == text


def test_split_extracts_block_and_body():
    text = "---\ntitle: Hello\nstatus: draft\n---\n# Body\n\ntext\n"
    raw, body = split_front_matter(text)
    assert raw == "title: Hello\nstatus: draft\n"
    assert body == "# Body\n\ntext\n"


def test_split_handles_empty_front_matter_block():
    text = "---\n---\n# Body\n"
    raw, body = split_front_matter(text)
    assert raw == ""
    assert body == "# Body\n"


def test_parse_flat_key_value_pairs():
    data = parse_front_matter("title: Hello\nstatus: draft\n")
    assert data == {"title": "Hello", "status": "draft"}


def test_parse_strips_quotes():
    data = parse_front_matter('title: "Hello there"\n')
    assert data == {"title": "Hello there"}


def test_parse_renders_bracketed_list_as_comma_joined():
    data = parse_front_matter("area: [render, pager, cli]\n")
    assert data == {"area": "render, pager, cli"}


def test_parse_skips_blank_lines_and_comments():
    data = parse_front_matter("title: Hello\n\n# a comment\nstatus: draft\n")
    assert data == {"title": "Hello", "status": "draft"}


def test_parse_skips_lines_without_a_colon():
    data = parse_front_matter("title: Hello\njust some prose\nstatus: draft\n")
    assert data == {"title": "Hello", "status": "draft"}


def test_parse_empty_block_yields_empty_dict():
    assert parse_front_matter("") == {}
    assert parse_front_matter("# just a comment\n") == {}


def test_drop_empty_removes_blank_and_whitespace_only_values():
    data = {"title": "Hello", "accepted_by": "", "reason": "   "}
    assert drop_empty(data) == {"title": "Hello"}


def test_drop_empty_keeps_non_empty_values():
    data = {"title": "Hello", "status": "draft"}
    assert drop_empty(data) == data


def test_drop_empty_of_empty_dict_is_empty_dict():
    assert drop_empty({}) == {}


def test_drop_empty_all_blank_yields_empty_dict():
    assert drop_empty({"a": "", "b": "  "}) == {}


def test_parse_nested_mapping_does_not_collide_with_top_level_key_of_same_name():
    data = parse_front_matter("title: Real title\nseo:\n  title: SEO title\n")
    assert data == {"title": "Real title", "seo.title": "SEO title"}


def test_parse_nested_mapping_flattens_to_dotted_keys_at_any_depth():
    data = parse_front_matter("social:\n  twitter:\n    card: summary\n")
    assert data == {"social.twitter.card": "summary"}


def test_parse_block_list_array_matches_bracket_form():
    dashed = parse_front_matter("tags:\n  - a\n  - b\n  - c\n")
    bracketed = parse_front_matter("tags: [a, b, c]\n")
    assert dashed == bracketed == {"tags": "a, b, c"}


def test_parse_array_of_objects_keeps_every_item():
    raw = (
        "authors:\n"
        "  - name: John\n"
        "    email: john@example.com\n"
        "  - name: Jane\n"
        "    email: jane@example.com\n"
    )
    data = parse_front_matter(raw)
    assert data == {
        "authors": "name: John, email: john@example.com; name: Jane, email: jane@example.com",
    }


def test_parse_literal_block_scalar_preserves_line_breaks():
    data = parse_front_matter("summary: |\n  line one\n  line two\n")
    assert data == {"summary": "line one\nline two"}


def test_parse_folded_block_scalar_joins_with_spaces():
    data = parse_front_matter("summary: >\n  line one\n  line two\n")
    assert data == {"summary": "line one line two"}


def test_parse_still_handles_flat_mapping_unchanged():
    data = parse_front_matter("title: Hello\nstatus: draft\narea: [render, cli]\n")
    assert data == {"title": "Hello", "status": "draft", "area": "render, cli"}
