"""Tests for compat module."""

from __future__ import annotations

from ansible_creator.compat import Traversable


def test_import() -> None:
    """Test the import of traversable.

    This is a simple test to ensure that the import of Traversable is working.
    Since it is only imported for type checking.
    """
    assert Traversable is not None
