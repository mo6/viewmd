import re

import pytest

from viewmd.mermaid.quadrant.parser import ParseError, parse, sniff


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("quadrantChart\ntitle X", True),
        ("QUADRANTCHART\ntitle X", True),
        ("quadrantChartFoo\ntitle X", True),  # sniff is a prefix match, like pie's own keyword
        ("%% a comment\nquadrantChart\ntitle X", True),
        ("pie\n\"A\":1", False),
        ("sequenceDiagram\nA->>B: hi", False),
        ("", False),
    ],
)
def test_sniff(source, expected):
    assert sniff(source) == expected


def test_parse_full_example():
    source = (
        "quadrantChart\n"
        "    title Reach and engagement of campaigns\n"
        "    x-axis Low Reach --> High Reach\n"
        "    y-axis Low Engagement --> High Engagement\n"
        "    quadrant-1 We should expand\n"
        "    quadrant-2 Need to promote\n"
        "    quadrant-3 Re-evaluate\n"
        "    quadrant-4 May be improved\n"
        "    Campaign A: [0.3, 0.6]\n"
    )
    chart = parse(source)
    assert chart.title == "Reach and engagement of campaigns"
    assert (chart.x_low, chart.x_high) == ("Low Reach", "High Reach")
    assert (chart.y_low, chart.y_high) == ("Low Engagement", "High Engagement")
    assert chart.quadrants == {
        1: "We should expand",
        2: "Need to promote",
        3: "Re-evaluate",
        4: "May be improved",
    }
    assert len(chart.points) == 1
    p = chart.points[0]
    assert (p.label, p.x, p.y, p.color) == ("Campaign A", 0.3, 0.6, None)


def test_parse_multiple_points():
    source = (
        "quadrantChart\n"
        "x-axis Low --> High\n"
        "y-axis Low --> High\n"
        "A: [0.1, 0.2]\n"
        "B: [0.3, 0.4]\n"
        "C: [0.5, 0.6]\n"
    )
    chart = parse(source)
    assert [p.label for p in chart.points] == ["A", "B", "C"]


def test_axis_low_only_form():
    # Mermaid's own syntax allows a bare `x-axis <text>` with no `-->`/high
    # label; the low label alone is still parsed.
    chart = parse("quadrantChart\nx-axis Effort\ny-axis Impact\n")
    assert (chart.x_low, chart.x_high) == ("Effort", "")
    assert (chart.y_low, chart.y_high) == ("Impact", "")


def test_quoted_labels_are_unquoted():
    chart = parse(
        'quadrantChart\n'
        'title "A title"\n'
        'x-axis Low --> "High ❤"\n'
        'y-axis Low --> High\n'
    )
    assert chart.title == "A title"
    assert chart.x_high == "High ❤"


def test_point_color_style_key():
    chart = parse(
        "quadrantChart\nx-axis Low --> High\ny-axis Low --> High\n"
        "A: [0.1, 0.2] color: #ff3300, radius: 10\n"
    )
    assert chart.points[0].color == "#ff3300"


def test_point_classdef_color_resolved_even_when_classdef_comes_after():
    chart = parse(
        "quadrantChart\nx-axis Low --> High\ny-axis Low --> High\n"
        "A:::c1: [0.1, 0.2]\n"
        "classDef c1 color: #109060, radius: 10\n"
    )
    assert chart.points[0].color == "#109060"


def test_point_own_color_overrides_classdef_color():
    chart = parse(
        "quadrantChart\nx-axis Low --> High\ny-axis Low --> High\n"
        "A:::c1: [0.1, 0.2] color: #ff3300\n"
        "classDef c1 color: #109060\n"
    )
    assert chart.points[0].color == "#ff3300"


def test_point_with_no_color_and_no_class_has_color_none():
    chart = parse(
        "quadrantChart\nx-axis Low --> High\ny-axis Low --> High\nA: [0.1, 0.2]\n"
    )
    assert chart.points[0].color is None


def test_malformed_point_line_is_skipped_not_aborted():
    # Requirement 9: a non-numeric coordinate is skipped, not a parse
    # failure of the whole chart.
    chart = parse(
        "quadrantChart\nx-axis Low --> High\ny-axis Low --> High\n"
        "Good: [0.1, 0.2]\n"
        "Bad: [abc, 0.2]\n"
    )
    assert [p.label for p in chart.points] == ["Good"]


def test_non_finite_point_coordinates_are_skipped_not_a_crash():
    # Regression: float() happily parses "nan"/"inf"/"-inf" as valid floats,
    # which would otherwise reach the renderer's round()/grid-index math and
    # crash with ValueError ("cannot convert float NaN to integer") -- a
    # bare crash, not the raw-fence fallback requirement 9 promises. Treated
    # the same as a non-numeric coordinate: skipped, not an abort.
    chart = parse(
        "quadrantChart\nx-axis Low --> High\ny-axis Low --> High\n"
        "Good: [0.1, 0.2]\n"
        "NotANumber: [nan, inf]\n"
        "AlsoBad: [-inf, 0.5]\n"
    )
    assert [p.label for p in chart.points] == ["Good"]


def test_sniff_and_parse_tolerate_leading_front_matter():
    # The issue's own "Example on config and theme" mockup wraps the
    # diagram in a YAML front-matter block for Mermaid's config/theme
    # overrides -- its presence must not hide the quadrantChart keyword.
    source = (
        "---\n"
        "config:\n"
        "  quadrantChart:\n"
        "    chartWidth: 400\n"
        "---\n"
        "quadrantChart\n"
        "x-axis Low --> High\n"
        "y-axis Low --> High\n"
    )
    assert sniff(source) is True
    chart = parse(source)
    assert (chart.x_low, chart.x_high) == ("Low", "High")


@pytest.mark.parametrize(
    "source",
    [
        "quadrantChart\nx-axis  -->  \ny-axis Low --> High\n",
        "quadrantChart\nx-axis Low --> High\ny-axis  -->  \n",
    ],
)
def test_axis_line_with_empty_labels_on_both_sides_of_arrow_is_rejected(source):
    # Regression: an axis line like "x-axis  --> " (empty low AND empty high
    # label) can't satisfy the high group's `.+`, so the regex used to
    # backtrack and swallow the literal "-->" into the low label instead of
    # failing -- silently accepting "-->" as if it were a real axis label.
    with pytest.raises(ParseError, match="could not parse line"):
        parse(source)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("", 'expected "quadrantChart" keyword'),
        ("pie\n\"A\":1", 'expected "quadrantChart" keyword'),
        ("quadrantChart\nx-axis Low --> High\n", "expected both an x-axis and a y-axis"),
        ("quadrantChart\ny-axis Low --> High\n", "expected both an x-axis and a y-axis"),
        ("quadrantChart\nx-axis Low --> High\ny-axis Low --> High\nnot a real line\n",
         "could not parse line"),
    ],
)
def test_parse_errors(source, message):
    with pytest.raises(ParseError, match=re.escape(message)):
        parse(source)
