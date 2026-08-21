"""Tests for viewmd's own interactive pager (VIEWMD-0007).

Covers every pure helper function directly -- the raw-terminal event loop itself (`run`) isn't
unit-testable without a real tty, so these lock down the logic it's built from instead, including
regressions found and fixed while this was developed as `poc/pager/pager_poc.py`. VIEWMD-0094
adds a narrow exception: `run()` is driven against a pipe standing in for `/dev/tty` to pin that
a click-to-quit consumes its paired SGR release rather than leaving it for the shell.
"""

import os
import pathlib
import threading
import time

import pytest

from viewmd import interactive_pager as ip

_KW = {"full_front_matter": False, "toc": False}

_DOC = """\
---
title: Test doc
---

# Title

## Alpha

alpha body text

## Beta

beta body text, with a [[wikilink]] in it

## Gamma

gamma body text
"""


def test_strip_ansi_removes_color_and_hyperlinks():
    colored = "\x1b[1mbold\x1b[0m \x1b]8;id=1;http://x\x1b\\link\x1b]8;;\x1b\\ plain"
    assert ip._strip_ansi(colored) == "bold link plain"


# --- _highlight_matches -----------------------------------------------------------------------


def test_highlight_matches_wraps_every_occurrence_case_insensitively():
    line = "The The the"
    out = ip._highlight_matches(line, "the")
    assert out is not None
    assert ip._strip_ansi(out) == line
    assert out.count(ip._SEARCH_HIGHLIGHT_BG) == 3


def test_highlight_matches_returns_none_for_no_match():
    assert ip._highlight_matches("hello world", "xyz") is None


def test_highlight_matches_returns_none_for_empty_query():
    assert ip._highlight_matches("hello world", "") is None


# --- _load / _locate_headings -------------------------------------------------------------------


def test_load_locates_every_heading_at_the_correct_row():
    colored, plain, headings, _ = ip._load(_DOC, 80, color_kwargs=_KW)
    assert [h.text for h in headings] == ["Title", "Alpha", "Beta", "Gamma"]
    for h in headings:
        assert ip._strip_ansi(plain[h.row]).strip() == h.text
        assert ip._strip_ansi(colored[h.row]).strip() == h.text


def test_load_colored_and_plain_agree_in_length_for_ordinary_markdown():
    colored, plain, _, _ = ip._load(_DOC, 80, color_kwargs=_KW)
    assert len(colored) == len(plain)


def test_nearest_heading_index_picks_the_section_currently_in_view():
    _, _, headings, _ = ip._load(_DOC, 80, color_kwargs=_KW)
    beta_row = next(h.row for h in headings if h.text == "Beta")
    assert ip._nearest_heading_index(headings, top=beta_row + 2) == 2
    assert ip._nearest_heading_index(headings, top=0) == 0


def test_nearest_heading_index_empty_headings_is_zero():
    assert ip._nearest_heading_index([], top=5) == 0


# --- body_start / _home_top (VIEWMD-0080) -------------------------------------------------------


def test_load_body_start_skips_the_front_matter_table():
    _, plain, headings, body_start = ip._load(_DOC, 80, color_kwargs=_KW)
    assert body_start > 0
    assert "═" in plain[body_start - 1]
    assert ip._strip_ansi(plain[body_start]).strip() == "Title"
    title_row = next(h.row for h in headings if h.text == "Title")
    assert body_start == title_row
    # Rows above body_start are the table, still in the document -- scrolling up reaches them.
    assert any("title" in ip._strip_ansi(row) for row in plain[:body_start])


def test_load_body_start_zero_without_front_matter():
    _, _, _, body_start = ip._load("# Just a heading\n\nsome text\n", 80, color_kwargs=_KW)
    assert body_start == 0


def test_load_body_start_zero_for_unterminated_front_matter():
    _, _, _, body_start = ip._load("---\ntitle: Hello\n\n# Body\n", 80, color_kwargs=_KW)
    assert body_start == 0


def test_load_body_start_zero_for_empty_front_matter_block():
    _, _, _, body_start = ip._load("---\n---\n# Body\n", 80, color_kwargs=_KW)
    assert body_start == 0


def test_load_body_start_zero_when_all_fields_are_empty_unless_full():
    md = "---\naccepted_by:\nreason:\n---\n# Body\n"
    _, _, _, body_start = ip._load(md, 80, color_kwargs=_KW)
    assert body_start == 0
    _, plain, _, body_start = ip._load(md, 80, color_kwargs={**_KW, "full_front_matter": True})
    assert body_start > 0
    assert "═" in plain[body_start - 1]


def test_load_body_start_recomputes_when_the_table_wraps():
    keys = "\n".join(f"k{i}: v{i}" for i in range(20))
    md = f"---\n{keys}\nlong: {'word ' * 40}\n---\n# Body\n"
    _, _, _, wide = ip._load(md, 120, color_kwargs=_KW)
    _, _, _, narrow = ip._load(md, 40, color_kwargs=_KW)
    assert wide > 0
    assert narrow > wide


def test_home_top_is_body_start_when_the_document_overflows():
    assert ip._home_top(body_start=10, max_top=50) == 10
    assert ip._home_top(body_start=0, max_top=50) == 0


def test_home_top_clamps_when_the_document_fits_on_screen():
    # max_top == 0 means every line is already visible, so "skip the table" would just leave
    # blank rows at the bottom -- open at 0 instead, matching every other jump's clamp.
    assert ip._home_top(body_start=10, max_top=0) == 0


def test_run_loader_reports_front_matter_body_start(monkeypatch):
    captured = {}

    def fake_run(loader, display_name, *, width, fallback, doc_dir=None, open_path=None):
        captured["loader"] = loader

    monkeypatch.setattr(ip, "_run", fake_run)
    ip.run(_DOC, "test.md", width=80, color=False, toc=False)
    _, plain, _, body_start = captured["loader"](80)
    assert body_start > 0
    assert ip._strip_ansi(plain[body_start]).strip() == "Title"
    assert ip._home_top(body_start, max_top=50) == body_start
    assert ip._home_top(body_start, max_top=0) == 0


def test_run_loader_narrows_for_scrollbar_at_full_width_when_document_overflows(monkeypatch):
    # Bug found in manual maintainer testing: `--width full README.md` showed `›` truncation
    # markers on ordinary prose lines with nothing to actually horizontally scroll to. Root cause,
    # the same two-pass problem `run_directory_listing`'s own loader already solves (VIEWMD-0089):
    # `run()`'s loader wrapped body text to the full terminal width `w` before `_run` knew whether
    # it would end up reserving `_SCROLLBAR_RESERVED_W` columns for a scrollbar (VIEWMD-0079) --
    # once the document had more lines than fit on screen, `draw()`'s crop silently truncated the
    # right edge of every already-wrapped-to-`w` line. `_load_avoiding_scrollbar_crop` now
    # re-renders one `_SCROLLBAR_RESERVED_W` narrower whenever `w` is exactly the terminal's own
    # width and the result needs a scrollbar.
    long_doc = "# Title\n\n" + "\n\n".join(
        f"Paragraph {i} with enough words in it to reliably wrap across the full width of a "
        f"reasonably narrow terminal pane, so this document overflows a small terminal height."
        for i in range(40)
    )

    # A small terminal (`columns=100, lines=10` -> `body_h = 10 - 2 = 8`) so the wrapped document
    # overflows, and `w == term_w` (100) so the full-width condition applies.
    monkeypatch.setattr(ip.shutil, "get_terminal_size", lambda: os.terminal_size((100, 10)))

    captured = {}

    def fake_run(loader, display_name, *, width, fallback, doc_dir=None, open_path=None):
        captured["loader"] = loader

    monkeypatch.setattr(ip, "_run", fake_run)
    ip.run(long_doc, "test.md", width=100, color=False, toc=False)

    w = 100
    colored, plain, _headings, _body_start = captured["loader"](w)
    assert len(plain) > 8  # confirms this test actually exercises the overflow branch
    narrow_w = w - ip._SCROLLBAR_RESERVED_W
    for line in plain:
        assert ip._display_width(line) <= narrow_w
    for line in colored:
        assert ip._display_width(ip._strip_ansi(line)) <= narrow_w


def test_run_loader_does_not_narrow_an_intentionally_oversized_width(monkeypatch):
    # An oversized `--width` (wider than the terminal) is the documented way to exercise real
    # horizontal scroll (`_run`'s own `configured_width` docstring) -- it must keep wrapping at
    # its own requested width unchanged even when a scrollbar shows, not get silently narrowed
    # the way the full-terminal-width case above does.
    long_doc = "# Title\n\n" + "\n\n".join(
        f"Paragraph {i} with enough words in it to reliably wrap across a wide render width, so "
        f"this document overflows a small terminal height." for i in range(40)
    )
    monkeypatch.setattr(ip.shutil, "get_terminal_size", lambda: os.terminal_size((100, 10)))

    captured = {}

    def fake_run(loader, display_name, *, width, fallback, doc_dir=None, open_path=None):
        captured["loader"] = loader

    monkeypatch.setattr(ip, "_run", fake_run)
    ip.run(long_doc, "test.md", width=200, color=False, toc=False)

    _colored, plain, _headings, _body_start = captured["loader"](200)
    assert len(plain) > 8  # confirms this test actually exercises the overflow branch
    assert max(ip._display_width(line) for line in plain) > 190  # not narrowed


# --- _popup_box --------------------------------------------------------------------------------


def _headings(n):
    return [ip.HeadingLoc(text=f"Heading {i}", level=2, row=i * 10) for i in range(n)]


def test_popup_box_marks_the_selected_row():
    headings = _headings(3)
    box, scroll = ip._popup_box(headings, selected=1, term_w=60, avail_h=20)
    content = box[1:-1]
    assert "▸" in ip._strip_ansi(content[1])
    assert ip._POPUP_SELECTED_BG in content[1]
    assert "▸" not in ip._strip_ansi(content[0])
    assert scroll == 0


def test_popup_box_scrolls_and_shows_indicators_when_too_tall():
    headings = _headings(20)
    avail_h = 8
    max_rows = max(3, avail_h - 2)
    box, scroll = ip._popup_box(headings, selected=10, term_w=60, avail_h=avail_h)
    content = box[1:-1]
    assert len(content) <= max_rows
    joined = "".join(content)
    assert "▲" in joined
    assert "▼" in joined
    assert scroll > 0


def test_popup_box_no_indicators_when_everything_fits():
    headings = _headings(3)
    box, scroll = ip._popup_box(headings, selected=0, term_w=60, avail_h=40)
    joined = "".join(box)
    assert "▲" not in joined
    assert "▼" not in joined
    assert scroll == 0


def test_popup_box_marks_a_hovered_row_distinct_from_selected():
    # VIEWMD-0092: hovering a *different* row than the current selection gets its own,
    # dimmer highlight -- not the selected row's own `_POPUP_SELECTED_BG`.
    headings = _headings(3)
    box, _scroll = ip._popup_box(headings, selected=0, term_w=60, avail_h=20, hover=2)
    content = box[1:-1]
    assert ip._POPUP_HOVER_BG in content[2]
    assert ip._POPUP_SELECTED_BG not in content[2]
    assert ip._POPUP_HOVER_BG not in content[0]  # the selected row itself is untouched by hover


def test_popup_box_selected_row_hover_keeps_selected_styling():
    # Hovering the already-selected row must not demote it to the dimmer hover shade.
    headings = _headings(3)
    box, _scroll = ip._popup_box(headings, selected=1, term_w=60, avail_h=20, hover=1)
    content = box[1:-1]
    assert ip._POPUP_SELECTED_BG in content[1]
    assert ip._POPUP_HOVER_BG not in content[1]


def test_popup_box_no_hover_by_default():
    headings = _headings(3)
    box, _scroll = ip._popup_box(headings, selected=0, term_w=60, avail_h=20)
    assert ip._POPUP_HOVER_BG not in "".join(box)


# --- _overlay ------------------------------------------------------------------------------------


def test_overlay_leaves_untouched_rows_exactly_as_given():
    body = [f"row {i}" for i in range(10)]
    popup = ["┌──┐", "│ok│", "└──┘"]
    out = ip._overlay(body, popup, term_w=20)
    assert out[0] == body[0]
    assert out[-1] == body[-1]


def test_overlay_no_popup_returns_body_unchanged():
    body = ["a", "b"]
    assert ip._overlay(body, [], term_w=20) is body


def test_overlay_does_not_pad_past_real_content():
    # Regression: an earlier version padded touched rows all the way to term_w with literal
    # spaces, painting over the terminal's own background where an erase should have been used.
    body = ["short"] * 5
    popup = ["┌──┐", "│ok│", "└──┘"]
    out = ip._overlay(body, popup, term_w=100)
    box_top = (len(body) - len(popup)) // 2
    row = out[box_top]
    left = (100 - 4) // 2
    tail = ip._strip_ansi(row)[left + 4 :]
    assert tail == body[box_top][left + 4 :]


def test_overlay_margins_come_from_the_real_colored_row():
    # VIEWMD-0102 regression, part 1 (content): a pie chart (VIEWMD-0043) renders a *structurally
    # different* horizontal-bar-chart layout with color off, not a de-colored circle -- so
    # rebuilding the popup's margins from a separately-rendered `color=False` document (as an
    # earlier version of `_overlay` did) spliced unrelated, misaligned bar-chart text into the
    # margins around the box, even on rows the popup never covered. Slicing the real colored row
    # directly (this test's subject) can't drift from itself the way a second render can.
    doc = "```mermaid\npie\n  \"A\" : 70\n  \"B\" : 30\n```\n"
    colored, plain, _headings, _body_start = ip._load(doc, 40, color_kwargs=_KW)
    # Fixture assumption: pie's no-color rendering really is a different layout, not just the same
    # text minus color -- if this ever stops holding, the bug this test guards against can't recur.
    assert plain != [ip._strip_ansi(row) for row in colored]

    popup = ["┌──┐", "│ok│", "└──┘"]
    term_w = 40
    out = ip._overlay(colored, popup, term_w)
    top, left = ip._popup_origin(popup, len(colored), term_w)
    popup_w = max(ip._display_width(ip._strip_ansi(r)) for r in popup)
    for r in range(top, top + len(popup)):
        margin_after = ip._strip_ansi(out[r])[left + popup_w :]
        real_after = ip._strip_ansi(colored[r])[left + popup_w :]
        assert margin_after == real_after


def test_overlay_margins_keep_their_own_color():
    # VIEWMD-0102 regression, part 2 (color): even once the margin *text* matched the real row
    # (part 1 above), an earlier fix still rebuilt margins from a colorless twin (`_strip_ansi` of
    # the colored row) -- correct content, but every popup-adjacent row visibly lost all color,
    # most noticeably on a color-filled diagram like a pie chart where color *is* the content, not
    # just a highlight on top of it. `_ansi_slice` can cut the real colored row directly without
    # that trade-off (reopening/closing whatever SGR span the cut lands inside, the same way
    # `_crop_row`'s horizontal-scroll cropping already relies on it to), so the margins should
    # carry the row's real color, not just its real text.
    row = f"{ip._TRUNCATION_STYLE}" + ("x" * 30) + ip._RESET
    popup = ["┌──┐", "│ok│", "└──┘"]
    term_w = 40
    body = [row] * 10
    out = ip._overlay(body, popup, term_w)
    top, left = ip._popup_origin(popup, len(body), term_w)
    assert left > 0  # a left margin actually exists to check color in
    touched = out[top]
    assert ip._TRUNCATION_STYLE in touched, "margin around the popup lost the row's real color"


# --- _ansi_slice / _crop_row -----------------------------------------------------------------


def test_ansi_slice_plain_text():
    assert ip._ansi_slice("0123456789", 3, 4) == "3456"


def test_ansi_slice_full_width_fast_path_returns_original():
    line = "\x1b[1mhello\x1b[0m"
    assert ip._ansi_slice(line, 0, 100) == line


def test_ansi_slice_never_changes_visible_text_mid_span():
    highlighted = ip._highlight_matches("hello wonderful world", "wonderful")
    assert highlighted is not None
    sliced = ip._ansi_slice(highlighted, 8, 6)
    assert ip._strip_ansi(sliced) == "hello wonderful world"[8:14]
    assert ip._SEARCH_HIGHLIGHT_BG in sliced


def test_ansi_slice_past_end_returns_empty():
    assert ip._ansi_slice("0123456789", 20, 5) == ""


def test_crop_row_no_markers_when_everything_fits():
    row = "short line"
    assert ip._crop_row(row, len(row), left_col=0, width=80) == row


def test_crop_row_right_marker_when_content_extends_past_view():
    row = "x" * 300
    out = ip._crop_row(row, len(row), left_col=0, width=80)
    assert len(ip._strip_ansi(out)) == 80
    assert "‹" not in out
    assert "›" in out


def test_crop_row_left_marker_once_scrolled():
    row = "x" * 300
    out = ip._crop_row(row, len(row), left_col=100, width=80)
    assert len(ip._strip_ansi(out)) == 80
    assert "‹" in out
    assert "›" in out


def test_crop_row_no_right_marker_at_the_true_end():
    row = "x" * 300
    out = ip._crop_row(row, len(row), left_col=220, width=80)
    assert "›" not in out
    assert "‹" in out


def test_max_left_col_no_scroll_needed_when_content_fits():
    assert ip._max_left_col(max_content_width=60, width=80) == 0


def test_max_left_col_reaches_the_rows_true_last_column():
    # VIEWMD-0101: at the max legal `left_col`, `_crop_row` must show the row's real last
    # character -- not stop one column short because the `‹` marker's reserved column at that
    # position was never subtracted out of the cap.
    row = "x" * 300 + "!"  # a distinctive last character to look for
    width = 80
    max_left = ip._max_left_col(max_content_width=len(row), width=width)
    out = ip._crop_row(row, len(row), left_col=max_left, width=width)
    assert "!" in ip._strip_ansi(out)
    assert "›" not in out  # nothing left to scroll to -- no right marker at the true end
    assert "‹" in out  # still scrolled away from the left edge


def test_max_left_col_stays_reachable_by_repeated_stepping():
    # Mirrors the actual wheel-right/`l` call site: repeatedly advancing `left_col` by a step and
    # clamping to `_max_left_col` must still land on a position that reveals the row's true end,
    # not overshoot-and-clamp to something short of it.
    row = "x" * 137 + "END"
    width = 50
    max_left = ip._max_left_col(len(row), width)
    left_col = 0
    for _ in range(20):
        left_col = min(max_left, left_col + 7)
    assert left_col == max_left
    out = ip._crop_row(row, len(row), left_col=left_col, width=width)
    assert "END" in ip._strip_ansi(out)
    assert "›" not in out


def test_crop_row_call_site_uses_the_rows_own_length_not_a_mismatched_twin():
    # Regression: an earlier version decided the right marker using a *different* render's
    # length (some Mermaid diagram types legitimately render different widths with color on vs
    # off, VIEWMD-0043 -- kanban's per-column background fill is a real example) instead of the
    # row actually being displayed, making the marker disappear too early or persist too long.
    # `_crop_row` itself just trusts whatever `plain_len` it's given; this locks down that
    # `draw()`'s call site (mirrored here) passes the row's *own* length, not `plain_lines`'.
    doc = (
        "```mermaid\nkanban\n  Todo\n    a[first]\n    b[second]\n  Done\n    c[third]\n```\n"
    )
    colored, plain, _, _ = ip._load(doc, 40, color_kwargs=_KW)
    divergent = [
        i for i in range(len(colored)) if len(ip._strip_ansi(colored[i])) != len(plain[i])
    ]
    assert divergent, "fixture assumption broken: expected a color/plain width mismatch"
    i = divergent[0]
    row = colored[i]
    own_len = len(ip._strip_ansi(row))
    mismatched_len = len(plain[i])
    assert mismatched_len != own_len
    correct = ip._crop_row(row, own_len, left_col=max(0, own_len - 10), width=80)
    wrong = ip._crop_row(row, mismatched_len, left_col=max(0, own_len - 10), width=80)
    assert "›" not in correct
    assert "›" in wrong


# --- _wrap_hover (VIEWMD-0092) ------------------------------------------------------------------


def test_wrap_hover_wraps_only_the_given_span():
    line = "0123456789"
    out = ip._wrap_hover(line, 3, 6)
    assert ip._strip_ansi(out) == line  # visible text is untouched, just re-styled
    assert f"{ip._HOVER_STYLE}345{ip._RESET}" in out
    assert not out.startswith(ip._HOVER_STYLE)  # prefix ("012") isn't wrapped


def test_wrap_hover_preserves_a_links_own_color_around_the_span():
    line = _first_colored_line("before [a link](B.md) after")
    col = _col_of(line, "a link")
    _href, start, end = ip._link_span_at(line, col)
    out = ip._wrap_hover(line, start, end)
    assert ip._strip_ansi(out) == ip._strip_ansi(line)
    assert ip._HOVER_STYLE in out
    assert ip._RESET in out


def test_wrap_hover_at_the_very_end_of_the_line():
    line = "0123456789"
    out = ip._wrap_hover(line, 8, 10)
    assert ip._strip_ansi(out) == line
    assert f"{ip._HOVER_STYLE}89{ip._RESET}" in out


def test_wrap_hover_survives_an_embedded_reset_mid_span():
    # Regression (found in manual testing): a keycap chip (`_keycap`) closes with its own
    # `_RESET` right after the key, e.g. "w full width" is `_KEYCAP_BG` + "w" + `_RESET` + "
    # full width". That embedded `_RESET` sits inside the wrapped span and must not cancel
    # `_HOVER_STYLE` for the rest of it -- previously only the "w" keycap itself showed reversed,
    # not " full width".
    text, spans = ip._keybind_help(popup_open=False, width_toggle="full width")
    chip = next((s, e) for s, e, invoke in spans if invoke == ip.Event("key", "w"))
    out = ip._wrap_hover(text, *chip)
    assert ip._strip_ansi(out) == ip._strip_ansi(text)
    # Exact expected rendering of the "w full width" chip once wrapped: the keycap's own
    # trailing `_RESET` (right after "w") is immediately followed by another `_HOVER_STYLE`, so
    # reverse video is never actually off anywhere inside the span -- not just "w", but
    # " full width" too.
    expected = (
        f"{ip._HOVER_STYLE}{ip._KEYCAP_BG}w{ip._RESET}{ip._HOVER_STYLE} full width{ip._RESET}"
    )
    assert expected in out


def test_compute_hover_style_matches_any_actionable_chip_not_only_w():
    # Regression (found in manual testing): hovering chips other than "w full width" (e.g. "t
    # contents", "? help", "q quit") never highlighted at all, because the hover-matching branch
    # was hardcoded to only recognize `Event("key", "w")` instead of any chip with a real invoke
    # -- mirrored here against `_chip_at`, the click-side counterpart that was never restricted
    # this way, to pin the fix without needing a live `_run()` session (not unit-testable, see
    # module docstring).
    _text, spans = ip._keybind_help(popup_open=False, has_headings=True)
    t_chip = next((s, e, i) for s, e, i in spans if i == ip.Event("key", "t"))
    start, end, invoke = t_chip
    assert invoke is not None
    assert ip._chip_at(spans, start) == invoke


# --- scrollbar column (VIEWMD-0079) -------------------------------------------------------------


def test_scrollbar_reserved_zero_when_document_fits():
    assert ip._scrollbar_reserved(total_lines=20, body_h=20) == 0
    assert ip._scrollbar_reserved(total_lines=5, body_h=20) == 0


def test_scrollbar_reserved_when_document_overflows():
    assert ip._scrollbar_reserved(total_lines=100, body_h=20) == ip._SCROLLBAR_RESERVED_W
    assert ip._SCROLLBAR_RESERVED_W == 2


def test_scrollbar_thumb_range_at_top():
    start, end = ip._scrollbar_thumb_range(total_lines=100, body_h=20, top=0)
    assert start == 0
    assert end > start


def test_scrollbar_thumb_range_at_bottom():
    max_top = 100 - 20
    start, end = ip._scrollbar_thumb_range(total_lines=100, body_h=20, top=max_top)
    assert end == 20


def test_scrollbar_thumb_range_proportional_midway():
    # Viewing half the document (50/100 rows visible) should occupy roughly half the column.
    start, end = ip._scrollbar_thumb_range(total_lines=100, body_h=50, top=25)
    assert end - start >= 20  # not the whole column, but a substantial chunk
    assert 0 < start < end < 50


def test_scrollbar_thumb_range_never_exceeds_body_h():
    start, end = ip._scrollbar_thumb_range(total_lines=21, body_h=20, top=0)
    assert 0 <= start < end <= 20


def test_scrollbar_prefix_marks_thumb_and_track_distinctly():
    prefix = ip._scrollbar_prefix(total_lines=100, body_h=10, top=0)
    assert len(prefix) == 10
    thumb_start, thumb_end = ip._scrollbar_thumb_range(100, 10, 0)
    for i, cell in enumerate(prefix):
        is_thumb = thumb_start <= i < thumb_end
        glyph = ip._SCROLLBAR_THUMB_GLYPH if is_thumb else ip._SCROLLBAR_TRACK_GLYPH
        assert glyph in cell
        assert "\x1b[" in cell  # colored


# --- _link_at / _resolve_link_target / _content_col (VIEWMD-0076) ------------------------------


def _first_colored_line(text: str, width: int = 80) -> str:
    return ip._load(text, width, color_kwargs=_KW)[0][0]


def _col_of(colored_line: str, substring: str) -> int:
    """Display column of `substring`'s first character in `colored_line` -- walks the same
    tokenizer `_link_at` does rather than trusting `str.index` on raw (escape-laden) text."""
    target = substring[0]
    col = 0
    for tok in ip._ANSI_TOKEN_RE.findall(colored_line):
        if tok.startswith("\x1b"):
            continue
        if tok == target:
            return col
        col += ip._char_width(tok)
    raise AssertionError(f"{substring!r} not found in {colored_line!r}")


def test_link_at_resolves_href_at_a_column_inside_the_link():
    line = _first_colored_line("[a link](B.md) after")
    col = _col_of(line, "a link")
    assert ip._link_at(line, col) == "B.md"


def test_link_at_returns_none_just_past_the_link():
    line = _first_colored_line("[a link](B.md) zzz")
    end_col = _col_of(line, "zzz")
    assert ip._link_at(line, end_col) is None


def test_link_at_returns_none_for_plain_text_with_no_link():
    line = _first_colored_line("just plain text, no links here")
    assert ip._link_at(line, 0) is None


def test_link_at_decodes_a_wikilink_href():
    line = _first_colored_line("[[Target Note]]")
    col = _col_of(line, "Target")
    assert ip._link_at(line, col) == "wikilink:Target Note"


def test_link_at_decodes_a_toc_anchor_href():
    # VIEWMD-0077: the static ToC block's own entries carry a `viewmd-toc:<rank>:<heading text>`
    # href (`viewmd/render.py`'s `_toc_lines()`) -- `_link_at` decodes it the same as any other
    # href, scheme-agnostic; the interactive pager's click dispatch is what treats this scheme
    # specially (resolved by heading text + rank into `top`, never through `_resolve_link_target`).
    kw = {**_KW, "toc": True}
    colored, _plain, _headings, _ = ip._load("# Title\n\n## Section\n", 80, color_kwargs=kw)
    toc_line = next(line for line in colored if "Section" in ip._strip_ansi(line))
    col = _col_of(toc_line, "Section")
    assert ip._link_at(toc_line, col) == f"{ip._TOC_ANCHOR_SCHEME}0:Section"


def test_link_at_decodes_a_toc_anchor_href_with_a_percent_looking_heading():
    # Regression (found in review): _link_at() already fully unquotes an href once -- a click
    # handler that unquotes it a *second* time would corrupt a heading whose text happens to
    # contain a literal '%'-looking substring (e.g. quote()-ing "%41" produces "%2541", and a
    # correct single decode gives back "%41", not a further-decoded "A").
    kw = {**_KW, "toc": True}
    heading_text = "Item %41 Spec"
    colored, _plain, _headings, _ = ip._load(f"# Title\n\n## {heading_text}\n", 80, color_kwargs=kw)
    toc_line = next(line for line in colored if "Item" in ip._strip_ansi(line))
    col = _col_of(toc_line, "Item")
    assert ip._link_at(toc_line, col) == f"{ip._TOC_ANCHOR_SCHEME}0:{heading_text}"


# --- _link_span_at (VIEWMD-0092) ------------------------------------------------------------


def test_link_span_at_resolves_href_and_span_inside_the_link():
    line = _first_colored_line("[a link](B.md) after")
    col = _col_of(line, "a link")
    href, start, end = ip._link_span_at(line, col)
    assert href == "B.md"
    assert start <= col < end
    # Every column across the link's own text resolves to the exact same span -- not just the
    # one column `col_of` happened to land on.
    for c in range(start, end):
        assert ip._link_span_at(line, c) == (href, start, end)


def test_link_span_at_returns_none_just_past_the_link():
    line = _first_colored_line("[a link](B.md) zzz")
    end_col = _col_of(line, "zzz")
    assert ip._link_span_at(line, end_col) is None


def test_link_span_at_returns_none_for_plain_text_with_no_link():
    line = _first_colored_line("just plain text, no links here")
    assert ip._link_span_at(line, 0) is None


def test_link_span_at_span_excludes_neighboring_plain_text():
    line = _first_colored_line("QQQ [a link](B.md) ZZZ")
    col = _col_of(line, "a link")
    _href, start, end = ip._link_span_at(line, col)
    plain = ip._strip_ansi(line)
    assert plain.index("QQQ") < start
    assert end <= plain.index("ZZZ")


def test_resolve_link_target_wikilink_direct_and_recursive(tmp_path):
    (tmp_path / "B.md").write_text("# B\n")
    assert ip._resolve_link_target("wikilink:B", str(tmp_path)) == str(tmp_path / "B.md")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "Nested.md").write_text("# Nested\n")
    assert ip._resolve_link_target("wikilink:Nested", str(tmp_path)) == str(sub / "Nested.md")
    assert ip._resolve_link_target("wikilink:NoSuchDoc", str(tmp_path)) is None


# --- path-qualified wikilink target resolution (VIEWMD-0082) -----------------------------------


def test_resolve_link_target_path_qualified_wikilink_from_vault_root(tmp_path):
    # Already-working case (a path-qualified target resolves directly when current_dir *is* the
    # vault root) -- MUST stay unaffected by the ancestor-walk added for the nested case below.
    sub = tmp_path / "Projects" / "Garden" / "Notes"
    sub.mkdir(parents=True)
    (sub / "_Index.md").write_text("# Notes\n")
    target = "wikilink:Projects/Garden/Notes/_Index"
    assert ip._resolve_link_target(target, str(tmp_path)) == str(sub / "_Index.md")


def test_resolve_link_target_path_qualified_wikilink_from_nested_note(tmp_path):
    # The reported bug: the linking note lives several levels below the vault root (here, inside
    # the very folder the target names), so the target can't be found relative to current_dir
    # directly -- it must be found by walking upward until an ancestor matches.
    sub = tmp_path / "Projects" / "Garden" / "Notes"
    sub.mkdir(parents=True)
    (sub / "_Index.md").write_text("# Notes\n")
    target = "wikilink:Projects/Garden/Notes/_Index"
    assert ip._resolve_link_target(target, str(sub)) == str(sub / "_Index.md")
    deeper = tmp_path / "Projects" / "Garden" / "Notes" / "Seedlings"
    deeper.mkdir()
    assert ip._resolve_link_target(target, str(deeper)) == str(sub / "_Index.md")


def test_resolve_link_target_path_qualified_wikilink_no_match_anywhere(tmp_path):
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert ip._resolve_link_target("wikilink:no/such/note", str(sub)) is None


def test_resolve_link_target_rejects_absolute_path_qualified_wikilink(tmp_path):
    # Regression (found in review): os.path.join(ancestor, target) silently discards `ancestor`
    # for an absolute `target` -- a crafted `[[/etc/passwd|x]]` MUST NOT resolve to any absolute
    # path reachable on disk, the same guard the non-wikilink branch below already has.
    outside = tmp_path.parent / "outside.md"
    outside.write_text("# Outside\n")
    target_without_extension = str(outside)[: -len(".md")]
    href = f"wikilink:{target_without_extension}"
    try:
        assert ip._resolve_link_target(href, str(tmp_path)) is None
    finally:
        outside.unlink()


def test_resolve_link_target_rejects_dotdot_escaping_path_qualified_wikilink(tmp_path):
    outside = tmp_path.parent / "outside.md"
    outside.write_text("# Outside\n")
    try:
        assert ip._resolve_link_target("wikilink:../outside", str(tmp_path)) is None
    finally:
        outside.unlink()


def test_resolve_link_target_bare_wikilink_unaffected_by_ancestor_walk(tmp_path):
    # Requirement 2: a bare (no "/") target's own direct-then-os.walk resolution is unchanged --
    # this exercises the exact scenario the ancestor-walk branch must not intercept.
    (tmp_path / "B.md").write_text("# B\n")
    assert ip._resolve_link_target("wikilink:B", str(tmp_path)) == str(tmp_path / "B.md")


def test_resolve_link_target_relative_markdown_link(tmp_path):
    (tmp_path / "B.md").write_text("# B\n")
    assert ip._resolve_link_target("B.md", str(tmp_path)) == str(tmp_path / "B.md")
    assert ip._resolve_link_target("missing.md", str(tmp_path)) is None


def test_resolve_link_target_rejects_non_md_and_external(tmp_path):
    (tmp_path / "image.png").write_bytes(b"")
    assert ip._resolve_link_target("image.png", str(tmp_path)) is None
    assert ip._resolve_link_target("https://example.com/x", str(tmp_path)) is None
    assert ip._resolve_link_target("mailto:a@b.com", str(tmp_path)) is None


def test_resolve_link_target_rejects_absolute_href(tmp_path):
    # An absolute href isn't "relative to current_dir" -- MUST NOT resolve outside the current
    # document's own directory tree just because a real .md file happens to exist at that
    # absolute path elsewhere on disk (found in review: os.path.join silently discards
    # current_dir for an absolute second argument).
    outside = tmp_path.parent / "outside.md"
    outside.write_text("# Outside\n")
    try:
        assert ip._resolve_link_target(str(outside), str(tmp_path)) is None
    finally:
        outside.unlink()


# --- _resolve_dir_target / directory-listing subdirectory click nav (VIEWMD-0081) --------------


def test_link_at_decodes_a_dir_anchor_href(tmp_path):
    from viewmd.render import render_directory_listing

    (tmp_path / "sub").mkdir()
    colored = render_directory_listing(str(tmp_path), width=80, color=True)
    line = next(line for line in colored.split("\n") if "sub" in ip._strip_ansi(line))
    col = _col_of(line, "sub")
    assert ip._link_at(line, col) == f"{ip._DIR_ANCHOR_SCHEME}sub"


def test_resolve_dir_target_resolves_an_existing_subdirectory(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    assert ip._resolve_dir_target(f"{ip._DIR_ANCHOR_SCHEME}sub", str(tmp_path)) == str(sub)


def test_resolve_dir_target_rejects_a_missing_directory(tmp_path):
    assert ip._resolve_dir_target(f"{ip._DIR_ANCHOR_SCHEME}missing", str(tmp_path)) is None


def test_resolve_dir_target_rejects_a_path_that_is_a_file_not_a_directory(tmp_path):
    (tmp_path / "a.md").write_text("# A\n")
    assert ip._resolve_dir_target(f"{ip._DIR_ANCHOR_SCHEME}a.md", str(tmp_path)) is None


def test_run_directory_listing_wires_doc_dir_and_subdirectory_open_path(monkeypatch, tmp_path):
    # VIEWMD-0081: `run_directory_listing()` now passes `doc_dir`/`open_path` to `_run()` (just
    # like `run()` does for a `.md` file) so a click on a subdirectory row can navigate into it --
    # this exercises that wiring directly, at the level `_run`'s own click-to-follow logic (itself
    # untested end-to-end, see VIEWMD-0076's tests above) is invoked at, without needing a real
    # tty/event loop.
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.md").write_text("# Nested\n")

    captured = {}

    def fake_run(loader, display_name, *, width, fallback, doc_dir=None, open_path=None):
        captured["doc_dir"] = doc_dir
        captured["open_path"] = open_path

    monkeypatch.setattr(ip, "_run", fake_run)
    # `width` (document default) and `directory_width` (listing default) deliberately differ so a
    # subdirectory target's returned default width (VIEWMD-0089) can be told apart from a
    # document's -- a subdirectory row should get `directory_width` back, not `width`.
    ip.run_directory_listing(str(tmp_path), width=80, directory_width=120, color=False)

    assert captured["doc_dir"] == str(tmp_path)
    new_loader, new_display_name, new_doc_dir, new_default_width = captured["open_path"](str(sub))
    assert new_display_name == "sub/"
    assert new_doc_dir == str(sub)
    assert new_default_width == 120
    colored, _plain, headings, body_start = new_loader(80)
    assert any("nested.md" in ip._strip_ansi(line) for line in colored)
    assert headings == []
    assert body_start == 0


def test_run_directory_listing_depth_carries_over_into_a_navigated_subdirectory(
    monkeypatch, tmp_path
):
    # VIEWMD-0089: a listing shown with `--depth 2` still shows two levels of a subdirectory's
    # own children after clicking into it, the same way `width`/`color` already carry over
    # unchanged rather than resetting to the `depth=1` default.
    sub = tmp_path / "sub"
    sub.mkdir()
    deeper = sub / "deeper"
    deeper.mkdir()
    (deeper / "deepest.md").write_text("# Deepest\n")

    captured = {}

    def fake_run(loader, display_name, *, width, fallback, doc_dir=None, open_path=None):
        captured["open_path"] = open_path

    monkeypatch.setattr(ip, "_run", fake_run)
    ip.run_directory_listing(str(tmp_path), width=80, directory_width=80, color=False, depth=2)

    new_loader, _new_display_name, _new_doc_dir, _new_default_width = captured["open_path"](
        str(sub)
    )
    colored, _plain, _headings, _body_start = new_loader(80)
    assert any("deepest.md" in ip._strip_ansi(line) for line in colored)


def test_run_directory_listing_loader_narrows_for_scrollbar_when_listing_overflows(
    monkeypatch, tmp_path
):
    # Bug found in manual maintainer testing: `render_directory_listing`'s table used to be
    # rendered at the *full* width `w` inside `make_loader`, with no way to know yet whether
    # `_run` would end up reserving `_SCROLLBAR_RESERVED_W` columns for a scrollbar (VIEWMD-0079)
    # -- once there were enough rows to trigger one, `draw()`'s crop silently truncated the
    # table's own right border/rightmost column on every single row (a `›` marker on every
    # line). `make_loader` now checks the rendered line count against the terminal's available
    # body height and, if it overflows, re-renders at `w - _SCROLLBAR_RESERVED_W` so the table
    # already fits the space the scrollbar will actually leave.
    for i in range(30):
        (tmp_path / f"file-{i:02d}.md").write_text(f"# File {i}\n")

    # A small terminal (`lines=10` -> `body_h = 10 - 2 = 8`) so 30 files' worth of rows overflow.
    monkeypatch.setattr(
        ip.shutil, "get_terminal_size", lambda: os.terminal_size((100, 10))
    )

    captured = {}

    def fake_run(loader, display_name, *, width, fallback, doc_dir=None, open_path=None):
        captured["loader"] = loader

    monkeypatch.setattr(ip, "_run", fake_run)
    ip.run_directory_listing(str(tmp_path), width=100, directory_width=100, color=False)

    w = 100
    colored, plain, _headings, _body_start = captured["loader"](w)
    assert len(plain) > 8  # confirms this test actually exercises the overflow branch
    narrow_w = w - ip._SCROLLBAR_RESERVED_W
    for line in plain:
        assert ip._display_width(line) <= narrow_w
    for line in colored:
        assert ip._display_width(ip._strip_ansi(line)) <= narrow_w


# --- .md file rows clickable in the directory listing (VIEWMD-0093) -----------------------------


def test_link_at_decodes_a_directory_listing_file_href(tmp_path):
    from viewmd.render import render_directory_listing

    (tmp_path / "a file.md").write_text("# A\n")
    colored = render_directory_listing(str(tmp_path), width=80, color=True)
    line = next(line for line in colored.split("\n") if "a file.md" in ip._strip_ansi(line))
    col = _col_of(line, "a file.md")
    assert ip._link_at(line, col) == "a file.md"


def test_resolve_link_target_resolves_a_directory_listing_file_href(tmp_path):
    # Unlike a subdirectory row's `_DIR_ANCHOR_SCHEME`-tagged href, a file row's href is a plain
    # (percent-encoded, already-unquoted-by-`_link_at`) relative path -- it resolves through the
    # same `_resolve_link_target` an ordinary in-document link uses, per the issue's design notes.
    (tmp_path / "a.md").write_text("# A\n")
    assert ip._resolve_link_target("a.md", str(tmp_path)) == str(tmp_path / "a.md")


def test_run_directory_listing_open_path_opens_an_md_file(monkeypatch, tmp_path):
    # VIEWMD-0093: `run_directory_listing()`'s `open_path` now dispatches to opening a document
    # (not a nested listing) when handed a `.md` file target, the same shape `run()`'s own
    # `open_path` returns for a clicked in-document link.
    (tmp_path / "a.md").write_text("# A\n\nBody text.\n")

    captured = {}

    def fake_run(loader, display_name, *, width, fallback, doc_dir=None, open_path=None):
        captured["open_path"] = open_path

    monkeypatch.setattr(ip, "_run", fake_run)
    # `width` (document default) and `directory_width` (listing default) deliberately differ, the
    # same way they do in real usage when `--width` is omitted (VIEWMD-0089) -- a `.md` file
    # target must get `width` back, not `directory_width`.
    ip.run_directory_listing(str(tmp_path), width=80, directory_width=200, color=False)

    opened = captured["open_path"](str(tmp_path / "a.md"))
    assert opened is not None
    new_loader, new_display_name, new_doc_dir, new_default_width = opened
    assert new_display_name == "a.md"
    assert new_doc_dir == str(tmp_path)
    assert new_default_width == 80
    colored, _plain, headings, _body_start = new_loader(80)
    assert any("Body text." in ip._strip_ansi(line) for line in colored)
    assert len(headings) == 1


def test_run_directory_listing_open_path_returns_none_for_unreadable_file(monkeypatch, tmp_path):
    captured = {}

    def fake_run(loader, display_name, *, width, fallback, doc_dir=None, open_path=None):
        captured["open_path"] = open_path

    monkeypatch.setattr(ip, "_run", fake_run)
    ip.run_directory_listing(str(tmp_path), width=80, directory_width=80, color=False)

    # Never written -- resolved and then removed/never-existed by the time open_path runs, the
    # same race `run()`'s own open_path guards against (VIEWMD-0076).
    assert captured["open_path"](str(tmp_path / "missing.md")) is None


# --- width-reset-on-navigation bug (VIEWMD-0089, per maintainer's manual testing) --------------
#
# Opening a directory listing with no explicit --width defaults its own table to the full
# terminal width (VIEWMD-0071's `directory_width`), while a plain `.md` file defaults to a
# narrower, prose-readability-capped width. Before this fix, `_run`'s `configured_width` was set
# once at the top of the session and never updated on navigation -- so a `.md` file clicked open
# from inside a directory listing kept inheriting the *listing's* full-width baseline instead of
# getting its own default, and going back with 'B' would then apply whatever width was active at
# that moment rather than restoring the width the target being returned to actually used. These
# tests drive the real event loop (via a pipe standing in for /dev/tty, the same technique
# `_run_pager_with_input` above uses for `run()`) rather than only checking `open_path`'s return
# value in isolation, so they also cover `_run`'s own click-dispatch/`nav_stack` wiring, not just
# the contract `open_path` promises to satisfy.


def _run_dir_pager_with_input(
    monkeypatch, dir_path: str, data: bytes, *, term_size, width, directory_width, depth=1
) -> None:
    """Drive `run_directory_listing()` against a pipe standing in for `/dev/tty`, feeding `data`
    as the pager's input -- the `run_directory_listing()` analogue of `_run_pager_with_input`
    above."""
    r, w = os.pipe()
    os.write(w, data)
    os.close(w)
    pager_fd = os.dup(r)

    real_open = ip.os.open

    def fake_open(path, flags, *args, **kwargs):
        if path == "/dev/tty":
            return pager_fd
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(ip.os, "open", fake_open)
    monkeypatch.setattr(ip.termios, "tcgetattr", lambda fd: [0, 0, 0, 0, 0, 0, [0] * 32])
    monkeypatch.setattr(ip.termios, "tcsetattr", lambda fd, when, mode: None)
    monkeypatch.setattr(ip.tty, "setcbreak", lambda fd: None)
    monkeypatch.setattr(
        ip.shutil, "get_terminal_size", lambda *a, **k: os.terminal_size(term_size)
    )

    ip.run_directory_listing(
        dir_path, width=width, directory_width=directory_width, color=False, depth=depth
    )
    os.close(r)


def _click_bytes(col: int, row: int) -> bytes:
    """A press+release SGR mouse-click pair at 1-indexed screen column/row -- the same encoding
    `test_echo_area_click_quit_consumes_paired_sgr_release` above uses."""
    press = f"\x1b[<0;{col};{row}M".encode()
    release = f"\x1b[<0;{col};{row}m".encode()
    return press + release


def test_navigating_into_a_file_from_a_directory_listing_uses_the_files_own_default_width(
    monkeypatch, tmp_path
):
    # The exact bug scenario: `--width` omitted, so `directory_width` (the listing's own default,
    # full terminal width) and `width` (a document's own default, prose-capped) genuinely differ
    # -- clicking a `.md` file row must render it at `width`, not `directory_width`.
    (tmp_path / "note.md").write_text("# Note\n\nbody text.\n")
    term_w, term_h = 200, 24
    directory_width, doc_width = 200, 100

    from viewmd.render import render_directory_listing

    colored = render_directory_listing(str(tmp_path), width=directory_width, color=True).rstrip(
        "\n"
    ).split("\n")
    line_no = next(i for i, line in enumerate(colored) if "note.md" in ip._strip_ansi(line))
    col = _col_of(colored[line_no], "note.md") + 1  # 1-indexed SGR column
    row = line_no + 1  # 1-indexed SGR row (top == 0, so doc_row == body_row)

    load_calls: list[int] = []
    real_load = ip._load

    def spy_load(text, w, *, color_kwargs):
        load_calls.append(w)
        return real_load(text, w, color_kwargs=color_kwargs)

    monkeypatch.setattr(ip, "_load", spy_load)

    _run_dir_pager_with_input(
        monkeypatch,
        str(tmp_path),
        _click_bytes(col, row) + b"q",
        term_size=(term_w, term_h),
        width=doc_width,
        directory_width=directory_width,
    )

    assert load_calls == [doc_width]


def test_going_back_from_a_navigated_file_restores_the_listings_own_width(monkeypatch, tmp_path):
    (tmp_path / "note.md").write_text("# Note\n\nbody text.\n")
    term_w, term_h = 200, 24
    directory_width, doc_width = 200, 100

    from viewmd.render import render_directory_listing

    colored = render_directory_listing(str(tmp_path), width=directory_width, color=True).rstrip(
        "\n"
    ).split("\n")
    line_no = next(i for i, line in enumerate(colored) if "note.md" in ip._strip_ansi(line))
    col = _col_of(colored[line_no], "note.md") + 1
    row = line_no + 1

    import viewmd.render as render_mod

    render_calls: list[int] = []
    real_render = render_mod.render_directory_listing

    def spy_render(d, *, width, color, depth=1, theme="dark"):
        render_calls.append(width)
        return real_render(d, width=width, color=color, depth=depth, theme=theme)

    # `run_directory_listing()`'s `make_loader` does `from viewmd.render import
    # render_directory_listing` *inside* the function body on every call, so it always resolves
    # against `viewmd.render`'s own module attribute at call time -- patching that module
    # attribute (not any name on `ip`, which never binds it at module scope) is what's needed for
    # the spy to actually intercept it.
    monkeypatch.setattr(render_mod, "render_directory_listing", spy_render)

    _run_dir_pager_with_input(
        monkeypatch,
        str(tmp_path),
        _click_bytes(col, row) + b"Bq",
        term_size=(term_w, term_h),
        width=doc_width,
        directory_width=directory_width,
    )

    # The listing is re-rendered (colored + plain twin) once up front and once more on 'B' going
    # back to it -- every one of those calls must be at `directory_width`, never the document's
    # `doc_width` that was briefly `configured_width` while the file was open.
    assert len(render_calls) >= 2
    assert all(w == directory_width for w in render_calls)


def test_navigating_into_a_file_with_explicit_width_is_unchanged(monkeypatch, tmp_path):
    # No visible behavior change when --width was explicitly passed: `width` and `directory_width`
    # already come out equal in that case (viewmd/__main__.py), so this locks in that a future
    # regression here (e.g. `width`/`directory_width` accidentally diverging when both were
    # supplied explicitly) would be caught.
    (tmp_path / "note.md").write_text("# Note\n\nbody text.\n")
    term_w, term_h = 200, 24
    same_width = 80

    from viewmd.render import render_directory_listing

    colored = render_directory_listing(str(tmp_path), width=same_width, color=True).rstrip(
        "\n"
    ).split("\n")
    line_no = next(i for i, line in enumerate(colored) if "note.md" in ip._strip_ansi(line))
    col = _col_of(colored[line_no], "note.md") + 1
    row = line_no + 1

    load_calls: list[int] = []
    real_load = ip._load

    def spy_load(text, w, *, color_kwargs):
        load_calls.append(w)
        return real_load(text, w, color_kwargs=color_kwargs)

    monkeypatch.setattr(ip, "_load", spy_load)

    _run_dir_pager_with_input(
        monkeypatch,
        str(tmp_path),
        _click_bytes(col, row) + b"q",
        term_size=(term_w, term_h),
        width=same_width,
        directory_width=same_width,
    )

    assert load_calls == [same_width]


def test_content_col_maps_through_no_scroll():
    # No truncation markers reserved -- screen column is content column, unchanged.
    assert ip._content_col(plain_len=40, left_col=0, width=80, screen_col=5) == 5


def test_content_col_none_on_left_truncation_marker():
    assert ip._content_col(plain_len=200, left_col=10, width=80, screen_col=0) is None
    assert ip._content_col(plain_len=200, left_col=10, width=80, screen_col=1) == 10


def test_content_col_none_on_right_truncation_marker():
    # plain_len > left_col + width -- a right marker is reserved at the last screen column.
    assert ip._content_col(plain_len=200, left_col=0, width=80, screen_col=79) is None
    assert ip._content_col(plain_len=200, left_col=0, width=80, screen_col=78) == 78


# --- _popup_origin / _popup_hit (VIEWMD-0076) ---------------------------------------------------


def _box(n_content_rows: int, width: int = 10) -> list[str]:
    top = "┌" + "─" * width + "┐"
    bottom = "└" + "─" * width + "┘"
    return [top] + [f"│{'x' * width}│" for _ in range(n_content_rows)] + [bottom]


def test_popup_hit_content_row_inside_box():
    popup = _box(3)
    top, left = ip._popup_origin(popup, body_h=20, term_w=40)
    assert ip._popup_hit(popup, body_h=20, term_w=40, col0=left, row0=top + 2) == 1


def test_popup_hit_none_on_border_row():
    popup = _box(3)
    top, left = ip._popup_origin(popup, body_h=20, term_w=40)
    assert ip._popup_hit(popup, body_h=20, term_w=40, col0=left, row0=top) is None
    assert ip._popup_hit(popup, body_h=20, term_w=40, col0=left, row0=top + 4) is None


def test_popup_hit_none_outside_box_columns():
    popup = _box(3)
    top, left = ip._popup_origin(popup, body_h=20, term_w=40)
    assert ip._popup_hit(popup, body_h=20, term_w=40, col0=0, row0=top + 1) is None


def test_popup_hit_none_for_empty_popup():
    assert ip._popup_hit([], body_h=20, term_w=40, col0=5, row0=5) is None


# --- _read_event ---------------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_sgr_unread():
    ip._unread.clear()
    yield
    ip._unread.clear()


def _pipe_with(data: bytes) -> int:
    r, w = os.pipe()
    os.write(w, data)
    os.close(w)
    return r


def _run_pager_with_input(
    monkeypatch,
    data: bytes | None = None,
    *,
    term_size=(80, 24),
    width=80,
    text="# Hi\n\nbody\n",
    name="file.md",
    chunks: list[bytes] | None = None,
) -> bytes:
    """Drive `run()` against a pipe standing in for `/dev/tty`, feeding `data` as the pager's
    input. Returns whatever bytes were still unread on that pipe after `run()` returned --
    VIEWMD-0094's leak is exactly those leftover SGR-release bytes.

    `name` (VIEWMD-0090) defaults to the bare, non-existent "file.md" every pre-existing caller
    here relies on -- `run()` only needs it as a display name/`doc_dir` source, never actually
    reads it, so a name with no real file backing it is fine for anything that doesn't click a
    link. A click-to-follow test passes a real on-disk path instead, since `open_path` (VIEWMD-
    0076) does actually open whatever a click resolves to.

    `chunks` (VIEWMD-0090), when given instead of `data`, is written to the pipe from a
    background thread with a short real sleep between each chunk, rather than all of `data`
    up front. `_drain_paired_sgr_release` (VIEWMD-0094) greedily reads *everything* currently
    queued on the fd looking for a click's own paired release -- fine for a single click, where
    at most one real following keystroke can possibly already be queued, but a second scripted
    click's whole press+release (and everything after it) sitting in the pipe from the start
    would get swept into that first drain's leftover-bytes buffer too, then have nothing left on
    the raw fd for the second click's own drain call to find (found while developing this test's
    two-navigation sequence: manifested as a spurious empty `Event('key', '')` and an extra
    redraw right after the second click). A real terminal session never has this problem --
    keystrokes arrive as the reader actually presses them, never all buffered at once before the
    session even starts -- so `chunks` exists to make this harness behave the same way for a
    multi-click script, without touching the drain logic itself (out of this issue's scope)."""
    r, w = os.pipe()
    if chunks is not None:

        def feed() -> None:
            for chunk in chunks:
                os.write(w, chunk)
                time.sleep(0.15)
            os.close(w)

        threading.Thread(target=feed, daemon=True).start()
    else:
        os.write(w, data)
        os.close(w)
    pager_fd = os.dup(r)

    real_open = ip.os.open

    def fake_open(path, flags, *args, **kwargs):
        if path == "/dev/tty":
            return pager_fd
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(ip.os, "open", fake_open)
    monkeypatch.setattr(ip.termios, "tcgetattr", lambda fd: [0, 0, 0, 0, 0, 0, [0] * 32])
    monkeypatch.setattr(ip.termios, "tcsetattr", lambda fd, when, mode: None)
    monkeypatch.setattr(ip.tty, "setcbreak", lambda fd: None)
    monkeypatch.setattr(
        ip.shutil, "get_terminal_size", lambda *a, **k: os.terminal_size(term_size)
    )

    ip.run(text, name, width=width, color=False)

    leftover = os.read(r, 64)
    os.close(r)
    return leftover


def test_read_event_plain_key():
    fd = _pipe_with(b"a")
    assert ip._read_event(fd) == ip.Event("key", "a")


def test_read_event_backspace_variants():
    for data in (b"\x7f", b"\x08"):
        fd = _pipe_with(data)
        assert ip._read_event(fd) == ip.Event("key", "backspace")


def test_read_event_arrow_keys():
    cases = {b"\x1b[A": "up", b"\x1b[B": "down", b"\x1b[C": "right", b"\x1b[D": "left"}
    for data, value in cases.items():
        fd = _pipe_with(data)
        assert ip._read_event(fd) == ip.Event("key", value)


def test_read_event_bare_esc():
    fd = _pipe_with(b"\x1b")
    assert ip._read_event(fd) == ip.Event("key", "esc")


def test_read_event_sgr_mouse_wheel():
    fd = _pipe_with(b"\x1b[<64;10;5M")
    assert ip._read_event(fd) == ip.Event("wheel_up")
    fd = _pipe_with(b"\x1b[<65;10;5M")
    assert ip._read_event(fd) == ip.Event("wheel_down")


def test_read_event_sgr_mouse_horizontal_wheel():
    fd = _pipe_with(b"\x1b[<66;10;5M")
    assert ip._read_event(fd) == ip.Event("wheel_left")
    fd = _pipe_with(b"\x1b[<67;10;5M")
    assert ip._read_event(fd) == ip.Event("wheel_right")


def test_read_event_sgr_mouse_shift_wheel_falls_back_to_horizontal():
    # Terminals with no native horizontal-wheel report (e.g. macOS Terminal.app) send Shift +
    # vertical wheel instead (SGR adds 4 for a held Shift: 64+4=68, 65+4=69) -- the same
    # shift-scrolls-horizontally convention other GUI apps fall back to.
    fd = _pipe_with(b"\x1b[<68;10;5M")
    assert ip._read_event(fd) == ip.Event("wheel_left")
    fd = _pipe_with(b"\x1b[<69;10;5M")
    assert ip._read_event(fd) == ip.Event("wheel_right")


def test_read_event_sgr_mouse_click_press():
    fd = _pipe_with(b"\x1b[<0;15;7M")
    assert ip._read_event(fd) == ip.Event("click", col=15, row=7)


def test_read_event_sgr_mouse_click_press_drains_paired_release():
    # VIEWMD-0094: a physical click is press then release; one `_read_event` call must consume
    # both so a click that quits the pager doesn't leave `\x1b[<0;Cx;Cym` for the shell to echo.
    fd = _pipe_with(b"\x1b[<0;69;46M\x1b[<0;69;46m")
    assert ip._read_event(fd) == ip.Event("click", col=69, row=46)
    leftover = os.read(fd, 64)
    os.close(fd)
    assert leftover == b""
    assert not ip._unread


def test_read_event_sgr_mouse_click_press_does_not_consume_a_following_key():
    # Requirement 3: a click that does *not* quit must not swallow the next real key -- the
    # drain only takes the paired release, and anything after it is pushed back.
    fd = _pipe_with(b"\x1b[<0;15;7M\x1b[<0;15;7mx")
    assert ip._read_event(fd) == ip.Event("click", col=15, row=7)
    assert ip._read_event(fd) == ip.Event("key", "x")
    os.close(fd)


def test_read_event_sgr_mouse_click_release_is_ignored():
    # The release ('m', not 'M') isn't a click -- VIEWMD-0076 only acts on the press.
    fd = _pipe_with(b"\x1b[<0;15;7m")
    ev = ip._read_event(fd)
    assert ev.kind != "click"


def test_read_event_sgr_mouse_modifier_click_is_ignored():
    # A modifier-click (Ctrl/Alt/Shift + left button) is out of scope (VIEWMD-0076 Non-goals) --
    # SGR encodes those as `btn` values other than the bare 0 a plain left-click press reports.
    fd = _pipe_with(b"\x1b[<4;15;7M")  # Shift + left-click
    ev = ip._read_event(fd)
    assert ev.kind != "click"


def test_echo_area_click_quit_consumes_paired_sgr_release(monkeypatch):
    # VIEWMD-0094: clicking the echo-area `q quit` chip (press + its paired release on the
    # input fd) must consume the release before the pager returns, not leave it for the shell.
    term_w, term_h = 80, 24
    body_h = term_h - 2
    _text, spans = ip._keybind_help(False, None, False, has_headings=True)
    q_start, _, invoke = next(s for s in spans if s[2] == ip.Event("key", "q"))
    assert invoke == ip.Event("key", "q")
    col = q_start + 1  # 1-indexed SGR Cx, inside the chip
    row = body_h + 2  # 1-indexed SGR Cy of the echo area
    press = f"\x1b[<0;{col};{row}M".encode()
    release = f"\x1b[<0;{col};{row}m".encode()
    leftover = _run_pager_with_input(
        monkeypatch, press + release, term_size=(term_w, term_h), width=term_w
    )
    assert leftover == b""
    assert not ip._unread


def test_help_screen_click_quit_consumes_paired_sgr_release(monkeypatch):
    # Same leak, via the `?` help screen's `q  quit` row (the originally reported path).
    # term_h=40 is tall enough that the q row is in the un-scrolled help window.
    term_w, term_h = 80, 40
    body_h = term_h - 2
    box, invokes = ip._help_box(term_w, max(3, body_h - 2), 0)
    q_hit = next(i for i, inv in enumerate(invokes) if inv == ip.Event("key", "q"))
    top, left = ip._popup_origin(box, body_h, term_w)
    col0, row0 = left + 2, top + 1 + q_hit
    assert ip._popup_hit(box, body_h, term_w, col0, row0) == q_hit
    col, row = col0 + 1, row0 + 1
    press = f"\x1b[<0;{col};{row}M".encode()
    release = f"\x1b[<0;{col};{row}m".encode()
    leftover = _run_pager_with_input(
        monkeypatch, b"?" + press + release, term_size=(term_w, term_h), width=term_w
    )
    assert leftover == b""
    assert not ip._unread


def test_non_quit_click_then_key_in_same_burst_is_not_stalled(monkeypatch):
    # Independent review: `_drain_paired_sgr_release` can push a following key into `_unread`,
    # and the main loop used to `select` only on the tty fd -- so `q` sitting in `_unread`
    # after a non-quit click (document body, not a chip) would never be read. Press+release+`q`
    # in one burst must still quit.
    leftover = _run_pager_with_input(
        monkeypatch, b"\x1b[<0;1;1M\x1b[<0;1;1mq", term_size=(80, 24), width=80
    )
    assert leftover == b""
    assert not ip._unread


def test_read_event_sgr_mouse_motion_no_button(monkeypatch):
    # VIEWMD-0092: xterm's own "motion, no button pressed" encoding is 32+3=35 -- confirmed
    # empirically in macOS Terminal.app (see the issue's Design notes) as the report a bare mouse
    # move (no click) produces once motion tracking (1003) is enabled.
    fd = _pipe_with(b"\x1b[<35;15;7M")
    assert ip._read_event(fd) == ip.Event("motion", col=15, row=7)


def test_read_event_sgr_mouse_motion_with_button_held_is_still_motion():
    # A drag (button held while moving) sets the same bit-32 motion flag, just with the held
    # button's own low bits instead of 3 ("no button") -- still a "motion" event here, since
    # this issue is about where the cursor currently sits, not whether a button happens to be
    # down while it gets there.
    fd = _pipe_with(b"\x1b[<32;15;7M")  # button 0 (left) held + moving
    assert ip._read_event(fd) == ip.Event("motion", col=15, row=7)


def test_read_event_sgr_mouse_motion_does_not_collide_with_wheel_or_click():
    # Regression guard for the bit-32 check's own reasoning comment: wheel codes (64-69) and a
    # plain click (0) must still parse exactly as before now that a motion branch sits between
    # them in `_read_event`.
    fd = _pipe_with(b"\x1b[<64;10;5M")
    assert ip._read_event(fd) == ip.Event("wheel_up")
    fd = _pipe_with(b"\x1b[<0;15;7M")
    assert ip._read_event(fd) == ip.Event("click", col=15, row=7)


# --- _mode_line ------------------------------------------------------------------------------


def test_mode_line_shows_top_bot_and_percent():
    assert "Top" in ip._mode_line("f.md", 100, 0, 10, term_w=80)
    assert "Bot" in ip._mode_line("f.md", 100, 90, 100, term_w=80)
    assert "50%" in ip._mode_line("f.md", 100, 40, 50, term_w=80)


def test_mode_line_shows_col_marker_when_scrolled_horizontally():
    line = ip._mode_line("f.md", 100, 0, 10, term_w=80, left_col=42)
    assert "col 43" in line


def test_mode_line_no_col_marker_at_left_col_zero():
    assert "col" not in ip._mode_line("f.md", 100, 0, 10, term_w=80, left_col=0)


def test_mode_line_always_exactly_term_w_wide():
    for term_w in (20, 60, 200):
        line = ip._mode_line("f.md", 100, 0, 10, term_w=term_w, section="A Section")
        assert len(ip._strip_ansi(line)) == term_w or len(line) == term_w


def test_mode_line_truncates_a_too_long_section_with_ellipsis():
    long_heading = "A" * 500
    line = ip._mode_line("f.md", 100, 0, 10, term_w=60, section=long_heading)
    assert len(line) == 60
    assert long_heading not in line
    assert "…" in line


def test_mode_line_drops_section_when_no_room_at_all():
    long_heading = "A" * 500
    line = ip._mode_line("f.md", 100, 0, 10, term_w=20, section=long_heading)
    assert len(line) == 20


# --- _keybind_help / _pad_ansi --------------------------------------------------------------


def test_keybind_help_fits_comfortably_and_stays_colored():
    for popup_open in (False, True):
        line, _spans = ip._keybind_help(popup_open, "full width", True)
        assert len(ip._strip_ansi(line)) <= 90
        assert ip._KEYCAP_BG in line


def test_keybind_help_omits_width_toggle_and_highlight_hints_when_not_applicable():
    line, _spans = ip._keybind_help(False, None, False)
    assert "full width" not in ip._strip_ansi(line)
    assert "clear hl" not in ip._strip_ansi(line)


def test_keybind_help_omits_contents_hint_without_headings():
    # VIEWMD-0072: a directory listing/multi-file view has no heading outline, so 't' is inert --
    # not advertised in the echo-area default hint.
    line, _spans = ip._keybind_help(False, None, False, has_headings=False)
    assert "contents" not in ip._strip_ansi(line)


def test_keybind_help_shows_contents_hint_with_headings_by_default():
    line, _spans = ip._keybind_help(False, None, False)
    assert "contents" in ip._strip_ansi(line)


def test_keybind_help_omits_prev_file_hint_before_any_navigation():
    line, _spans = ip._keybind_help(False, None, False)
    plain = ip._strip_ansi(line)
    assert "back (" not in plain
    assert "fwd (" not in plain


def test_keybind_help_shows_back_hint_with_trail_depth_once_back_count_is_positive():
    # VIEWMD-0076: 'b' is only advertised once there's actually something to go back to;
    # VIEWMD-0090 extends this to a full stack, so the hint's label carries the depth
    # (requirement 6 -- a discoverable trail position) rather than just "yes/no".
    line, _spans = ip._keybind_help(False, None, False, back_count=2)
    assert "back (2)" in ip._strip_ansi(line)


def test_keybind_help_omits_forward_hint_with_nothing_ahead():
    line, _spans = ip._keybind_help(False, None, False, back_count=1)
    assert "fwd (" not in ip._strip_ansi(line)


def test_keybind_help_shows_forward_hint_with_trail_depth_once_forward_count_is_positive():
    # VIEWMD-0090 requirement 3/6: 'f' is only advertised once there's somewhere to go forward
    # to, and its label carries the depth the same way the back hint's does.
    line, _spans = ip._keybind_help(False, None, False, forward_count=3)
    assert "fwd (3)" in ip._strip_ansi(line)


# --- _keybind_help spans / _chip_at (VIEWMD-0078) -------------------------------------------


def test_keybind_help_every_chip_has_a_resolvable_span():
    # Requirement 2/acceptance: every chip `_keybind_help()` can render, in both layouts, has a
    # span that covers at least one column and doesn't overlap its neighbors.
    for popup_open in (False, True):
        for width_toggle, highlight_active, has_headings, back_count, forward_count in (
            (None, False, True, 0, 0),
            ("full width", True, True, 1, 2),
            (None, False, False, 0, 0),
        ):
            _text, spans = ip._keybind_help(
                popup_open,
                width_toggle,
                highlight_active,
                has_headings=has_headings,
                back_count=back_count,
                forward_count=forward_count,
            )
            assert spans
            prev_end = 0
            for start, end, _invoke in spans:
                assert start >= prev_end
                assert end > start
                prev_end = end


def test_keybind_help_base_layout_chip_invokes_match_their_key():
    _text, spans = ip._keybind_help(
        False, "full width", True, has_headings=True, back_count=1, forward_count=1
    )
    invokes = {inv.value: inv for _s, _e, inv in spans if inv is not None}
    assert invokes["/"] == ip.Event("key", "/")
    assert invokes["t"] == ip.Event("key", "t")
    assert invokes["b"] == ip.Event("key", "b")
    assert invokes["f"] == ip.Event("key", "f")
    assert invokes["w"] == ip.Event("key", "w")
    assert invokes["esc"] == ip.Event("key", "esc")
    assert invokes["?"] == ip.Event("key", "?")
    assert invokes["q"] == ip.Event("key", "q")
    # "scroll" (up/down,wheel) has no single unambiguous direction, same as its `_HELP_GROUPS`
    # row -- its span is the first one and carries no invoke.
    assert spans[0][2] is None


def test_keybind_help_popup_layout_chips_have_no_ambiguous_invoke():
    # `up/down,wheel,j/k` (which direction?) and `Enter` (confirms whichever heading happens to
    # be `popup_selected`, not something a synthesized event alone can carry) stay genuinely
    # ambiguous -- but `Esc/t cancel` and the trailing `q quit` both have one unambiguous outcome
    # regardless of which listed key does it (VIEWMD-0092 follow-up: `Esc/t cancel` was wrongly
    # grouped with the truly-ambiguous chips here, which is why it was inert to both hover and
    # click while a ToC popup was open).
    _text, spans = ip._keybind_help(True)
    invokes = [invoke for _start, _end, invoke in spans]
    assert invokes[:2] == [None, None]
    assert invokes[2] == ip.Event("key", "esc")
    assert invokes[-1] == ip.Event("key", "q")


def test_keybind_help_help_layout_close_chip_has_an_invoke():
    # VIEWMD-0092 follow-up: the help-screen echo hint used to be a hardcoded plain string with
    # no chip structure at all, so "Esc/?/q close help" was inert to both hover and click; now
    # routed through the same `_keybind_help`/`_render_chips` machinery every other layout uses.
    text, spans = ip._keybind_help(False, help_open=True)
    assert "scroll" in ip._strip_ansi(text)
    assert "close help" in ip._strip_ansi(text)
    invokes = [invoke for _start, _end, invoke in spans]
    assert invokes[0] is None  # up/down,wheel,j/k: scroll -- direction-ambiguous
    assert invokes[1] == ip.Event("key", "esc")


def test_chip_at_resolves_column_to_the_right_chip():
    text, spans = ip._keybind_help(False, None, False, has_headings=True)
    plain = ip._strip_ansi(text)
    t_col = plain.index("t contents")
    assert ip._chip_at(spans, t_col) == ip.Event("key", "t")
    q_col = plain.rindex("q quit")
    assert ip._chip_at(spans, q_col) == ip.Event("key", "q")


def test_chip_at_resolves_the_popup_cancel_and_quit_chips():
    text, spans = ip._keybind_help(True)
    plain = ip._strip_ansi(text)
    cancel_col = plain.index("Esc/t cancel")
    assert ip._chip_at(spans, cancel_col) == ip.Event("key", "esc")
    q_col = plain.rindex("q quit")
    assert ip._chip_at(spans, q_col) == ip.Event("key", "q")
    # The still-ambiguous chips resolve to no invoke at all.
    move_col = plain.index("move")
    assert ip._chip_at(spans, move_col) is None


def test_chip_at_resolves_the_help_screen_close_chip():
    text, spans = ip._keybind_help(False, help_open=True)
    plain = ip._strip_ansi(text)
    close_col = plain.index("close help")
    assert ip._chip_at(spans, close_col) == ip.Event("key", "esc")


def test_chip_at_returns_none_between_chips_and_out_of_range():
    text, spans = ip._keybind_help(False, None, False, has_headings=True)
    plain = ip._strip_ansi(text)
    assert ip._chip_at(spans, -1) is None
    assert ip._chip_at(spans, len(plain) + 5) is None
    # The two literal spaces joining every pair of chips fall in no span.
    gap_col = spans[0][1]
    assert plain[gap_col] == " "
    assert ip._chip_at(spans, gap_col) is None


def test_pad_ansi_pads_with_plain_trailing_spaces():
    colored = ip._keycap("q")
    padded = ip._pad_ansi(colored, 20)
    assert len(padded) == len(colored) + (20 - len(ip._strip_ansi(colored)))
    assert padded.endswith(" ")


def test_pad_ansi_falls_back_to_plain_text_when_truncating():
    colored = ip._keycap("q") + " quit"
    truncated = ip._pad_ansi(colored, 3)
    assert truncated == ip._strip_ansi(colored)[:3]


# --- _help_box -----------------------------------------------------------------------------------


def test_help_box_contains_every_group_and_key():
    box, invokes = ip._help_box(term_w=100, avail_h=40)
    text = "\n".join(ip._strip_ansi(row) for row in box)
    for group_name, entries in ip._HELP_GROUPS:
        assert group_name in text
        for key, _, _ in entries:
            assert key in text
    assert len(invokes) == len(box) - 2


def test_help_box_never_exceeds_the_given_width():
    box, _invokes = ip._help_box(term_w=100, avail_h=40)
    assert all(len(ip._strip_ansi(row)) <= 100 for row in box)


def test_help_box_has_a_blank_row_above_every_header_but_the_first():
    box, _invokes = ip._help_box(term_w=100, avail_h=40)
    for i, (group_name, _) in enumerate(ip._HELP_GROUPS):
        header_i = next(j for j, row in enumerate(box) if group_name in row)
        prev_inner = ip._strip_ansi(box[header_i - 1]).strip("│").strip()
        if i > 0:
            assert prev_inner == ""


def test_help_box_headers_and_keys_are_styled():
    box, _invokes = ip._help_box(term_w=100, avail_h=40)
    header_hits = sum(row.count(ip._HELP_HEADER_STYLE) for row in box)
    key_hits = sum(row.count(ip._HELP_KEY_STYLE) for row in box)
    assert header_hits == len(ip._HELP_GROUPS)
    assert key_hits == sum(len(entries) for _, entries in ip._HELP_GROUPS)


def test_help_box_invokes_align_with_entries_that_have_one_unambiguous_action():
    box, invokes = ip._help_box(term_w=100, avail_h=40)
    non_none = [inv for inv in invokes if inv is not None]
    total_entries_with_invoke = sum(
        1 for _, entries in ip._HELP_GROUPS for _, _, inv in entries if inv is not None
    )
    assert len(non_none) == total_entries_with_invoke
    assert all(isinstance(inv, ip.Event) for inv in non_none)


def test_help_box_scrolls_with_indicators_when_too_tall():
    full, _full_invokes = ip._help_box(term_w=100, avail_h=40)
    short, short_invokes = ip._help_box(term_w=100, avail_h=12, scroll=0)
    assert len(short) < len(full)
    assert len(short_invokes) == len(short) - 2
    assert "▼" in "".join(short)
    assert "▲" not in "".join(short)
    end, _end_invokes = ip._help_box(term_w=100, avail_h=12, scroll=1000)
    assert "▲" in "".join(end)
    assert "▼" not in "".join(end)


def test_help_box_marks_a_hovered_actionable_row():
    box, invokes = ip._help_box(term_w=100, avail_h=40)
    hover_i = next(i for i, inv in enumerate(invokes) if inv is not None)
    hovered_box, _hovered_invokes = ip._help_box(term_w=100, avail_h=40, hover=hover_i)
    assert ip._POPUP_HOVER_BG in hovered_box[1 + hover_i]
    # No other row picks up the hover styling.
    assert sum(1 for row in hovered_box if ip._POPUP_HOVER_BG in row) == 1


def test_help_box_does_not_highlight_a_non_actionable_hovered_row():
    # A header/blank/tip row (invoke is None) is a click no-op -- hovering it must not imply
    # otherwise (requirement 2's "MUST NOT ... imply a target is clickable" reasoning, applied to
    # the help table the same way `_help_box`'s own docstring states for the hover param).
    box, invokes = ip._help_box(term_w=100, avail_h=40)
    hover_i = next(i for i, inv in enumerate(invokes) if inv is None)
    hovered_box, _hovered_invokes = ip._help_box(term_w=100, avail_h=40, hover=hover_i)
    assert ip._POPUP_HOVER_BG not in "".join(hovered_box)


def test_help_box_no_hover_by_default():
    box, _invokes = ip._help_box(term_w=100, avail_h=40)
    assert ip._POPUP_HOVER_BG not in "".join(box)


def test_help_box_never_fills_the_full_body_edge_to_edge():
    # Regression: the popup must always leave at least one row of real document visible above
    # and below it -- callers pass `avail_h = max(3, body_h - 2)`, not the full body height.
    full, _full_invokes = ip._help_box(term_w=100, avail_h=40)
    body_h = len(full)
    body_rows = [f"document line {i}" for i in range(body_h)]
    capped, _capped_invokes = ip._help_box(term_w=100, avail_h=max(3, body_h - 2))
    overlaid = ip._overlay(body_rows, capped, term_w=100)
    assert "┌" not in ip._strip_ansi(overlaid[0])
    assert "└" not in ip._strip_ansi(overlaid[-1])


# --- _search ---------------------------------------------------------------------------------


def test_search_finds_next_match_forward():
    lines = ["alpha", "beta", "gamma", "beta again"]
    assert ip._search(lines, "beta", start_after=0) == 1


def test_search_wraps_around_to_the_top():
    lines = ["alpha", "beta", "gamma"]
    assert ip._search(lines, "alpha", start_after=1) == 0


def test_search_case_insensitive():
    lines = ["Hello World"]
    assert ip._search(lines, "hello", start_after=-1) == 0


def test_search_returns_none_when_not_found():
    assert ip._search(["a", "b"], "zzz", start_after=-1) is None


def test_search_empty_query_returns_none():
    assert ip._search(["a", "b"], "", start_after=-1) is None


# --- mouse toggle constants -----------------------------------------------------------------


def test_mouse_on_off_are_a_real_enable_disable_pair():
    assert ip._MOUSE_ON != ip._MOUSE_OFF
    assert "1000h" in ip._MOUSE_ON
    assert "1000l" in ip._MOUSE_OFF


def test_mouse_on_off_enable_motion_tracking_too():
    # VIEWMD-0092 requirement 1: motion tracking (1003) is layered onto the same on/off toggle as
    # click reporting (1000) and SGR coordinates (1006) -- 'm' (see `_dispatch_base`) turning
    # mouse capture off must also stop motion reports, not just clicks/wheel, so there's no stray
    # hover highlighting while the reader has deliberately dropped out of mouse capture to select
    # text natively.
    assert "1003h" in ip._MOUSE_ON
    assert "1003l" in ip._MOUSE_OFF


# --- wide characters (VIEWMD-0070) ------------------------------------------------------------

# Rich's own placeholder glyph for an unrenderable image (`![alt](src)`) -- the exact character
# that surfaced this bug live, real double-width content rather than a synthetic fixture.
_WIDE = "🌆"


def test_display_width_counts_a_wide_character_as_two():
    assert ip._display_width(_WIDE) == 2
    assert ip._display_width("a") == 1
    assert ip._char_width(_WIDE) == 2


def test_wc_ljust_pads_by_display_width_not_character_count():
    padded = ip._wc_ljust(f"{_WIDE} demo", 10)
    assert ip._display_width(padded) == 10
    assert len(padded) < 10  # fewer characters than columns, since the emoji is 2 columns/1 char


def test_ansi_slice_wide_character_fully_inside_window():
    line = f"ab{_WIDE}cd"
    out = ip._ansi_slice(line, 0, 6)
    assert out == line
    assert ip._display_width(out) == 6


def test_ansi_slice_pads_a_wide_character_straddling_the_right_edge():
    line = f"ab{_WIDE}cd"  # columns: a=0 b=1 [wide]=2-3 c=4 d=5
    out = ip._ansi_slice(line, 0, 3)  # window [0, 3) cuts the wide char in half
    assert ip._display_width(out) == 3
    assert out == "ab "  # half the glyph can't render -- padded with a space instead


def test_ansi_slice_pads_a_wide_character_straddling_the_left_edge():
    line = f"ab{_WIDE}cd"
    out = ip._ansi_slice(line, 3, 3)  # window starts inside the wide char's own column span
    assert ip._display_width(out) == 3
    assert out == " cd"


def test_crop_row_total_width_unaffected_by_a_wide_character():
    row = f"{_WIDE} " + "x" * 100
    plain_len = ip._display_width(row)
    for left_col in (0, 1, 2, 50):
        out = ip._crop_row(row, plain_len, left_col=left_col, width=20)
        assert ip._display_width(ip._strip_ansi(out)) == 20


def test_overlay_stays_column_aligned_around_a_wide_character():
    # Regression: README.md's own "🌆 viewmd demo" image-placeholder line threw off the help
    # popup's left border in a real terminal -- character-index splicing landed one column short
    # of where display-column splicing should have cut.
    body = [f"{_WIDE} viewmd demo" + " " * 88] * 5  # a 100-col-wide row with a wide char at col 0
    popup = ["┌────┐", "│ ok │", "└────┘"]
    out = ip._overlay(body, popup, term_w=100)
    popup_w = max(ip._display_width(row) for row in popup)
    left = max(0, (100 - popup_w) // 2)
    box_top = (len(body) - len(popup)) // 2
    row = ip._strip_ansi(out[box_top])
    # The popup's own left border must land at display column `left`, not character index
    # `left` -- with a width-2 character at column 0, those differ by one.
    assert ip._display_width(row[: row.index("┌")]) == left
    assert ip._display_width(row) == 100


def test_popup_box_sizes_itself_for_a_heading_containing_a_wide_character():
    headings = [ip.HeadingLoc(text=f"{_WIDE} Section", level=2, row=0)]
    box, _scroll = ip._popup_box(headings, selected=0, term_w=60, avail_h=20)
    widths = {ip._display_width(ip._strip_ansi(row)) for row in box}
    assert len(widths) == 1  # every row, borders included, is exactly the same display width


def test_mode_line_section_with_a_wide_character_stays_exactly_term_w():
    for term_w in (20, 40, 80):
        line = ip._mode_line("f.md", 100, 0, 10, term_w=term_w, section=f"{_WIDE} Intro")
        assert ip._display_width(line) == term_w


# --- run(): non-terminal fallback -------------------------------------------------------------


def test_run_falls_back_to_plain_print_without_a_controlling_terminal(monkeypatch, capsys):
    from viewmd.render import render_markdown

    def fake_open(path, flags):
        raise OSError("no controlling terminal")

    monkeypatch.setattr(ip.os, "open", fake_open)
    text = "# Hello\n\nbody\n"
    ip.run(text, "file.md", width=80, color=False)
    out = capsys.readouterr().out
    assert out == render_markdown(text, width=80, color=False)


def test_run_reads_input_from_dev_tty_not_stdin(monkeypatch):
    # VIEWMD-0007: input piped via stdin (`cat file.md | viewmd -`) must not break keyboard
    # control -- the interactive loop reads from /dev/tty explicitly, never `sys.stdin`, since
    # stdin may be an already-drained pipe with nothing left to read.
    opened = []
    real_open = ip.os.open

    def fake_open(path, flags):
        opened.append(path)
        if path == "/dev/tty":
            raise OSError("no /dev/tty available in this test sandbox")
        return real_open(path, flags)

    monkeypatch.setattr(ip.os, "open", fake_open)
    ip.run("# Hello\n", "-", width=80, color=False)
    assert opened == ["/dev/tty"]


# --- run_directory_listing()/run_multi_file(): non-terminal fallback (VIEWMD-0072) ------------


def test_run_directory_listing_falls_back_to_plain_print(monkeypatch, capsys, tmp_path):
    from viewmd.render import render_directory_listing

    (tmp_path / "a.md").write_text("# A\n")

    def fake_open(path, flags):
        raise OSError("no controlling terminal")

    monkeypatch.setattr(ip.os, "open", fake_open)
    ip.run_directory_listing(str(tmp_path), width=80, directory_width=80, color=False)
    out = capsys.readouterr().out
    assert out == render_directory_listing(str(tmp_path), width=80, color=False)


def test_run_multi_file_loader_narrows_directory_width_for_scrollbar_when_overflowing(
    monkeypatch, tmp_path
):
    # Same two-pass scrollbar problem as `run_directory_listing`, applied to a bare directory
    # listing embedded among a multi-file concatenation's entries: `directory_width` is a fixed
    # full-terminal-width value that doesn't shrink for the 'w' toggle, so if the whole
    # concatenation ends up tall enough to need a scrollbar, the embedded listing's own table
    # (rendered at the un-reduced `directory_width`) would get silently cropped by `draw()` the
    # same way. `run_multi_file`'s loader now re-renders at `directory_width -
    # _SCROLLBAR_RESERVED_W` once it detects the whole thing overflows the body.
    for i in range(30):
        (tmp_path / f"file-{i:02d}.md").write_text(f"# File {i}\n")
    entries = [(str(tmp_path), None)]

    monkeypatch.setattr(
        ip.shutil, "get_terminal_size", lambda: os.terminal_size((100, 10))
    )

    captured = {}

    def fake_run(loader, display_name, *, width, fallback):
        captured["loader"] = loader

    monkeypatch.setattr(ip, "_run", fake_run)
    ip.run_multi_file(entries, width=100, directory_width=100, color=False,
                      full_front_matter=False, toc=True)

    w = 100
    colored, plain, _headings, _body_start = captured["loader"](w)
    assert len(plain) > 8  # confirms this test actually exercises the overflow branch
    narrow_w = w - ip._SCROLLBAR_RESERVED_W
    # Only the embedded directory-listing table's own rows are under test here (its own file
    # heading line above it is a long absolute `tmp_path`, unrelated pre-existing overflow with
    # nothing to do with the scrollbar-cropping bug this test targets).
    table_plain = [line for line in plain if line[:1] in "│╭├╰"]
    table_colored = [line for line in colored if ip._strip_ansi(line)[:1] in "│╭├╰"]
    assert table_plain
    for line in table_plain:
        assert ip._display_width(line) <= narrow_w
    for line in table_colored:
        assert ip._display_width(ip._strip_ansi(line)) <= narrow_w


def test_run_multi_file_falls_back_to_plain_print(monkeypatch, capsys):
    from viewmd.render import render_multi_file

    def fake_open(path, flags):
        raise OSError("no controlling terminal")

    monkeypatch.setattr(ip.os, "open", fake_open)
    entries = [("a.md", "# A\n"), ("b.md", "# B\n")]
    ip.run_multi_file(entries, width=80, directory_width=80, color=False,
                      full_front_matter=False, toc=True)
    out = capsys.readouterr().out
    assert out == render_multi_file(entries, width=80, directory_width=80, color=False,
                                    full_front_matter=False, toc=True)


# --- Multi-level b/f trail (VIEWMD-0090) --------------------------------------------------


def _sgr_click(col: int, row: int) -> bytes:
    """A plain left-click press + its paired release, 1-indexed SGR mouse-report coordinates --
    same shape every other click-driven test in this file sends."""
    press = f"\x1b[<0;{col};{row}M".encode()
    release = f"\x1b[<0;{col};{row}m".encode()
    return press + release


def test_multilevel_back_and_forward_walk_a_three_document_trail(monkeypatch, capsys, tmp_path):
    # VIEWMD-0090 acceptance: a three-hop link-following sequence (A -> B -> C), back-back
    # returns to the origin (A), forward-forward re-reaches the final hop (C), and each
    # document's own scroll position -- not just its home position -- is restored exactly on
    # both directions. Driven through the real `_run()` event loop (via a pipe standing in for
    # `/dev/tty`, `_run_pager_with_input`), since click-to-follow's own scroll-restoration math
    # only lives inside that loop's closures, not in any separately-testable helper.
    width = 80
    term_size = (width, 24)
    body_h = term_size[1] - 2

    def make_doc(label: str, link_target: str | None) -> str:
        # A single tight list, one item per source line -- deliberately not blank-line-separated
        # paragraphs, so each item is exactly one rendered row with no interleaved blank rows to
        # account for (found while developing this test: paragraph-per-line content renders with
        # an unpredictable number of blank divider rows between items, depending on Rich's own
        # Markdown wrapping, which would make every row index below a guess rather than a fact).
        items = []
        for i in range(60):
            if link_target is not None and i == 20:
                items.append(f"- [NEXT]({link_target})")
            else:
                items.append(f"- {label} filler {i}")
        return f"# {label}\n\n" + "\n".join(items) + "\n"

    text_a = make_doc("A", "b.md")
    text_b = make_doc("B", "c.md")
    text_c = make_doc("C", None)
    a_path = tmp_path / "a.md"
    a_path.write_text(text_a)
    (tmp_path / "b.md").write_text(text_b)
    (tmp_path / "c.md").write_text(text_c)

    def row_of(plain_lines: list[str], marker: str) -> int:
        return next(i for i, line in enumerate(plain_lines) if marker in line)

    # `ip.run()` itself defaults to `toc=True` -- matched here rather than reusing plain `_KW`
    # (toc=False), even though a single-heading doc makes no practical difference (a ToC block
    # only renders with >= 2 headings, `render.py`'s own `render_markdown`), so this test's row
    # math is never relying on that incidental equivalence.
    kw = {**_KW, "toc": True}
    colored_a, plain_a, _h, _bs = ip._load(text_a, width, color_kwargs=kw)
    colored_b, plain_b, _h, _bs = ip._load(text_b, width, color_kwargs=kw)
    _colored_c, plain_c, _h, _bs = ip._load(text_c, width, color_kwargs=kw)

    link_row_a = row_of(plain_a, "NEXT")
    link_row_b = row_of(plain_b, "NEXT")
    # Scrolled a few rows short of the link, not all the way to it or left at the top -- proves
    # the exact scroll position (not just "somewhere"/"the top") survives the round trip.
    top_a, top_b, top_c = link_row_a - 3, link_row_b - 3, 9
    # The link's own screen row after scrolling to `top_*` -- must stay on-screen (0 <= . < body_h)
    # for the click below to actually land on it.
    assert 0 <= link_row_a - top_a < body_h
    assert 0 <= link_row_b - top_b < body_h
    expect_a, expect_b, expect_c = plain_a[top_a], plain_b[top_b], plain_c[top_c]
    # Guards the test itself against a vacuous pass: an empty/blank expected row would make the
    # substring check below trivially true regardless of what the pager actually restored.
    assert expect_a.strip() and expect_b.strip() and expect_c.strip()

    # The scrollbar-plus-gap column (VIEWMD-0079) is reserved to the left of every body row
    # whenever the document doesn't fit in one screen -- true for all three here (60-item
    # lists) -- so a click's screen column has to account for it, same as `_run`'s own click
    # handling does when mapping a screen column back to a content column.
    reserved = ip._scrollbar_reserved(len(colored_a), body_h)
    assert reserved == ip._scrollbar_reserved(len(colored_b), body_h)
    col_a = reserved + _col_of(colored_a[link_row_a], "NEXT")
    col_b = reserved + _col_of(colored_b[link_row_b], "NEXT")

    # Split around the two navigating clicks (`chunks`, not one plain `data` blob) -- two real
    # clicks in one script needs the paced delivery `_run_pager_with_input`'s own docstring
    # explains, or the second click's paired-release drain finds nothing left to drain.
    chunks = [
        b"j" * top_a + _sgr_click(col_a + 1, (link_row_a - top_a) + 1),  # A -> B
        b"j" * top_b + _sgr_click(col_b + 1, (link_row_b - top_b) + 1),  # B -> C
        b"j" * top_c + b"bb" + b"ff" + b"q",  # C -> B -> A -> B -> C, then quit
    ]

    _run_pager_with_input(
        monkeypatch, chunks=chunks, term_size=term_size, width=width, text=text_a, name=str(a_path)
    )
    out = capsys.readouterr().out
    frames = out.split(ip._HOME)[1:]

    def first_body_row(frame: str) -> str:
        return ip._strip_ansi(frame.split("\n", 1)[0])

    # Event order -> frame index: 0 is the initial draw; each subsequent key/click event (never
    # a "motion" event here) produces exactly one more, in order (see `_run`'s main loop -- every
    # branch reaches its own `draw()` call at the bottom before the next event is read).
    n_scroll_a, n_scroll_b, n_scroll_c = top_a, top_b, top_c
    idx_after_click_to_c = n_scroll_a + 1 + n_scroll_b + 1  # two clicks: A->B, B->C
    idx_back_to_b = idx_after_click_to_c + n_scroll_c + 1
    idx_back_to_a = idx_back_to_b + 1
    idx_fwd_to_b = idx_back_to_a + 1
    idx_fwd_to_c = idx_fwd_to_b + 1
    assert len(frames) == idx_fwd_to_c + 1

    assert expect_c.strip() in first_body_row(frames[idx_after_click_to_c + n_scroll_c])
    # Back, back: C -> B (B's own saved scroll) -> A (A's own saved scroll, the origin).
    assert expect_b.strip() in first_body_row(frames[idx_back_to_b])
    assert expect_a.strip() in first_body_row(frames[idx_back_to_a])
    # Forward, forward: A -> B (redone) -> C, each landing back at its own saved scroll position,
    # not just the top of the document -- the final hop is exactly where it was left.
    assert expect_b.strip() in first_body_row(frames[idx_fwd_to_b])
    assert expect_c.strip() in first_body_row(frames[idx_fwd_to_c])


def test_forward_is_a_no_op_with_nothing_ahead(monkeypatch, capsys, tmp_path):
    # VIEWMD-0090 requirement 3: 'f' with nothing on the forward stack (no 'b' yet pressed, or
    # after a fresh navigation has discarded it) is inert, same as 'b' already is at the start of
    # a session -- an echo-area message, not a crash or an unexplained no-op.
    (tmp_path / "a.md").write_text("# A\n")
    data = b"f" + b"q"
    _run_pager_with_input(
        monkeypatch, data, text="# A\n", name=str(tmp_path / "a.md")
    )
    out = capsys.readouterr().out
    assert "No next file to go forward to" in ip._strip_ansi(out)


def test_new_navigation_clears_the_forward_stack(monkeypatch, capsys, tmp_path):
    # VIEWMD-0090 design decision: following a new link after backing up discards whatever was
    # ahead on the trail (the same rule a browser's own forward history follows) -- 'f' must not
    # resurrect a document the reader has since navigated away from through a different link.
    text_a = "# A\n\n[to B](b.md)\n"
    text_c = "# C\n\nonly C\n"
    (tmp_path / "a.md").write_text(text_a)
    (tmp_path / "b.md").write_text("# B\n\n[to C](c.md)\n")
    (tmp_path / "c.md").write_text(text_c)

    colored, plain, _h, _bs = ip._load(text_a, 80, color_kwargs={**_KW, "toc": True})
    link_row = next(i for i, line in enumerate(plain) if "to B" in line)
    col = _col_of(colored[link_row], "to B")
    row = link_row + 1  # 1-indexed screen row, top == 0

    # Split around the two navigating clicks (see `_run_pager_with_input`'s own docstring for
    # why: the second click's paired-release drain finds nothing left to drain otherwise, once
    # everything is available on the pipe from the very start).
    chunks = [
        _sgr_click(col + 1, row),  # A -> B
        b"b",  # B -> A (now something to go forward to)
        _sgr_click(col + 1, row),  # A -> B again, a *new* navigation
        b"f" + b"q",  # nothing ahead any more -- must be inert
    ]
    _run_pager_with_input(monkeypatch, chunks=chunks, text=text_a, name=str(tmp_path / "a.md"))
    out = capsys.readouterr().out
    assert "No next file to go forward to" in ip._strip_ansi(out)


# --- page-back-up key remap (maintainer review, VIEWMD-0090) --------------------------------
#
# The maintainer asked for lowercase 'b'/'f' as the trail keys instead of 'B'/'F', which
# collided with lowercase 'b' already meaning "page back up" (the standard `less`-style
# binding). Resolution (maintainer's explicit call): drop 'b' from page-back-up entirely,
# leaving only '-'/Backspace for it, freeing 'b' for trail-back.


def test_page_back_up_still_works_via_dash_and_backspace(monkeypatch, capsys):
    # '-' and Backspace must still page back up exactly as before the remap.
    term_size = (80, 24)
    text = "# Doc\n\n" + "\n".join(f"- line {i}" for i in range(200)) + "\n"

    def first_body_row(frame: str) -> str:
        return ip._strip_ansi(frame.split("\n", 1)[0])

    for key in (b"-", b"\x7f"):  # '-' and Backspace (DEL)
        data = b" " + key + b"q"  # page down, then page back up, then quit
        _run_pager_with_input(monkeypatch, data, term_size=term_size, width=80, text=text)
        out = capsys.readouterr().out
        frames = out.split(ip._HOME)[1:]
        assert len(frames) == 3
        after_page_down = first_body_row(frames[1])
        after_page_back = first_body_row(frames[2])
        # Paging down then back up returns to the same first body row it started from.
        assert after_page_back == first_body_row(frames[0])
        assert after_page_down != after_page_back


def test_lowercase_b_alone_no_longer_pages_back_up(monkeypatch, capsys):
    # Lowercase 'b' is now the trail-back key, not page-back-up -- with an empty history stack
    # it must be an inert no-op (an echo-area message), never scrolling the viewport at all.
    term_size = (80, 24)
    text = "# Doc\n\n" + "\n".join(f"- line {i}" for i in range(200)) + "\n"

    def first_body_row(frame: str) -> str:
        return ip._strip_ansi(frame.split("\n", 1)[0])

    data = b" " + b"b" + b"q"  # page down, then 'b' (no trail to go back to), then quit
    _run_pager_with_input(monkeypatch, data, term_size=term_size, width=80, text=text)
    out = capsys.readouterr().out
    frames = out.split(ip._HOME)[1:]
    assert len(frames) == 3
    after_page_down = first_body_row(frames[1])
    after_b = first_body_row(frames[2])
    # 'b' left the viewport exactly where it was -- no page-back-up happened.
    assert after_b == after_page_down
    assert "No previous file to go back to" in ip._strip_ansi(out)


if __name__ == "__main__":
    pytest.main([str(pathlib.Path(__file__))])
