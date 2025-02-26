# cspell: ignore dcmp, subdcmp
"""Unit tests for ansible-creator add."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys

from filecmp import cmp, dircmp
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
    }


def has_differences(dcmp: dircmp[str], errors: list[str]) -> list[str]:
    """Recursively check for differences in dircmp object.

    Args:
        dcmp: dircmp object.
        errors: List of errors.

    Returns:
        list: List of errors.
    """
    errors.extend([f"Only in {dcmp.left}: {f}" for f in dcmp.left_only])
    errors.extend([f"Only in {dcmp.right}: {f}" for f in dcmp.right_only])
    errors.extend(
        [f"Differing files: {dcmp.left}/{f} {dcmp.right}/{f}" for f in dcmp.diff_files],
    )
    for subdcmp in dcmp.subdirs.values():
        errors = has_differences(subdcmp, errors)
    return errors


def test_run_success_add_devfile(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run().

    Successfully add devfile to path

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.
    """
    cli_args["resource_type"] = "devfile"
    add = Add(
        Config(**cli_args),
    )

    # Mock the "unique_name_in_devfile" method
    def mock_unique_name_in_devfile() -> str:
        """Mock function to generate a unique name for use in a devfile.

        Returns:
            str: A placeholder name, "testorg".
        """
        return "testorg"

    with pytest.MonkeyPatch.context() as mp:
        # Apply the mock
        mp.setattr(
            Add,
            "unique_name_in_devfile",
            staticmethod(mock_unique_name_in_devfile),
        )
        add.run()
    result = capsys.readouterr().out
    assert re.search("Note: Resource added to", result) is not None

    expected_devfile = tmp_path / "devfile.yaml"
    effective_devfile = FIXTURES_DIR / "common" / "devfile" / "devfile.yaml"
    cmp_result = cmp(expected_devfile, effective_devfile, shallow=False)
    assert cmp_result

    conflict_file = tmp_path / "devfile.yaml"
    conflict_file.write_text("schemaVersion: 2.2.2")

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

    # expect a warning followed by devfile resource creation msg
    # when response to overwrite is yes.
    monkeypatch.setattr("builtins.input", lambda _: "y")
    add.run()
    result = capsys.readouterr().out
    assert (
        re.search(
            "already exists",
            result,
        )
        is not None
    ), result
    assert re.search("Note: Resource added to", result) is not None


def test_run_error_no_overwrite(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Add.run().

    Successfully add devfile to path

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
    """
    cli_args["resource_type"] = "devfile"
    add = Add(
        Config(**cli_args),
    )

    # Mock the "unique_name_in_devfile" method
    def mock_unique_name_in_devfile() -> str:
        """Mock function to generate a unique name for use in a devfile.

        Returns:
            str: A placeholder name, "testorg".
        """
        return "testorg"

    with pytest.MonkeyPatch.context() as mp:
        # Apply the mock
        mp.setattr(
            Add,
            "unique_name_in_devfile",
            staticmethod(mock_unique_name_in_devfile),
        )
        add.run()
    result = capsys.readouterr().out
    assert re.search("Note: Resource added to", result) is not None

    expected_devfile = tmp_path / "devfile.yaml"
    effective_devfile = FIXTURES_DIR / "common" / "devfile" / "devfile.yaml"
    cmp_result = cmp(expected_devfile, effective_devfile, shallow=False)
    assert cmp_result

    conflict_file = tmp_path / "devfile.yaml"
    conflict_file.write_text("schemaVersion: 2.2.2")

    cli_args["no_overwrite"] = True
    add = Add(
        Config(**cli_args),
    )
    with pytest.raises(CreatorError) as exc_info:
        add.run()
    assert "Please re-run ansible-creator with --overwrite to continue." in str(exc_info.value)


def test_error_invalid_path(
    cli_args: ConfigDict,
) -> None:
    """Test Add.run().

    Successfully add devfile to path

    Args:
        cli_args: Dictionary, partial Add class object.
    """
    cli_args["resource_type"] = "devfile"
    cli_args["path"] = "/invalid"
    add = Add(
        Config(**cli_args),
    )

    with pytest.raises(CreatorError) as exc_info:
        add.run()
    assert "does not exist. Please provide an existing directory" in str(exc_info.value)


def test_error_invalid_collection_path(
    cli_args: ConfigDict,
) -> None:
    """Test Add.run().

    Check if collection exists.

    Args:
        cli_args: Dictionary, partial Add class object.
    """
    cli_args["plugin_type"] = "lookup"
    add = Add(
        Config(**cli_args),
    )

    with pytest.raises(CreatorError) as exc_info:
        add.run()
    assert (
        "is not a valid Ansible collection path. "
        "Please provide the root path of a valid ansible collection."
    ) in str(
        exc_info.value,
    )


def test_run_error_unsupported_resource_type(
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run() with an unsupported resource type.

    This test checks if the CreatorError is raised when an unsupported
    resource type is provided.

    Args:
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.
    """
    cli_args["resource_type"] = "devfile"
    add = Add(
        Config(**cli_args),
    )
    # Mock the _resource_type to bypass the validation step
    monkeypatch.setattr(add, "_resource_type", "unsupported_type")

    # Expect a CreatorError with the appropriate message
    with pytest.raises(CreatorError) as exc_info:
        add.run()
    assert "Unsupported resource type: unsupported_type" in str(exc_info.value)


def test_run_success_add_devcontainer(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run() for adding a devcontainer.

    Successfully adds devcontainer to path.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.
    """
    # Set the resource_type to devcontainer
    cli_args["resource_type"] = "devcontainer"
    cli_args["image"] = "auto"
    add = Add(
        Config(**cli_args),
    )
    add.run()
    result = capsys.readouterr().out
    assert re.search("Note: Resource added to", result) is not None

    # Verify the generated devcontainer files match the expected structure
    expected_devcontainer = tmp_path / ".devcontainer"
    effective_devcontainer = FIXTURES_DIR / "collection" / "testorg" / "testcol" / ".devcontainer"

    cmp_result = dircmp(expected_devcontainer, effective_devcontainer)
    diff = has_differences(dcmp=cmp_result, errors=[])
    assert diff == [], diff

    # Test for overwrite prompt and failure with no overwrite option
    conflict_file = tmp_path / ".devcontainer" / "devcontainer.json"
    conflict_file.write_text('{ "name": "conflict" }')

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

    # expect a warning followed by devcontainer resource creation msg
    # when response to overwrite is yes.
    monkeypatch.setattr("builtins.input", lambda _: "y")
    add.run()
    result = capsys.readouterr().out
    assert (
        re.search(
            "already exists",
            result,
        )
        is not None
    ), result
    assert re.search("Note: Resource added to", result) is not None


# Skip this test on macOS due to unavailability of docker on macOS GHA runners
@pytest.mark.skipif(sys.platform == "darwin", reason="Skip test on macOS")
def test_devcontainer_usability(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Add.run() for adding a devcontainer.

    Successfully adds devcontainer to path.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.

    Raises:
        FileNotFoundError: If the 'npm' or 'docker' executable is not found in the PATH.
    """
    # Set the resource_type to devcontainer
    cli_args["resource_type"] = "devcontainer"
    cli_args["image"] = "auto"
    add = Add(
        Config(**cli_args),
    )
    add.run()
    result = capsys.readouterr().out
    assert re.search("Note: Resource added to", result) is not None

    npm_executable = shutil.which("npm")
    if not npm_executable:
        err = "npm executable not found in PATH"
        raise FileNotFoundError(err)

    # Start the devcontainer using devcontainer CLI
    devcontainer_up_cmd = (
        f"devcontainer up --workspace-folder {tmp_path} --remove-existing-container"
    )
    devcontainer_up_output = subprocess.run(  # noqa: S603
        [
            npm_executable,
            "exec",
            "-c",
            devcontainer_up_cmd,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert devcontainer_up_output.returncode == 0

    devcontainer_id = json.loads(devcontainer_up_output.stdout.strip("\n")).get("containerId")

    # Execute the command within the container
    devcontainer_exec_cmd = f"devcontainer exec --container-id {devcontainer_id} adt --version"
    devcontainer_exec_output = subprocess.run(  # noqa: S603
        [npm_executable, "exec", "-c", devcontainer_exec_cmd],
        capture_output=True,
        text=True,
        check=True,
    )
    assert devcontainer_exec_output.returncode == 0

    docker_executable = shutil.which("docker")
    if not docker_executable:
        err = "docker executable not found in PATH"
        raise FileNotFoundError(err)
    # Stop devcontainer
    stop_container = subprocess.run(  # noqa: S603
        [docker_executable, "rm", "-f", devcontainer_id],
        capture_output=True,
        text=True,
        check=True,
    )
    assert stop_container.returncode == 0


def test_run_success_add_plugin_filter(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run().

    Successfully add plugin to path
    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.
    """
    cli_args["plugin_type"] = "filter"
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
    add.run()
    result = capsys.readouterr().out
    assert re.search("Note: Filter plugin added to", result) is not None

    expected_file = tmp_path / "plugins" / "filter" / "hello_world.py"
    effective_file = (
        FIXTURES_DIR
        / "collection"
        / "testorg"
        / "testcol"
        / "plugins"
        / "filter"
        / "hello_world.py"
    )
    cmp_result = cmp(expected_file, effective_file, shallow=False)
    assert cmp_result

    conflict_file = tmp_path / "plugins" / "filter" / "hello_world.py"
    conflict_file.write_text("Author: Your Name")

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

    # expect a warning followed by filter plugin addition msg
    # when response to overwrite is yes.
    monkeypatch.setattr("builtins.input", lambda _: "y")
    add.run()
    result = capsys.readouterr().out
    assert (
        re.search(
            "already exists",
            result,
        )
        is not None
    ), result
    assert re.search("Note: Filter plugin added to", result) is not None


def test_run_success_add_plugin_lookup(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run().

    Successfully add plugin to path

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.
    """
    cli_args["plugin_type"] = "lookup"
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
    add.run()
    result = capsys.readouterr().out
    assert re.search("Note: Lookup plugin added to", result) is not None

    expected_file = tmp_path / "plugins" / "lookup" / "hello_world.py"
    effective_file = (
        FIXTURES_DIR
        / "collection"
        / "testorg"
        / "testcol"
        / "plugins"
        / "lookup"
        / "hello_world.py"
    )
    cmp_result = cmp(expected_file, effective_file, shallow=False)
    assert cmp_result

    conflict_file = tmp_path / "plugins" / "lookup" / "hello_world.py"
    conflict_file.write_text("Author: Your Name")

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

    # expect a warning followed by lookup plugin addition msg
    # when response to overwrite is yes.
    monkeypatch.setattr("builtins.input", lambda _: "y")
    add.run()
    result = capsys.readouterr().out
    assert (
        re.search(
            "already exists",
            result,
        )
        is not None
    ), result
    assert re.search("Note: Lookup plugin added to", result) is not None


def test_run_success_add_plugin_action(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run().

    Successfully add plugin to path
    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.
    """
    cli_args["plugin_type"] = "action"
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

    # Mock the "update_galaxy_dependency" method
    def mock_update_galaxy_dependency() -> None:
        """Mock function to skip updating galaxy file."""

    monkeypatch.setattr(
        Add,
        "update_galaxy_dependency",
        staticmethod(mock_update_galaxy_dependency),
    )

    add.run()
    result = capsys.readouterr().out
    assert re.search("Note: Action plugin added to", result) is not None

    expected_plugin_file = tmp_path / "plugins" / "action" / "hello_world.py"
    expected_module_file = tmp_path / "plugins" / "modules" / "hello_world.py"
    effective_plugin_file = (
        FIXTURES_DIR
        / "collection"
        / "testorg"
        / "testcol"
        / "plugins"
        / "action"
        / "hello_world.py"
    )
    effective_module_file = (
        FIXTURES_DIR
        / "collection"
        / "testorg"
        / "testcol"
        / "plugins"
        / "modules"
        / "hello_world.py"
    )
    cmp_result1 = cmp(expected_plugin_file, effective_plugin_file, shallow=False)
    cmp_result2 = cmp(expected_module_file, effective_module_file, shallow=False)
    assert cmp_result1, cmp_result2


def test_run_success_add_plugin_module(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run().

    Successfully add plugin to path

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.
    """
    cli_args["plugin_type"] = "module"
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
    add.run()
    result = capsys.readouterr().out
    assert re.search("Note: Module plugin added to", result) is not None

    expected_file = tmp_path / "plugins" / "sample_module" / "hello_world.py"
    effective_file = (
        FIXTURES_DIR
        / "collection"
        / "testorg"
        / "testcol"
        / "plugins"
        / "sample_module"
        / "hello_world.py"
    )
    cmp_result = cmp(expected_file, effective_file, shallow=False)
    assert cmp_result

    conflict_file = tmp_path / "plugins" / "sample_module" / "hello_world.py"
    conflict_file.write_text("Author: Your Name")

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

    # expect a warning followed by module plugin addition msg
    # when response to overwrite is yes.
    monkeypatch.setattr("builtins.input", lambda _: "y")
    add.run()
    result = capsys.readouterr().out
    assert (
        re.search(
            "already exists",
            result,
        )
        is not None
    ), result
    assert re.search("Note: Module plugin added to", result) is not None


def test_run_error_plugin_no_overwrite(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run().

    Successfully add devfile to path

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.
    """
    cli_args["plugin_type"] = "lookup"
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
    add.run()
    result = capsys.readouterr().out
    assert re.search("Note: Lookup plugin added to", result) is not None

    expected_file = tmp_path / "plugins" / "lookup" / "hello_world.py"
    effective_file = (
        FIXTURES_DIR
        / "collection"
        / "testorg"
        / "testcol"
        / "plugins"
        / "lookup"
        / "hello_world.py"
    )
    cmp_result = cmp(expected_file, effective_file, shallow=False)
    assert cmp_result

    conflict_file = tmp_path / "plugins" / "lookup" / "hello_world.py"
    conflict_file.write_text("name: Your Name")

    cli_args["no_overwrite"] = True
    add = Add(
        Config(**cli_args),
    )
    with pytest.raises(CreatorError) as exc_info:
        add.run()
    assert "Please re-run ansible-creator with --overwrite to continue." in str(exc_info.value)


def test_run_error_unsupported_plugin_type(
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run() with an unsupported plugin type.

    This test checks if the CreatorError is raised when an unsupported
    resource type is provided.

    Args:
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.
    """
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
    monkeypatch.setattr(add, "_plugin_type", "unsupported_type")

    # Expect a CreatorError with the appropriate message
    with pytest.raises(CreatorError) as exc_info:
        add.run()
    assert "Unsupported plugin type: unsupported_type" in str(exc_info.value)


def test_run_success_add_execution_env(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run() for adding a execution-environment sample file.

    Successfully adds execution-environment.yml sample file to path.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.
    """
    # Set the resource_type to execution-environment
    cli_args["resource_type"] = "execution-environment"
    add = Add(
        Config(**cli_args),
    )
    add.run()
    result = capsys.readouterr().out
    assert re.search("Note: Resource added to", result) is not None

    # Verify the generated execution-environment file match the expected structure
    expected_ee_file = tmp_path / "execution-environment.yml"
    effective_ee_file = (
        FIXTURES_DIR / "common" / "execution-environment" / "execution-environment.yml"
    )

    cmp_result = cmp(expected_ee_file, effective_ee_file, shallow=False)
    assert cmp_result

    # Test for overwrite prompt and failure with no overwrite option
    conflict_file = tmp_path / "execution-environment.yml"
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
    assert (
        re.search(
            "already exists",
            result,
        )
        is not None
    ), result
    assert re.search("Note: Resource added to", result) is not None


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
