"""Unit tests for the gantt chart parser (VIEWMD-0032).

No upstream reference implementation to differentially test against
(mermaid-ascii has no gantt support) -- hand-written directly against
Mermaid's own gantt syntax, same posture as the pie/quadrant/packet/kanban
parsers' own tests.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from viewmd.mermaid.gantt.parser import ParseError, parse, sniff


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("gantt\ntitle x\n", True),
        ("GANTT\ntitle x\n", True),
        ("---\ntitle: T\n---\ngantt\ntitle x\n", True),
        ("ganttFoo\ntitle x\n", False),  # whole-token match, not a prefix
        ("pie\n\"A\":1", False),
        ("erDiagram\nA\n", False),
        ("", False),
    ],
)
def test_sniff(source, expected):
    assert sniff(source) == expected


def test_title_and_date_format():
    d = parse("gantt\ntitle My Chart\ndateFormat YYYY-MM-DD\nsection S\n  A :a1, 2024-01-01, 3d\n")
    assert d.title == "My Chart"
    assert d.tasks[0].start == datetime(2024, 1, 1)


def test_parse_tolerates_leading_front_matter():
    d = parse(
        "---\ntitle: Ignored\n---\ngantt\ntitle My Chart\ndateFormat YYYY-MM-DD\n"
        "section S\n  A :a1, 2024-01-01, 3d\n"
    )
    assert d.title == "My Chart"
    assert d.tasks[0].start == datetime(2024, 1, 1)


def test_unsupported_date_format_is_a_parse_error():
    with pytest.raises(ParseError):
        parse("gantt\ndateFormat DD/MM/YYYY\nsection S\n  A :a1, 01/01/2024, 3d\n")


def test_section_grouping():
    d = parse(
        "gantt\n"
        "section One\n  A :a1, 2024-01-01, 2d\n  B :b1, 2024-01-03, 2d\n"
        "section Two\n  C :c1, 2024-01-05, 2d\n"
    )
    assert [t.section for t in d.tasks] == ["One", "One", "Two"]


def test_explicit_start_date():
    d = parse("gantt\nsection S\n  A :a1, 2024-03-01, 5d\n")
    assert d.tasks[0].start == datetime(2024, 3, 1)
    assert d.tasks[0].end == datetime(2024, 3, 6)


def test_after_id_reference():
    d = parse("gantt\nsection S\n  A :a1, 2024-01-01, 5d\n  B :after a1, 3d\n")
    assert d.tasks[1].start == d.tasks[0].end == datetime(2024, 1, 6)
    assert d.tasks[1].end == datetime(2024, 1, 9)


def test_until_id_reference_with_duration():
    d = parse(
        "gantt\nsection S\n"
        "  A :a1, 2024-01-10, 2d\n"
        "  B :until a1, 3d\n"
    )
    # B's end is bound to A's start (2024-01-10); its own start is 3d before that.
    assert d.tasks[1].end == datetime(2024, 1, 10)
    assert d.tasks[1].start == datetime(2024, 1, 7)


def test_until_id_reference_forward_declared():
    """D2's `Add to mermaid :until isadded` references a task declared on
    the *next* line -- the parser must resolve forward references, not just
    lean on declaration order."""
    d = parse(
        "gantt\nsection S\n"
        "  Prior task    :p1, 2024-01-01, 5d\n"
        "  Add to mermaid :until later\n"
        "  Later task     :milestone, later, 2024-01-20, 0d\n"
    )
    add_task = d.tasks[1]
    later_task = d.tasks[2]
    assert add_task.end == later_task.start == datetime(2024, 1, 20)
    assert add_task.start == d.tasks[0].end  # requirement 4a: implicit continuation


def test_implicit_continuation_default_requirement_4a():
    d = parse(
        "gantt\nsection S\n"
        "  A :a1, 2024-01-01, 5d\n"
        "  B :3d\n"  # no start, no id -- continues from A's end
    )
    assert d.tasks[1].start == d.tasks[0].end == datetime(2024, 1, 6)
    assert d.tasks[1].end == datetime(2024, 1, 9)


def test_implicit_continuation_crosses_sections():
    """D1's `another task` continues from `Task in Another`'s end even
    though a new `section` line sits in between -- 4a is diagram-global, not
    per-section."""
    d = parse(
        "gantt\nsection One\n  A :a1, 2024-01-01, 5d\nsection Two\n  B :3d\n"
    )
    assert d.tasks[1].start == d.tasks[0].end


def test_duration_units_day_week_hour():
    d = parse(
        "gantt\nsection S\n"
        "  A :a1, 2024-01-01, 2w\n"
        "  B :b1, after a1, 3d\n"
        "  C :c1, after b1, 24h\n"
    )
    assert d.tasks[0].end == datetime(2024, 1, 15)  # 2 weeks = 14 days
    assert d.tasks[1].end == datetime(2024, 1, 18)
    assert d.tasks[2].end == datetime(2024, 1, 19)  # 24h == exactly 1 day


def test_explicit_end_date_instead_of_duration():
    d = parse("gantt\nsection S\n  A :a1, 2024-01-01, 2024-01-10\n")
    assert d.tasks[0].end == datetime(2024, 1, 10)


def test_id_reused_across_sections_resolves_to_most_recent_requirement_4b():
    d = parse(
        "gantt\n"
        "section One\n  A :a1, 2024-01-01, 5d\n"
        "section Two\n  A :a1, 2024-02-01, 2d\n"
        "section Three\n  B :after a1, 1d\n"
    )
    # B's `after a1` must resolve to the *second* a1 (section Two), not the first.
    assert d.tasks[2].start == d.tasks[1].end == datetime(2024, 2, 3)


def test_excludes_weekends_skips_saturday_and_sunday():
    # 2024-01-05 is a Friday; +3d business days should land on Wed 2024-01-10,
    # skipping the 2024-01-06/07 weekend.
    d = parse(
        "gantt\nexcludes weekends\nsection S\n  A :a1, 2024-01-05, 3d\n"
    )
    assert d.tasks[0].end == datetime(2024, 1, 10)


def test_excludes_weekends_absent_uses_plain_calendar_math():
    d = parse("gantt\nsection S\n  A :a1, 2024-01-05, 3d\n")
    assert d.tasks[0].end == datetime(2024, 1, 8)


def test_unsupported_excludes_value_is_a_parse_error():
    with pytest.raises(ParseError):
        parse("gantt\nexcludes monday\nsection S\n  A :a1, 2024-01-01, 3d\n")


@pytest.mark.parametrize(
    ("tag_line", "flag"),
    [
        ("done, a1, 2024-01-01, 3d", "done"),
        ("active, a1, 2024-01-01, 3d", "active"),
        ("milestone, a1, 2024-01-01, 0d", "milestone"),
        ("crit, a1, 2024-01-01, 3d", "crit"),
    ],
)
def test_single_status_tags(tag_line, flag):
    d = parse(f"gantt\nsection S\n  A :{tag_line}\n")
    t = d.tasks[0]
    assert getattr(t, flag) is True
    others = {"done", "active", "milestone", "crit"} - {flag}
    assert not any(getattr(t, o) for o in others)


def test_untagged_task_has_no_status_flags():
    d = parse("gantt\nsection S\n  A :a1, 2024-01-01, 3d\n")
    t = d.tasks[0]
    assert not (t.done or t.active or t.crit or t.milestone)


@pytest.mark.parametrize("combo", ["crit, done", "crit, active"])
def test_crit_combined_with_done_or_active(combo):
    d = parse(f"gantt\nsection S\n  A :{combo}, a1, 2024-01-01, 3d\n")
    t = d.tasks[0]
    assert t.crit is True
    assert (t.done if "done" in combo else t.active) is True


def test_missing_colon_is_a_parse_error():
    with pytest.raises(ParseError):
        parse("gantt\nsection S\n  A a1, 2024-01-01, 3d\n")


def test_unknown_id_reference_is_a_parse_error():
    with pytest.raises(ParseError):
        parse("gantt\nsection S\n  A :after nope, 3d\n")


def test_no_tasks_is_a_parse_error():
    with pytest.raises(ParseError):
        parse("gantt\ntitle Empty\n")
