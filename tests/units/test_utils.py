"""Test the utils module."""

from pathlib import Path

from ansible_creator.utils import expand_path


def test_expand_path() -> None:
    """Test expand_path."""
    assert expand_path("~") == Path.home()
    assert expand_path("foo") == Path.cwd() / "foo"
    assert expand_path("$HOME") == Path.home()
    assert expand_path("~/$HOME") == Path(str(Path.home()) + str(Path.home()))
