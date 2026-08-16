import re

import pytest

from viewmd.mermaid.xychart.parser import ParseError, parse, sniff


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("xychart-beta\nbar [1]", True),
        ("xychart\nbar [1]", True),
        ("XYCHART-BETA\nbar [1]", True),
        ("XYCHART\nbar [1]", True),
        ("xychart-beta horizontal\nbar [1]", True),
        ("xychart horizontal\nbar [1]", True),
        ("%% a comment\nxychart-beta\nbar [1]", True),
        ("---\nconfig:\n  theme: default\n---\nxychart-beta\nbar [1]", True),
        ("xychart-betaFoo\nbar [1]", False),
        ("xychartFoo\nbar [1]", False),
        ("pie\n\"A\":1", False),
        ("sequenceDiagram\nA->>B: hi", False),
        ("", False),
        ("%% just a comment", False),
    ],
)
def test_sniff(source, expected):
    assert sniff(source) == expected


def test_parse_bar_only_bare_x_axis():
    chart = parse(
        "xychart-beta\n"
        "    title \"Sales\"\n"
        "    x-axis [Q1, Q2, Q3, Q4]\n"
        "    y-axis 0 --> 100\n"
        "    bar [40, 55, 70, 90]\n"
    )
    assert chart.title == "Sales"
    assert chart.categories == ["Q1", "Q2", "Q3", "Q4"]
    assert chart.x_title == ""
    assert (chart.y_min, chart.y_max) == (0.0, 100.0)
    assert chart.bar == [40.0, 55.0, 70.0, 90.0]
    assert chart.line is None
    assert chart.horizontal is False


def test_parse_titled_x_axis_and_y_axis():
    chart = parse(
        'xychart-beta\n'
        '    x-axis "quarter" [Q1, Q2]\n'
        '    y-axis "USD" 10 --> 50\n'
        '    bar [20, 40]\n'
    )
    assert chart.x_title == "quarter"
    assert chart.y_title == "USD"
    assert chart.categories == ["Q1", "Q2"]
    assert (chart.y_min, chart.y_max) == (10.0, 50.0)


def test_parse_quoted_category_names():
    chart = parse(
        'xychart\n'
        '    x-axis ["Category 1", "Category 2"]\n'
        '    bar [1, 2]\n'
    )
    assert chart.categories == ["Category 1", "Category 2"]


def test_omitted_y_axis_leaves_range_unset():
    chart = parse(
        "xychart-beta\n"
        "    x-axis [A, B]\n"
        "    bar [10, 20]\n"
    )
    assert chart.y_min is None and chart.y_max is None
    assert chart.bar == [10.0, 20.0]


def test_parse_line_only():
    chart = parse(
        "xychart-beta\n"
        "    x-axis [Q1, Q2, Q3, Q4]\n"
        "    y-axis 0 --> 100\n"
        "    line [40, 60, 20, 100]\n"
    )
    assert chart.line == [40.0, 60.0, 20.0, 100.0]
    assert chart.bar is None


def test_parse_combo_bar_and_line():
    chart = parse(
        "xychart-beta\n"
        "    x-axis [Q1, Q2, Q3, Q4]\n"
        "    y-axis 0 --> 120\n"
        "    bar  [40, 60, 80, 100]\n"
        "    line [60, 80, 100, 120]\n"
    )
    assert chart.bar == [40.0, 60.0, 80.0, 100.0]
    assert chart.line == [60.0, 80.0, 100.0, 120.0]


def test_bare_xychart_alias():
    chart = parse("xychart\n    x-axis [A, B]\n    line [1, 2]\n")
    assert chart.categories == ["A", "B"]
    assert chart.line == [1.0, 2.0]


def test_horizontal_keyword_is_parsed_and_ignored():
    chart = parse(
        "xychart-beta horizontal\n"
        "    x-axis [A, B]\n"
        "    bar [1, 2]\n"
    )
    assert chart.horizontal is True
    assert chart.bar == [1.0, 2.0]


def test_malformed_axis_line_is_tolerated_without_raising():
    # Requirement 9 / termaid's TestMalformedXYChartInput: a range that
    # fails to parse is skipped, not an abort of the whole chart.
    chart = parse(
        'xychart-beta\n'
        '    x-axis "t" 0.1.2 --> 10\n'
        '    bar [1, 2]\n'
    )
    assert chart.categories == []
    assert chart.bar == [1.0, 2.0]


def test_malformed_y_axis_is_tolerated_and_leaves_range_unset():
    chart = parse(
        "xychart-beta\n"
        "    x-axis [A, B]\n"
        "    y-axis 0.1.2 --> 10\n"
        "    bar [1, 2]\n"
    )
    assert chart.y_min is None and chart.y_max is None
    assert chart.categories == ["A", "B"]


def test_front_matter_config_is_ignored():
    chart = parse(
        "---\n"
        "config:\n"
        "  themeVariables:\n"
        "    xyChart:\n"
        "      plotColorPalette: '#000000, #0000FF'\n"
        "---\n"
        "xychart\n"
        "    x-axis [A, B]\n"
        "    bar [1, 2]\n"
    )
    assert chart.bar == [1.0, 2.0]


def test_init_directive_comment_is_ignored():
    chart = parse(
        "xychart-beta\n"
        "    %%{init: {'theme': 'dark'}}%%\n"
        "    x-axis [A, B]\n"
        "    bar [1, 2]\n"
    )
    assert chart.bar == [1.0, 2.0]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("", 'expected "xychart-beta" or "xychart" keyword'),
        ("pie\n\"A\":1", 'expected "xychart-beta" or "xychart" keyword'),
        ("xychart-beta\n    x-axis [A, B]\n", "expected a bar or line dataset"),
        (
            "xychart-beta\n    x-axis [A, B]\n    bar [1]\n",
            "bar dataset has 1 values, expected 2 categories",
        ),
        (
            "xychart-beta\n    x-axis [A, B]\n    bar [1, 2]\n    bar [3, 4]\n",
            "multiple bar datasets are not supported",
        ),
        (
            "xychart-beta\n    x-axis [A, B]\n    line [1, 2]\n    line [3, 4]\n",
            "multiple line datasets are not supported",
        ),
        (
            "xychart-beta\n    x-axis 0 --> 10\n    bar [1, 2]\n",
            "numeric x-axis is not supported",
        ),
        (
            "xychart-beta\n    x-axis [A, B]\n    bar [1, 2]\n    not a real line\n",
            "could not parse line",
        ),
        (
            'xychart-beta\n    x-axis [A]\n    line [1.5 "label"]\n',
            "could not parse dataset value",
        ),
    ],
)
def test_parse_errors(source, message):
    with pytest.raises(ParseError, match=re.escape(message)):
        parse(source)


def test_dataset_optional_name_is_accepted():
    chart = parse(
        'xychart-beta\n'
        '    x-axis [A, B]\n'
        '    bar "Sales" [10, 20]\n'
        '    line "Target" [15, 25]\n'
    )
    assert chart.bar == [10.0, 20.0]
    assert chart.line == [15.0, 25.0]


def test_float_values():
    chart = parse(
        "xychart-beta\n"
        "    x-axis [Q1, Q2]\n"
        "    bar [42.5, 67.3]\n"
    )
    assert chart.bar == [42.5, 67.3]
