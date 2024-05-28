"""Compat library for ansible-creator.

This contains compatibility definitions for older python
When we need to import a module differently depending on python versions, we do it
here.
"""

# ruff: noqa: F401

import sys


if sys.version_info >= (3, 11):
    from importlib.resources.abc import Traversable as _Traversable
else:
    from importlib.abc import (  # pylint: disable=deprecated-class
        Traversable as _Traversable,
    )

Traversable = _Traversable
