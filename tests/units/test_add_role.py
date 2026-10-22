"""Unit tests for ansible-creator add: role resource and galaxy helpers."""

from __future__ import annotations

from filecmp import cmp
from typing import TYPE_CHECKING, Any, TypedDict

import pytest
import yaml

from ansible_creator.config import Config
from ansible_creator.exceptions import CreatorError


if TYPE_CHECKING:
    from pathlib import Path

    from ansible_creator.output import Output

from ansible_creator.subcommands.add import Add
from tests.defaults import FIXTURES_DIR


class ConfigDict(TypedDict):
    """Type hint for Config dictionary.

    Attributes:
        creator_version: The version of the creator.
        output: The output object to use for logging.
        subcommand: The subcommand to execute.
        resource_type: The type of resource to be scaffolded.
        plugin_type: The type of the plugin to be scaffolded.
        plugin_name: The name of the plugin to be scaffolded.
        type: The type of the project for which the resource is being scaffolded.
        path: The file path where the resource should be added.
        force: Force overwrite of existing directory.
        overwrite: To overwrite files in an existing directory.
        no_overwrite: To not overwrite files in an existing directory.
        image: The image to be used while scaffolding devcontainer.
        role_name: The name of role to be used while scaffolding.
        skip_collection_check: Whether to skip collection path validation.
        scm_provider: SCM provider for EE CI (github or gitlab).
    """

    creator_version: str
    output: Output
    subcommand: str
    resource_type: str
    plugin_type: str
    plugin_name: str
    type: str
    path: str
    force: bool
    overwrite: bool
    no_overwrite: bool
    image: str
    role_name: str
    skip_collection_check: bool
    scm_provider: str


@pytest.fixture(name="cli_args")
def fixture_cli_args(tmp_path: Path, output: Output) -> ConfigDict:
    """Create a dict to use for a Add class object as fixture.

    Args:
        tmp_path: Temporary directory path.
        output: Output class object.

    Returns:
        dict: Dictionary, partial Add class object.
    """
    return {
        "creator_version": "0.0.1",
        "output": output,
        "subcommand": "add",
        "type": "resource",
        "resource_type": "",
        "plugin_type": "",
        "plugin_name": "hello_world",
        "path": str(tmp_path),
        "force": False,
        "overwrite": False,
        "no_overwrite": False,
        "image": "",
        "role_name": "",
        "skip_collection_check": False,
        "scm_provider": "github",
    }


def test_run_success_add_role(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run() for adding a role sample file.

    Successfully adds role sample file to path.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.

    Raises:
        ValueError: If the file is not found.
    """
    # Set the resource_type to role
    cli_args["resource_type"] = "role"
    cli_args["role_name"] = "run"
    add = Add(
        Config(**cli_args),
    )

    # Mock the "_check_collection_path" method
    def mock_check_collection_path() -> None:
        """Mock function to skip checking collection path."""

    monkeypatch.setattr(
        Add,
        "_check_collection_path",
        staticmethod(mock_check_collection_path),
    )

    # Mock the "role_galaxy" method
    def mock_role_galaxy() -> tuple[str, str]:
        """Mock this function to return specific values.

        Returns:
            tuple[str, str]: Values for namespace and collection name.
        """
        return "testorg", "testcol"

    monkeypatch.setattr(
        Add,
        "role_galaxy",
        staticmethod(mock_role_galaxy),
    )

    add.run()
    result = capsys.readouterr().out
    assert "Note: Resource added to" in result

    # Verify the role file match the expected structure
    try:
        expected_role_file = tmp_path / "roles" / "run" / "meta" / "main.yml"
        effective_role_file = (
            FIXTURES_DIR
            / "collection"
            / "testorg"
            / "testcol"
            / "roles"
            / "run"
            / "meta"
            / "main.yml"
        )
    except ValueError as e:
        # Assign the error message to a variable before raising the exception
        error_message = "file not found"
        raise ValueError(error_message) from e

    cmp_result = cmp(expected_role_file, effective_role_file, shallow=False)
    assert cmp_result

    # Test for overwrite prompt and failure with no overwrite option
    conflict_file = tmp_path / "roles" / "run" / "meta" / "main.yml"
    conflict_file.write_text('{ "version": "1" }')

    # expect a CreatorError when the response to overwrite is no.
    monkeypatch.setattr("builtins.input", lambda _: "n")
    fail_msg = (
        "The destination directory contains files that will be overwritten."
        " Please re-run ansible-creator with --overwrite to continue."
    )
    with pytest.raises(
        CreatorError,
        match=fail_msg,
    ):
        add.run()

    # expect a warning followed by execution-environment resource creation msg
    # when response to overwrite is yes.
    monkeypatch.setattr("builtins.input", lambda _: "y")
    add.run()
    result = capsys.readouterr().out
    assert "already exists" in result, result
    assert "Note: Resource added to" in result


def test_run_success_add_role_uses_role_name(
    tmp_path: Path,
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run() renders the role name in the README examples and defaults comment.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.
    """
    cli_args["resource_type"] = "role"
    cli_args["role_name"] = "web_server"
    add = Add(Config(**cli_args))

    def mock_check_collection_path() -> None:
        """Mock function to skip checking collection path."""

    def mock_role_galaxy() -> tuple[str, str]:
        """Mock function to return a namespace and collection name.

        Returns:
            tuple[str, str]: Values for namespace and collection name.
        """
        return "testorg", "testcol"

    monkeypatch.setattr(Add, "_check_collection_path", staticmethod(mock_check_collection_path))
    monkeypatch.setattr(Add, "role_galaxy", staticmethod(mock_role_galaxy))

    add.run()

    role_dir = tmp_path / "roles" / "web_server"
    readme = (role_dir / "README.md").read_text()
    defaults_text = (role_dir / "defaults" / "main.yml").read_text()

    assert "role: testorg.testcol.web_server\n      web_server_my_variable:" in readme
    assert (
        "name: testorg.testcol.web_server\n      vars:\n        web_server_my_variable:" in readme
    )
    assert "testorg.testcol.run" not in readme
    assert " run role" not in readme
    assert "run_x" not in readme
    assert "web_server_my_variable" in yaml.safe_load(defaults_text)
    assert "'web_server_' prefix" in defaults_text


def test_update_galaxy_dependency(tmp_path: Path, cli_args: ConfigDict) -> None:
    """Test update_galaxy_dependency method.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.

    """
    galaxy_file = tmp_path / "galaxy.yml"
    initial_data: dict[str, Any]

    # Test case 1: No dependencies key
    initial_data = {"name": "test_collection"}
    galaxy_file.write_text(yaml.dump(initial_data))
    add = Add(Config(**cli_args))
    add.update_galaxy_dependency()

    with galaxy_file.open("r") as file:
        updated_data = yaml.safe_load(file)
    assert "dependencies" in updated_data
    assert updated_data["dependencies"] == {"ansible.utils": "*"}

    # Test case 2: Empty dependencies
    initial_data = {"name": "test_collection", "dependencies": {}}
    galaxy_file.write_text(yaml.dump(initial_data))
    add.update_galaxy_dependency()

    with galaxy_file.open("r") as file:
        updated_data = yaml.safe_load(file)
    assert updated_data["dependencies"] == {"ansible.utils": "*"}

    # Test case 3: Existing dependencies without ansible.utils
    initial_data = {"name": "test_collection", "dependencies": {"another.dep": "1.0.0"}}
    galaxy_file.write_text(yaml.dump(initial_data))
    add.update_galaxy_dependency()

    with galaxy_file.open("r") as file:
        updated_data = yaml.safe_load(file)
    assert updated_data["dependencies"] == {"another.dep": "1.0.0", "ansible.utils": "*"}

    # Test case 4: Existing dependencies with ansible.utils
    initial_data = {"name": "test_collection", "dependencies": {"ansible.utils": "1.0.0"}}
    galaxy_file.write_text(yaml.dump(initial_data))
    add.update_galaxy_dependency()

    with galaxy_file.open("r") as file:
        updated_data = yaml.safe_load(file)
    assert updated_data["dependencies"] == {"ansible.utils": "1.0.0"}


def test_role_galaxy(tmp_path: Path, cli_args: ConfigDict) -> None:
    """Test update_galaxy_dependency method.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
    """
    galaxy_file = tmp_path / "galaxy.yml"
    initial_data: dict[str, Any]

    # Test case 1: No dependencies key
    initial_data = {}
    galaxy_file.write_text(yaml.dump(initial_data))
    add = Add(Config(**cli_args))
    namespace, collection_name = add.role_galaxy()

    with galaxy_file.open("r") as file:
        updated_data = yaml.safe_load(file)
    assert namespace == "your-collection-namespace", f"Namespace name mismatch {namespace}"
    assert collection_name == "your-collection-name", f"Collection name mismatch {collection_name}"
    assert namespace == "your-collection-namespace"
    assert collection_name == "your-collection-name"

    # Test case 3: Existing dependencies without ansible.utils
    initial_data = {"namespace": "test_collection", "name": "collection_test"}
    galaxy_file.write_text(yaml.dump(initial_data))
    namespace, collection_name = add.role_galaxy()

    with galaxy_file.open("r") as file:
        updated_data = yaml.safe_load(file)

    assert namespace == updated_data["namespace"]
    assert collection_name == updated_data["name"]
