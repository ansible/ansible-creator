"""Compat library for ansible-creator.

This contains compatibility definitions for older python
When we need to import a module differently depending on python versions, we do it
here.
"""

# ruff: noqa: F401

# pylint: disable=unused-import

import sys


if sys.version_info >= (3, 11):
    from importlib.resources.abc import Traversable
else:
    from importlib.abc import Traversable
