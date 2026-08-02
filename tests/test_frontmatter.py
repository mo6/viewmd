from viewmd.frontmatter import parse_front_matter, split_front_matter


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
