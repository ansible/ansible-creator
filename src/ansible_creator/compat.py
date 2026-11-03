"""Compat library for ansible-creator.

This contains compatibility definitions for older python
When we need to import a module differently depending on python versions, we do it
here.
"""

from __future__ import annotations

from importlib.resources.abc import Traversable as _Traversable


Traversable = _Traversable
