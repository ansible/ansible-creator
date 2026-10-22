"""Unit tests for the ansible-creator V1 API: schema introspection."""

from __future__ import annotations

import argparse

import pytest

from ansible_creator.api import V1
from ansible_creator.schema import _extract_action_info


@pytest.fixture(name="creator_api")
def fixture_creator_api() -> V1:
    """Create a V1 API instance.

    Returns:
        V1: API instance with default verbosity.
    """
    return V1()


# --- Schema tests ---


def test_schema_returns_dict(creator_api: V1) -> None:
    """Test that schema() returns a well-formed dictionary.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.schema()
    assert isinstance(result, dict)
    assert result["name"] == "ansible-creator"
    assert "subcommands" in result
    assert "init" in result["subcommands"]
    assert "add" in result["subcommands"]
    assert "schema" in result["subcommands"]


def test_schema_init_has_subcommands(creator_api: V1) -> None:
    """Test that init subcommand has expected project types.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.schema()
    init_cmd = result["subcommands"]["init"]
    assert "subcommands" in init_cmd
    assert "collection" in init_cmd["subcommands"]
    assert "playbook" in init_cmd["subcommands"]
    assert "execution_env" in init_cmd["subcommands"]


def test_schema_add_has_resource_and_plugin(creator_api: V1) -> None:
    """Test that add subcommand has resource and plugin subtrees.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.schema()
    add_cmd = result["subcommands"]["add"]
    assert "subcommands" in add_cmd
    assert "resource" in add_cmd["subcommands"]
    assert "plugin" in add_cmd["subcommands"]


def test_schema_for_init_collection(creator_api: V1) -> None:
    """Test schema_for() returns correct subtree for init collection.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.schema_for("init", "collection")
    assert result["name"] == "collection"
    assert "parameters" in result
    assert "collection" in result["parameters"]["properties"]


def test_schema_for_add_resource(creator_api: V1) -> None:
    """Test schema_for() returns correct subtree for add resource devfile.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.schema_for("add", "resource", "devfile")
    assert result["name"] == "devfile"
    assert "parameters" in result


def test_schema_for_invalid_path(creator_api: V1) -> None:
    """Test schema_for() raises KeyError for invalid path.

    Args:
        creator_api: V1 API instance.
    """
    with pytest.raises(KeyError, match="not found"):
        creator_api.schema_for("init", "nonexistent")


def test_schema_for_empty_path(creator_api: V1) -> None:
    """Test schema_for() with no path returns the root schema.

    Args:
        creator_api: V1 API instance.
    """
    result = creator_api.schema_for()
    assert result["name"] == "ansible-creator"


def test_schema_extract_append_action_type() -> None:
    """Test _extract_action_info handles action='append' as array type."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", action="append", help="Repeatable items")
    action = next(a for a in parser._actions if a.dest == "items")
    info = _extract_action_info(action)
    assert info["type"] == "array"
    assert info["items"] == {"type": "string"}


def test_schema_extract_int_type() -> None:
    """Test _extract_action_info handles int type arguments."""
    parser = argparse.ArgumentParser()
    expected_default = 5
    parser.add_argument("--count", type=int, default=expected_default, help="A count")
    action = next(a for a in parser._actions if a.dest == "count")
    info = _extract_action_info(action)
    assert info["type"] == "int"
    assert info["default"] == expected_default


def test_schema_extract_array_type() -> None:
    """Test _extract_action_info handles nargs=+ arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", nargs="+", help="Multiple items")
    action = next(a for a in parser._actions if a.dest == "items")
    info = _extract_action_info(action)
    assert info["type"] == "array"
    assert info["items"] == {"type": "string"}


def test_schema_extract_count_action_type() -> None:
    """Test _extract_action_info handles action='count' as integer type."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Verbosity")
    action = next(a for a in parser._actions if a.dest == "verbose")
    info = _extract_action_info(action)
    assert info["type"] == "integer"


def test_schema_extract_boolean_optional_action() -> None:
    """Test _extract_action_info handles BooleanOptionalAction as boolean type."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--flag",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="A flag",
    )
    action = next(a for a in parser._actions if a.dest == "flag")
    info = _extract_action_info(action)
    assert info["type"] == "boolean"


def test_schema_extract_schema_metadata() -> None:
    """Test _extract_action_info merges schema_metadata into output."""
    parser = argparse.ArgumentParser()
    expected_min_length = 3
    act = parser.add_argument("--name", help="A name")
    act.schema_metadata = {  # type: ignore[attr-defined]
        "minLength": expected_min_length,
        "pattern": "^[a-z]+$",
        "format": "fqcn",
    }
    action = next(a for a in parser._actions if a.dest == "name")
    info = _extract_action_info(action)
    assert info["minLength"] == expected_min_length
    assert info["pattern"] == "^[a-z]+$"
    assert info["format"] == "fqcn"
    assert info["type"] == "string"


def test_schema_validation_metadata_on_collection() -> None:
    """Test that collection parameter includes validation metadata."""
    from ansible_creator.schema import for_command  # noqa: PLC0415

    schema = for_command("init", "collection")
    props = schema["parameters"]["properties"]
    assert "collection" in props
    col = props["collection"]
    assert "pattern" in col
    assert "minLength" in col
    assert col["format"] == "fqcn"
    expected_min_length = 7
    assert col["minLength"] == expected_min_length


def test_schema_validation_metadata_on_verbosity() -> None:
    """Test that verbose parameter includes integer type and min/max."""
    from ansible_creator.schema import for_command  # noqa: PLC0415

    schema = for_command("init", "collection")
    props = schema["parameters"]["properties"]
    assert "verbose" in props
    verbose = props["verbose"]
    assert verbose["type"] == "integer"
    assert verbose["minimum"] == 0
    expected_max = 3
    assert verbose["maximum"] == expected_max


def test_schema_validation_metadata_on_ee_file_name() -> None:
    """Test that ee_file_name parameter includes pattern and minLength."""
    from ansible_creator.schema import for_command  # noqa: PLC0415

    schema = for_command("init", "execution_env")
    props = schema["parameters"]["properties"]
    assert "ee_file_name" in props
    ee_fn = props["ee_file_name"]
    assert "pattern" in ee_fn
    expected_min_length = 5
    assert ee_fn["minLength"] == expected_min_length


def test_schema_validation_metadata_on_registry_tls_verify() -> None:
    """Test that registry_tls_verify is detected as boolean type."""
    from ansible_creator.schema import for_command  # noqa: PLC0415

    schema = for_command("init", "execution_env")
    props = schema["parameters"]["properties"]
    assert "registry_tls_verify" in props
    assert props["registry_tls_verify"]["type"] == "boolean"
