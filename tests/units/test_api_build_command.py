"""Unit tests for the ansible-creator V1 API: ``build_command()`` argv construction."""

from __future__ import annotations

import json

from typing import TYPE_CHECKING

import pytest

from ansible_creator.api import V1


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(name="creator_api")
def fixture_creator_api() -> V1:
    """Create a V1 API instance.

    Returns:
        V1: API instance with default verbosity.
    """
    return V1()


# --- build_command tests ---


def test_build_command_init_collection(creator_api: V1) -> None:
    """Test argv for init collection.

    Args:
        creator_api: V1 API instance.
    """
    argv = creator_api.build_command(
        "init",
        "collection",
        collection="testns.testcol",
    )
    assert argv[:3] == ["init", "collection", "testns.testcol"]


def test_build_command_add_plugin_with_flags(creator_api: V1) -> None:
    """Test argv for add plugin with overwrite flag.

    Args:
        creator_api: V1 API instance.
    """
    argv = creator_api.build_command(
        "add",
        "plugin",
        "filter",
        plugin_name="my_filter",
        overwrite=True,
    )
    assert "add" in argv
    assert "plugin" in argv
    assert "filter" in argv
    assert "my_filter" in argv
    # The overwrite flag may use short form (-o) or long form (--overwrite)
    assert "-o" in argv or "--overwrite" in argv


def test_build_command_add_resource_simple(creator_api: V1) -> None:
    """Test argv for add resource devfile.

    Args:
        creator_api: V1 API instance.
    """
    argv = creator_api.build_command("add", "resource", "devfile")
    assert argv[:4] == ["add", "resource", "devfile"]


def test_build_command_init_execution_env(creator_api: V1, tmp_path: Path) -> None:
    """Test argv for init execution_env with explicit path.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "ee"
    argv = creator_api.build_command(
        "init",
        "execution_env",
        init_path=str(target),
    )
    assert "init" in argv
    assert "execution_env" in argv
    assert str(target) in argv


def test_build_command_optional_string_arg(creator_api: V1, tmp_path: Path) -> None:
    """Test argv includes optional string arguments with flag prefix.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    log = tmp_path / "my.log"
    argv = creator_api.build_command(
        "init",
        "execution_env",
        log_file=str(log),
    )
    assert str(log) in argv


def test_build_command_store_true_false_value(creator_api: V1) -> None:
    """Test that store_true flags with False value are omitted from argv.

    Args:
        creator_api: V1 API instance.
    """
    argv = creator_api.build_command(
        "add",
        "plugin",
        "filter",
        plugin_name="my_filter",
        overwrite=False,
    )
    assert "-o" not in argv
    assert "--overwrite" not in argv


def test_build_command_routing_key_override_rejected(creator_api: V1) -> None:
    """Test that build_command rejects routing key overrides.

    Args:
        creator_api: V1 API instance.
    """
    with pytest.raises(TypeError, match="Cannot override routing keys"):
        creator_api.build_command("init", "collection", project="playbook")


def test_build_command_count_action_repeats_flag(creator_api: V1) -> None:
    """Test that count-action options repeat the flag N times.

    The ``-v`` / ``--verbosity`` argument uses ``action="count"``, so
    ``verbose=2`` should produce ``["-v", "-v"]`` rather than
    ``["-v", "2"]``.

    Args:
        creator_api: V1 API instance.
    """
    verbosity = 3
    argv = creator_api.build_command(
        "init",
        "collection",
        collection="ns.col",
        verbose=verbosity,
    )
    assert argv.count("-v") == verbosity
    # Should not include the numeric value as a separate token
    assert "3" not in argv


def test_build_command_unknown_kwarg_rejected(creator_api: V1) -> None:
    """Test that unknown kwargs raise TypeError.

    Args:
        creator_api: V1 API instance.
    """
    with pytest.raises(TypeError, match="Unknown parameters"):
        creator_api.build_command(
            "init",
            "collection",
            collection="ns.col",
            nonexistent_option="value",
        )


def test_build_command_dict_value_serialized_as_json(creator_api: V1) -> None:
    """Test that dict values are serialized as JSON strings in argv.

    When a caller passes a dict for a string-type argument (e.g. ee_config),
    the API should use json.dumps() so the downstream JSON parser can
    decode it correctly.

    Args:
        creator_api: V1 API instance.
    """
    ee_data = {"name": "my-ee", "base_image": "quay.io/fedora/fedora:41"}
    argv = creator_api.build_command(
        "init",
        "execution_env",
        ee_config=ee_data,
    )
    idx = argv.index("--ee-config")
    raw_value = argv[idx + 1]
    parsed = json.loads(raw_value)
    assert parsed == ee_data


def test_build_command_append_action_expands_list(
    creator_api: V1,
    tmp_path: Path,
) -> None:
    """Test that append-action options expand a list into repeated flags.

    The ``--ee-collections`` argument uses ``action="append"``, so
    ``ee_collections=["cisco.nxos", "ansible.utils"]`` should produce
    ``["--ee-collections", "cisco.nxos", "--ee-collections", "ansible.utils"]``
    rather than ``["--ee-collections", "['cisco.nxos', 'ansible.utils']"]``.

    Args:
        creator_api: V1 API instance.
        tmp_path: Temporary directory path.
    """
    target = tmp_path / "ee"
    argv = creator_api.build_command(
        "init",
        "execution_env",
        init_path=str(target),
        ee_collections=["cisco.nxos", "ansible.utils"],
    )
    assert argv.count("--ee-collections") == 2  # noqa: PLR2004
    nxos_idx = argv.index("cisco.nxos")
    utils_idx = argv.index("ansible.utils")
    assert argv[nxos_idx - 1] == "--ee-collections"
    assert argv[utils_idx - 1] == "--ee-collections"


def test_build_command_nargs_plus_expands_list(creator_api: V1) -> None:
    """Test that nargs='+' options expand a list into flag + items.

    The ``--include`` argument uses ``nargs="+"``, so
    ``include=["devcontainer", "vscode"]`` should produce
    ``["--include", "devcontainer", "vscode"]``.

    Args:
        creator_api: V1 API instance.
    """
    argv = creator_api.build_command(
        "init",
        "collection",
        collection="ns.col",
        include=["devcontainer", "vscode"],
    )
    idx = argv.index("--include")
    assert argv[idx + 1] == "devcontainer"
    assert argv[idx + 2] == "vscode"


def test_build_command_nargs_plus_accepts_tuple(creator_api: V1) -> None:
    """Test that nargs='+' options also accept tuples.

    API consumers may pass tuples instead of lists for immutable sequences.

    Args:
        creator_api: V1 API instance.
    """
    argv = creator_api.build_command(
        "init",
        "collection",
        collection="ns.col",
        include=("gitignore", "ai"),
    )
    idx = argv.index("--include")
    assert argv[idx + 1] == "gitignore"
    assert argv[idx + 2] == "ai"
