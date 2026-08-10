from viewmd.wikilinks import rewrite_wikilinks


def test_bare_wikilink_rewrites_to_markdown_link():
    assert rewrite_wikilinks("see [[Target]] here") == "see [Target](<wikilink:Target>) here"


def test_piped_wikilink_uses_display_text():
    assert (
        rewrite_wikilinks("see [[Target|Display text]] here")
        == "see [Display text](<wikilink:Target>) here"
    )


def test_wikilink_inside_fenced_code_block_is_untouched():
    md = "prose [[Outside]]\n```\ncode [[Inside]]\n```\nafter [[After]]\n"
    assert rewrite_wikilinks(md) == (
        "prose [Outside](<wikilink:Outside>)\n```\ncode [[Inside]]\n```\n"
        "after [After](<wikilink:After>)\n"
    )


def test_wikilink_inside_tilde_fenced_code_block_is_untouched():
    md = "~~~\ndes.map([[...]])\n~~~\n"
    assert rewrite_wikilinks(md) == md


def test_wikilink_inside_indented_fenced_code_block_is_untouched():
    # A fence nested under a list item is indented, not at column 0; still must count as a fence.
    md = "- item\n  ```\n  code [[Inside]]\n  ```\n  after [[After]]\n"
    assert rewrite_wikilinks(md) == (
        "- item\n  ```\n  code [[Inside]]\n  ```\n  after [After](<wikilink:After>)\n"
    )


def test_wikilink_shaped_string_inside_inline_code_is_untouched():
    md = "call `des.map([[...]])` then [[Real]]"
    assert rewrite_wikilinks(md) == "call `des.map([[...]])` then [Real](<wikilink:Real>)"


def test_plain_text_with_no_wikilinks_passes_through_unchanged():
    md = "# Hello\n\njust some prose and a [normal](https://example.com) link\n"
    assert rewrite_wikilinks(md) == md


def test_wikilink_target_with_space_produces_valid_link_destination():
    # A bare `(wikilink:Getting Started)` destination has an unescaped space, which is invalid
    # CommonMark outside of the <...> bracketed form -- Rich would fall back to printing the raw
    # markdown instead of rendering a styled link (the bug this guards against).
    assert (
        rewrite_wikilinks("[[Getting Started]]")
        == "[Getting Started](<wikilink:Getting Started>)"
    )


def test_wikilink_target_with_angle_bracket_is_escaped():
    assert (
        rewrite_wikilinks("[[Weird <Target>]]") == "[Weird <Target>](<wikilink:Weird \\<Target\\>>)"
    )
