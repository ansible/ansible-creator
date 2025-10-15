"""Test the custom help formatter."""

from __future__ import annotations

import sys

import pytest

from ansible_creator.arg_parser import CustomArgumentParser


@pytest.mark.skipif(
    sys.version_info >= (3, 14), reason="Custom help formatter is not supported in Python 3.14+"
)
def test_custom_help_single() -> None:
    """Test the custom help formatter with single."""
    parser = CustomArgumentParser()
    parser.add_argument("--foo", help="foo help")
    help_text = parser.format_help()
    line = " --foo          foo help"
    assert line in help_text.splitlines()


@pytest.mark.skipif(
    sys.version_info >= (3, 14), reason="Custom help formatter is not supported in Python 3.14+"
)
def test_custom_help_double() -> None:
    """Test the custom help formatter with double."""
    parser = CustomArgumentParser()
    parser.add_argument("-f", "--foo", help="foo help")
    help_text = parser.format_help()
    line = " -f     --foo   foo help"
    assert line in help_text.splitlines()


@pytest.mark.skipif(
    sys.version_info >= (3, 14), reason="Custom help formatter is not supported in Python 3.14+"
)
def test_custom_help_triple() -> None:
    """Test the custom help formatter with triple."""
    parser = CustomArgumentParser()
    parser.add_argument("-f", "--foo", "--foolish", help="foo help")

    with pytest.raises(ValueError, match="Too many option strings"):
        parser.format_help()
