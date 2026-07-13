"""Dynamic discovery of common resource bundles.

This module introspects the ``ansible_creator.resources.common`` package
to enumerate available scaffold bundles at runtime, eliminating the need
for hardcoded bundle lists in multiple locations.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources as impl_resources


RESOURCE_PACKAGE = "ansible_creator.resources.common"

_INIT_EXCLUDED_BUNDLES: frozenset[str] = frozenset(
    {
        "ee-ci",
        "execution-environment",
        "play-argspec",
        "molecule_migrate",
    },
)


@lru_cache(maxsize=1)
def discover_common_bundles() -> tuple[str, ...]:
    """Discover all common resource bundle names from the package filesystem.

    Returns a sorted tuple of short bundle names (directory names under
    ``ansible_creator/resources/common/``).

    Returns:
        Sorted tuple of all discovered bundle short names.
    """
    common_root = impl_resources.files(RESOURCE_PACKAGE)
    return tuple(
        sorted(
            entry.name
            for entry in common_root.iterdir()
            if entry.is_dir() and entry.name != "__pycache__"
        ),
    )


@lru_cache(maxsize=1)
def get_init_bundle_names() -> tuple[str, ...]:
    """Return bundle names valid for ``--include``/``--exclude`` during init.

    Excludes special-purpose bundles that are not user-selectable
    (e.g. ``ee-ci`` is auto-included for execution-environment projects).

    Returns:
        Sorted tuple of init-eligible bundle short names.
    """
    return tuple(name for name in discover_common_bundles() if name not in _INIT_EXCLUDED_BUNDLES)
