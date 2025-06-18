"""Test the custom help formatter."""

from __future__ import annotations

import argparse

import pytest

from ansible_creator.arg_parser import CustomHelpFormatter


def test_custom_help_single() -> None:
    """Test the custom help formatter with single."""
    parser = argparse.ArgumentParser(formatter_class=CustomHelpFormatter)
    parser.add_argument("--foo", help="foo help")
    help_text = parser.format_help()
    line = " --foo          foo help"
    assert line in help_text.splitlines()


def test_custom_help_double() -> None:
    """Test the custom help formatter with double."""
    parser = argparse.ArgumentParser(formatter_class=CustomHelpFormatter)
    parser.add_argument("-f", "--foo", help="foo help")
    help_text = parser.format_help()
    line = " -f     --foo   foo help"
    assert line in help_text.splitlines()


def test_custom_help_triple() -> None:
    """Test the custom help formatter with triple."""
    parser = argparse.ArgumentParser(formatter_class=CustomHelpFormatter)
    parser.add_argument("-f", "--foo", "--foolish", help="foo help")

    with pytest.raises(ValueError, match="Too many option strings"):
        parser.format_help()
