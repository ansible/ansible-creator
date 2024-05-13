"""Test the utils module."""

from pathlib import Path

from ansible_creator.utils import expand_path


def test_expand_path() -> None:
    """Test expand_path utils."""
    home = Path.home().resolve()
    expected = home / "collections/ansible_collections/namespace/collection"
    assert expand_path("~/$DEV_WORKSPACE/namespace/collection") == expected
    assert expand_path("~") == home
    assert expand_path("foo") == Path.cwd() / "foo"
    assert expand_path("$HOME") == home
    assert expand_path("~/$HOME") == Path(f"{home}/{Path.home()}")
