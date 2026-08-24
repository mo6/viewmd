"""Tests for `viewmd:mark` sentinel highlighting (VIEWMD-0104)."""

from __future__ import annotations

import re

from viewmd.highlight import DEFAULT_KIND, MarkRegion, strip_marks
from viewmd.render import _MARK_BACKGROUND, render_markdown

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m|\x1b\]8;[^\x1b]*\x1b\\")
WIDTH = 60


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def has_background(line: str, kind: str) -> bool:
    return _MARK_BACKGROUND[kind] in line


def _foregrounds(text: str) -> set[str]:
    # Not anchored on a trailing "m": an unmarked line's own combined SGR sequence can carry a
    # background right after the foreground in the *same* escape (e.g.
    # "\x1b[38;2;r;g;b;48;2;r;g;bm"), while a marked line's foreground appears in its own escape
    # after `_strip_line_backgrounds` splits the two apart -- both must count as "the same
    # foreground color" for this comparison.
    return set(re.findall(r"38;2;\d+;\d+;\d+", text))


def _backgrounds(text: str) -> set[str]:
    return set(re.findall(r"48;2;\d+;\d+;\d+", text))


# ---------------------------------------------------------------------------
# strip_marks() -- text-level sentinel parsing
# ---------------------------------------------------------------------------


def test_strip_marks_removes_sentinel_lines_and_records_region():
    text = "A\n\n<!-- viewmd:mark start kind=added -->\nB\n<!-- viewmd:mark end -->\n\nC\n"
    stripped, regions, warnings = strip_marks(text)
    assert stripped == "A\n\nB\n\nC\n"
    assert regions == [MarkRegion("added", 2, 2)]
    assert warnings == []


def test_strip_marks_tolerates_flexible_whitespace():
    text = "<!--viewmd:mark start-->\nB\n<!--  viewmd:mark  end  -->\n"
    stripped, regions, warnings = strip_marks(text)
    assert stripped == "B\n"
    assert regions == [MarkRegion(DEFAULT_KIND, 0, 0)]
    assert warnings == []


def test_strip_marks_defaults_unknown_kind_to_changed():
    text = "<!-- viewmd:mark start kind=bogus -->\nB\n<!-- viewmd:mark end -->\n"
    _stripped, regions, warnings = strip_marks(text)
    assert regions == [MarkRegion("changed", 0, 0)]
    assert warnings == []


def test_strip_marks_accepts_all_three_kinds():
    for kind in ("added", "changed", "removed"):
        text = f"<!-- viewmd:mark start kind={kind} -->\nB\n<!-- viewmd:mark end -->\n"
        _stripped, regions, _warnings = strip_marks(text)
        assert regions == [MarkRegion(kind, 0, 0)]


def test_strip_marks_unbalanced_start_extends_to_end_of_document():
    text = "<!-- viewmd:mark start kind=added -->\nB\nC\n"
    stripped, regions, warnings = strip_marks(text)
    assert stripped == "B\nC\n"
    # end_line == 2, not 1: `text.split("\n")` on a trailing-newline-terminated string yields a
    # final "" element with no real content of its own -- a harmlessly generous upper bound for
    # an *unbalanced* region (nothing downstream ever has a line number that high to wrongly
    # match against it).
    assert regions == [MarkRegion("added", 0, 2)]
    assert len(warnings) == 1
    assert "unbalanced" in warnings[0]


def test_strip_marks_stray_end_is_ignored_and_warns():
    text = "A\n<!-- viewmd:mark end -->\nB\n"
    stripped, regions, warnings = strip_marks(text)
    assert stripped == "A\nB\n"
    assert regions == []
    assert len(warnings) == 1
    assert "no open start" in warnings[0]


def test_strip_marks_nested_start_is_ignored_and_warns():
    text = (
        "<!-- viewmd:mark start kind=added -->\n"
        "A\n"
        "<!-- viewmd:mark start kind=removed -->\n"
        "B\n"
        "<!-- viewmd:mark end -->\n"
    )
    stripped, regions, warnings = strip_marks(text)
    assert stripped == "A\nB\n"
    assert regions == [MarkRegion("added", 0, 1)]
    assert len(warnings) == 1
    assert "nested" in warnings[0]


def test_strip_marks_malformed_comment_is_stripped_and_warns():
    text = "A\n\n<!-- viewmd:mark strat -->\nB\n\nC\n"
    stripped, regions, warnings = strip_marks(text)
    assert stripped == "A\n\nB\n\nC\n"
    assert regions == []
    assert len(warnings) == 1
    assert "malformed" in warnings[0]


def test_strip_marks_leaves_sentinel_looking_text_inside_a_fence_untouched():
    text = (
        "```\n"
        "<!-- viewmd:mark start kind=added -->\n"
        "```\n"
        "\n"
        "<!-- viewmd:mark start kind=added -->\n"
        "B\n"
        "<!-- viewmd:mark end -->\n"
    )
    stripped, regions, warnings = strip_marks(text)
    # The fenced copy survives verbatim; only the real (unfenced) pair is stripped/recorded.
    assert stripped == "```\n<!-- viewmd:mark start kind=added -->\n```\n\nB\n"
    assert regions == [MarkRegion("added", 4, 4)]
    assert warnings == []


def test_strip_marks_no_sentinels_is_unchanged():
    text = "A\n\nB\n"
    stripped, regions, warnings = strip_marks(text)
    assert stripped == text
    assert regions == []
    assert warnings == []


# ---------------------------------------------------------------------------
# render_markdown() -- background tinting
# ---------------------------------------------------------------------------


def _marked(kind: str, body: str) -> str:
    return f"<!-- viewmd:mark start kind={kind} -->\n{body}\n<!-- viewmd:mark end -->\n"


def test_added_region_tinted_green_across_full_width_including_wrapped_lines():
    long_paragraph = "word " * 40
    text = f"Intro.\n\n{_marked('added', long_paragraph.strip())}\nOutro.\n"
    out = render_markdown(text, width=WIDTH, color=True, toc=False)
    lines = out.split("\n")
    marked_lines = [line for line in lines if has_background(line, "added")]
    assert len(marked_lines) >= 2  # the paragraph wraps at this width
    for line in marked_lines:
        assert strip_ansi(line).rstrip("\n") == " " * WIDTH or len(strip_ansi(line)) >= WIDTH


def test_changed_and_removed_kinds_use_their_own_background():
    text = (
        f"{_marked('changed', 'changed text')}\n"
        f"{_marked('removed', 'removed text')}\n"
    )
    out = render_markdown(text, width=WIDTH, color=True, toc=False)
    assert any(has_background(line, "changed") for line in out.split("\n"))
    assert any(has_background(line, "removed") for line in out.split("\n"))


def test_marked_table_and_mermaid_block_are_tinted():
    table_markdown = "| a | b |\n|---|---|\n| 1 | 2 |"
    text = (
        f"{_marked('added', table_markdown)}\n"
        "```mermaid\n"
        "pie title P\n"
        '    "A" : 1\n'
        '    "B" : 1\n'
        "```\n"
    )
    marked_table = render_markdown(text, width=WIDTH, color=True, toc=False)
    table_lines = [
        line for line in marked_table.split("\n") if has_background(line, "added")
    ]
    assert len(table_lines) >= 3  # header, rule, one data row at minimum

    mermaid_text = _marked(
        "removed",
        '```mermaid\npie title P\n    "A" : 1\n    "B" : 1\n```',
    )
    out = render_markdown(mermaid_text, width=WIDTH, color=True, toc=False)
    diagram_lines = [
        line for line in out.split("\n") if has_background(line, "removed")
    ]
    assert len(diagram_lines) >= 4


def test_foreground_colors_survive_marking_code_fence():
    code = "```python\ndef foo():\n    return 1\n```"
    marked = render_markdown(_marked("added", code), width=WIDTH, color=True, toc=False)
    unmarked = render_markdown(code + "\n", width=WIDTH, color=True, toc=False)
    assert _foregrounds(marked) == _foregrounds(unmarked)
    assert _foregrounds(marked)  # sanity: the fence really is syntax-highlighted


def test_marked_region_background_overrides_content_own_background():
    code = "```python\ndef foo():\n    return 1\n```"
    marked = render_markdown(_marked("removed", code), width=WIDTH, color=True, toc=False)
    unmarked = render_markdown(code + "\n", width=WIDTH, color=True, toc=False)

    unmarked_backgrounds = set(re.findall(r"\x1b\[48;2;\d+;\d+;\d+m", unmarked))
    marked_backgrounds = set(re.findall(r"\x1b\[48;2;\d+;\d+;\d+m", marked))
    # The fence's own themed background (present when unmarked) must not survive marking --
    # only the mark's own removed-red background should appear.
    assert unmarked_backgrounds - {_MARK_BACKGROUND["removed"]}
    assert marked_backgrounds == {_MARK_BACKGROUND["removed"]}


_QUADRANT_MERMAID = (
    "```mermaid\n"
    "quadrantChart\n"
    "    x-axis Low --> High\n"
    "    y-axis Low --> High\n"
    "    quadrant-1 Q1\n"
    "    quadrant-2 Q2\n"
    "    quadrant-3 Q3\n"
    "    quadrant-4 Q4\n"
    "    Point A: [0.3, 0.6]\n"
    "```"
)


def test_marked_mermaid_quadrant_chart_keeps_its_own_foreground_tints():
    marked = render_markdown(
        _marked("changed", _QUADRANT_MERMAID), width=WIDTH, color=True, toc=False
    )
    unmarked = render_markdown(_QUADRANT_MERMAID + "\n", width=WIDTH, color=True, toc=False)
    marked_fg = _foregrounds(marked)
    unmarked_fg = _foregrounds(unmarked)
    assert unmarked_fg  # sanity: the quadrant chart really does have its own foreground colors
    assert marked_fg == unmarked_fg


def test_marked_mermaid_quadrant_chart_background_overrides_its_own_quadrant_fill():
    marked = render_markdown(
        _marked("removed", _QUADRANT_MERMAID), width=WIDTH, color=True, toc=False
    )
    unmarked = render_markdown(_QUADRANT_MERMAID + "\n", width=WIDTH, color=True, toc=False)
    mark_bg = _backgrounds(_MARK_BACKGROUND["removed"]).pop()
    unmarked_bg = _backgrounds(unmarked)
    marked_bg = _backgrounds(marked)
    # The quadrant chart paints its own per-quadrant background fill when unmarked...
    assert unmarked_bg - {mark_bg}
    # ...but none of that survives once marked -- only the mark's own background remains.
    assert marked_bg == {mark_bg}


def test_color_never_output_identical_to_sentinels_simply_deleted():
    text = f"A\n\n{_marked('added', 'B')}\nC\n"
    stripped = "A\n\nB\n\nC\n"
    marked_out = render_markdown(text, width=WIDTH, color=False, toc=False)
    stripped_out = render_markdown(stripped, width=WIDTH, color=False, toc=False)
    assert marked_out == stripped_out


def test_sentinel_comments_never_appear_in_output():
    text = f"A\n\n{_marked('added', 'B')}\nC\n"
    out_color = render_markdown(text, width=WIDTH, color=True, toc=False)
    out_no_color = render_markdown(text, width=WIDTH, color=False, toc=False)
    assert "viewmd:mark" not in out_color
    assert "viewmd:mark" not in out_no_color


def test_marked_document_blank_line_spacing_matches_sentinels_deleted():
    text = f"A\n\n{_marked('added', 'B')}\nC\n"
    stripped = "A\n\nB\n\nC\n"
    marked_out = render_markdown(text, width=WIDTH, color=True, toc=False)
    stripped_out = render_markdown(stripped, width=WIDTH, color=True, toc=False)
    marked_plain = strip_ansi(marked_out).split("\n")
    stripped_plain = strip_ansi(stripped_out).split("\n")
    assert len(marked_plain) == len(stripped_plain)
    for marked_line, stripped_line in zip(marked_plain, stripped_plain, strict=True):
        assert marked_line.rstrip() == stripped_line.rstrip()


# Byte-pinned against the pre-VIEWMD-0104 `develop` tip (verified by running this exact call
# against a checkout of that commit) -- a self-comparison against only the *new* code would pass
# even if this change had silently altered ordinary rendering, per this project's own established
# lesson about golden fixtures (AGENTS.md: "a golden fixture that gets edited to match new output
# isn't proof of no regression -- check it against the pre-change commit").
_NO_MARKS_GOLDEN = (
    "                           \x1b[1;4mTitle\x1b[0m                            \n"
    "\nSome paragraph.                                             \n"
    "\n\x1b[36m      \x1b[0m\n"
    "\x1b[36m \x1b[0m\x1b[36ma\x1b[0m\x1b[1m \x1b[0m\x1b[36m \x1b[0m\x1b[36mb\x1b[0m"
    "\x1b[36m \x1b[0m\n"
    "\x1b[36m ──── \x1b[0m\n"
    "\x1b[36m \x1b[0m1 \x1b[36m \x1b[0m2\x1b[36m \x1b[0m\n"
    "\x1b[36m      \x1b[0m\n"
)


def test_document_with_no_sentinels_is_byte_identical_to_pre_change_baseline():
    text = "# Title\n\nSome paragraph.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    out = render_markdown(text, width=WIDTH, color=True, toc=False)
    assert out == _NO_MARKS_GOLDEN


def test_unbalanced_start_warns_and_still_renders(capsys):
    text = "A\n\n<!-- viewmd:mark start kind=added -->\nB\n"
    out = render_markdown(text, width=WIDTH, color=True, toc=False)
    assert "B" in strip_ansi(out)
    err = capsys.readouterr().err
    assert "viewmd:" in err
    assert "unbalanced" in err


def test_stray_end_warns_and_still_renders(capsys):
    text = "A\n\n<!-- viewmd:mark end -->\n\nB\n"
    out = render_markdown(text, width=WIDTH, color=True, toc=False)
    assert "A" in strip_ansi(out)
    assert "B" in strip_ansi(out)
    err = capsys.readouterr().err
    assert "viewmd:" in err
    assert "no open start" in err


# ---------------------------------------------------------------------------
# Region nested inside an existing container (VIEWMD-0106) -- a mark whose sentinels sit
# between two list items of the *same* list, not between two top-level blocks, matching
# gitgleam's real generated output for "one new bullet appended to an existing list".
# ---------------------------------------------------------------------------


def _tinted_lines(out: str, kind: str) -> list[str]:
    return [line for line in out.split("\n") if has_background(line, kind)]


def test_mark_nested_inside_a_single_list_item_is_tinted():
    text = (
        "- first existing item\n"
        "- second existing item\n"
        f"{_marked('added', '- third item, newly added')}\n"
    )
    out = render_markdown(text, width=WIDTH, color=True, toc=False)
    tinted = _tinted_lines(out, "added")
    assert len(tinted) == 1
    assert "third item, newly added" in strip_ansi(tinted[0])
    # The two pre-existing items must stay untinted.
    plain_lines = strip_ansi(out).split("\n")
    for line, plain in zip(out.split("\n"), plain_lines, strict=True):
        if "existing item" in plain:
            assert not has_background(line, "added")


def test_mark_nested_inside_a_list_item_in_the_middle_of_the_list_is_tinted():
    text = (
        "- first item\n"
        f"{_marked('changed', '- second item, changed')}\n"
        "- third item\n"
    )
    out = render_markdown(text, width=WIDTH, color=True, toc=False)
    tinted = _tinted_lines(out, "changed")
    assert len(tinted) == 1
    assert "second item, changed" in strip_ansi(tinted[0])


def test_mark_nested_two_levels_deep_inside_a_sub_list_is_tinted():
    text = (
        "- outer item one\n"
        "- outer item two\n"
        "  - inner item A\n"
        "  - inner item B\n"
        "  <!-- viewmd:mark start kind=added -->\n"
        "  - inner item C\n"
        "  <!-- viewmd:mark end -->\n"
        "- outer item three\n"
    )
    out = render_markdown(text, width=WIDTH, color=True, toc=False)
    tinted = _tinted_lines(out, "added")
    assert len(tinted) == 1
    assert "inner item C" in strip_ansi(tinted[0])
    unmarked_names = (
        "outer item one", "outer item two", "inner item A", "inner item B", "outer item three",
    )
    for name in unmarked_names:
        for line in out.split("\n"):
            if name in strip_ansi(line):
                assert not has_background(line, "added")


def test_mark_nested_inside_an_ordered_list_item_does_not_apply_wrong_highlight():
    # An ordered list is deliberately excluded from _is_recursable_container: rich's own
    # ListElement.render_number sizes its numbering column from len(self.items) -- the item
    # *count actually present in that render*, not the document's true total -- so a "closed
    # early" partial-list reconstruction can pick a different column width than the real
    # full-list render whenever the two item counts have a different digit count, silently
    # mismeasuring (and, worse than a table row, capable of tinting the *wrong* item rather than
    # just failing to tint one). This 12-item list crosses exactly that digit-count boundary
    # (13 total -> width from "13"; a 4-item reconstructed prefix -> width from "4"), with item
    # 2's content long enough to wrap differently under the two widths -- reproducing the bug
    # found during this issue's own independent review before _is_recursable_container excluded
    # ordered lists. The safe fallback (VIEWMD-0104 requirement 10) is simply no highlight.
    items = [
        "first item",
        "second item is long enough that it may wrap under one numbering width but not another",
        *(f"item {n}" for n in range(3, 13)),
    ]
    lines = [f"{i}. {item}" for i, item in enumerate(items, start=1)]
    lines[4] = f"{_marked('removed', lines[4])}"  # mark item 5 (index 4)
    text = "\n".join(lines) + "\n"
    out = render_markdown(text, width=WIDTH, color=True, toc=False)
    assert _tinted_lines(out, "removed") == []


def test_mark_nested_inside_a_table_row_does_not_apply_wrong_highlight():
    # A table row shares its enclosing table's box-drawn top/bottom border, which only renders
    # once at the true start/end of the whole table -- a "closed early" partial-table
    # reconstruction would draw that border prematurely and silently mismeasure every later
    # line, so nesting into a table row is deliberately not supported (_is_recursable_container).
    # The safe fallback (VIEWMD-0104 requirement 10) is simply no highlight, not a wrong one.
    text = (
        "| a | b |\n|---|---|\n| 1 | 2 |\n"
        f"{_marked('changed', '| 3 | 4 |')}\n"
        "| 5 | 6 |\n"
    )
    out = render_markdown(text, width=WIDTH, color=True, toc=False)
    assert _tinted_lines(out, "changed") == []
    # And nothing else gets wrongly tinted either.
    for kind in ("added", "changed", "removed"):
        assert _tinted_lines(out, kind) == []


# ---------------------------------------------------------------------------
# Generic (non-mark) standalone HTML comment stripping (VIEWMD-0107).
# ---------------------------------------------------------------------------


def test_strip_marks_removes_a_plain_single_line_comment():
    text = "A\n\n<!-- an ordinary editorial comment -->\nB\n"
    stripped, regions, warnings = strip_marks(text)
    assert stripped == "A\n\nB\n"
    assert regions == []
    assert warnings == []


def test_strip_marks_removes_a_multi_line_comment_as_one_block():
    text = "A\n\n<!--\nmulti\nline\ncomment\n-->\nB\n"
    stripped, regions, warnings = strip_marks(text)
    assert stripped == "A\n\nB\n"
    assert regions == []
    assert warnings == []


def test_strip_marks_leaves_an_inline_comment_in_running_text_untouched():
    text = "A text <!-- inline --> more text.\n"
    stripped, regions, warnings = strip_marks(text)
    assert stripped == text
    assert regions == []
    assert warnings == []


def test_strip_marks_unterminated_comment_warns_and_drops_the_rest():
    text = "A\n\n<!-- never closes\nrest\nmore"
    stripped, regions, warnings = strip_marks(text)
    assert stripped == "A\n"
    assert regions == []
    assert len(warnings) == 1
    assert "unterminated" in warnings[0]


def test_plain_comment_blank_line_spacing_matches_comment_simply_deleted():
    text = "A\n\n<!-- an ordinary comment -->\n\nB\n"
    stripped = "A\n\nB\n"
    with_comment = render_markdown(text, width=WIDTH, color=False, toc=False)
    without_comment = render_markdown(stripped, width=WIDTH, color=False, toc=False)
    assert with_comment == without_comment


def test_multi_line_comment_blank_line_spacing_matches_comment_simply_deleted():
    text = "A\n\n<!--\nmulti\nline\ncomment\n-->\n\nB\n"
    stripped = "A\n\nB\n"
    with_comment = render_markdown(text, width=WIDTH, color=False, toc=False)
    without_comment = render_markdown(stripped, width=WIDTH, color=False, toc=False)
    assert with_comment == without_comment


def test_viewmd_mark_handling_is_unaffected_by_generic_comment_stripping():
    text = f"A\n\n{_marked('added', 'B')}\n\nC\n\n<!-- ordinary -->\n\nD\n"
    out = render_markdown(text, width=WIDTH, color=True, toc=False)
    assert has_background(
        [line for line in out.split("\n") if "B" in strip_ansi(line)][0], "added"
    )
    assert "viewmd:mark" not in out
    assert "ordinary" not in strip_ansi(out)  # the plain comment's own text never appears
