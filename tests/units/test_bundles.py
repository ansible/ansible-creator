"""Tests for ansible_creator.bundles module."""

from __future__ import annotations

from ansible_creator.bundles import (
    _INIT_EXCLUDED_BUNDLES,
    discover_common_bundles,
    get_init_bundle_names,
)


def test_discover_common_bundles_returns_sorted_tuple() -> None:
    """All discovered bundle names are sorted alphabetically."""
    result = discover_common_bundles()
    assert isinstance(result, tuple)
    assert result == tuple(sorted(result))


def test_discover_common_bundles_contains_known_bundles() -> None:
    """Known bundles from the resources directory appear in the result."""
    result = discover_common_bundles()
    for expected in ("ai", "devcontainer", "devfile", "gitignore", "role", "vscode"):
        assert expected in result


def test_get_init_bundle_names_excludes_special_purpose() -> None:
    """Init-eligible bundles do not include special-purpose bundles."""
    result = get_init_bundle_names()
    for excluded in _INIT_EXCLUDED_BUNDLES:
        assert excluded not in result


def test_get_init_bundle_names_is_subset_of_all() -> None:
    """Init bundle names are a proper subset of all discovered bundles."""
    all_bundles = set(discover_common_bundles())
    init_bundles = set(get_init_bundle_names())
    assert init_bundles < all_bundles


def test_get_init_bundle_names_sorted() -> None:
    """Init bundle names are sorted alphabetically."""
    result = get_init_bundle_names()
    assert result == tuple(sorted(result))


def test_new_bundle_directory_auto_discovered() -> None:
    """Verify the caching mechanism returns consistent results."""
    first_call = discover_common_bundles()
    second_call = discover_common_bundles()
    assert first_call is second_call
