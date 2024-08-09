"""Compat library for ansible-creator.

This contains compatibility definitions for older python
When we need to import a module differently depending on python versions, we do it
here.
"""

from __future__ import annotations

import sys


if sys.version_info >= (3, 11):
    from importlib.resources.abc import Traversable as _Traversable
else:
    from importlib.abc import (  # pylint: disable = deprecated-class
        Traversable as _Traversable,  # pragma: no cover
    )

Traversable = _Traversable
