import argparse

import pytest

from viewmd.__main__ import DEFAULT_MAX_WIDTH, _resolve_width, _width_arg


def test_resolve_width_defaults_to_100_when_terminal_is_wider():
    assert _resolve_width(None, terminal_width=200) == DEFAULT_MAX_WIDTH


def test_resolve_width_defaults_to_terminal_width_when_narrower_than_100():
    assert _resolve_width(None, terminal_width=60) == 60


def test_resolve_width_explicit_number_overrides_the_100_cap():
    assert _resolve_width("60", terminal_width=200) == 60
    assert _resolve_width("150", terminal_width=80) == 150


def test_resolve_width_full_uses_terminal_width_uncapped():
    assert _resolve_width("full", terminal_width=200) == 200
    assert _resolve_width("full", terminal_width=60) == 60


def test_width_arg_accepts_full():
    assert _width_arg("full") == "full"


def test_width_arg_accepts_positive_integer_string():
    assert _width_arg("42") == "42"


@pytest.mark.parametrize("value", ["0", "-5", "banana", ""])
def test_width_arg_rejects_invalid_values(value):
    with pytest.raises(argparse.ArgumentTypeError):
        _width_arg(value)
