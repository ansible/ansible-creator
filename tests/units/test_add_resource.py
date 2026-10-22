"""Unit tests for ansible-creator add: simple file resources (devfile, ai, playbook, etc.)."""

from __future__ import annotations

from filecmp import cmp
from typing import TYPE_CHECKING, TypedDict

import pytest

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
        return "testorg.testcol"

    with pytest.MonkeyPatch.context() as mp:
        # Apply the mock
        mp.setattr(
            Add,
            "unique_name_in_devfile",
            staticmethod(mock_unique_name_in_devfile),
        )
        add.run()
    result = capsys.readouterr().out
    assert "Note: Resource added to" in result

    expected_devfile = tmp_path / "devfile.yaml"
    effective_devfile = FIXTURES_DIR / "collection" / "testorg" / "testcol" / "devfile.yaml"
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
    # Check for "already" and "exists" separately since they might be on different lines
    assert "already" in result, result
    assert "exists" in result, result
    assert "Note: Resource added to" in result


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
        return "testorg.testcol"

    with pytest.MonkeyPatch.context() as mp:
        # Apply the mock
        mp.setattr(
            Add,
            "unique_name_in_devfile",
            staticmethod(mock_unique_name_in_devfile),
        )
        add.run()
    result = capsys.readouterr().out
    assert "Note: Resource added to" in result

    expected_devfile = tmp_path / "devfile.yaml"
    effective_devfile = FIXTURES_DIR / "collection" / "testorg" / "testcol" / "devfile.yaml"
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


def test_run_success_add_ai(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Add.run() for adding AI files.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.

    """
    cli_args["resource_type"] = "ai"
    add = Add(
        Config(**cli_args),
    )
    add.run()
    result = capsys.readouterr().out
    assert "Note: Resource added to" in result
    expected_file = tmp_path / "AGENTS.md"
    assert expected_file.exists()
    assert not expected_file.is_symlink()
    content = expected_file.read_text()
    assert len(content) > 0


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
    assert "Note: Resource added to" in result

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
    assert "already exists" in result, result
    assert "Note: Resource added to" in result


def test_run_success_add_playbook(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Add.run() for adding a sample playbook file.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
    """
    cli_args["resource_type"] = "playbook"
    add = Add(
        Config(**cli_args),
    )
    add.run()
    result = capsys.readouterr().out
    assert "Note: Resource added to" in result

    playbook = tmp_path / "playbook.yml"
    assert playbook.exists()
    content = playbook.read_text()
    assert "name: Example playbook" in content
    assert "hosts: localhost" in content
    assert "ansible.builtin.debug" in content


def test_run_success_add_play_argspec(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run() for adding play-argspec sample files.

    Successfully adds playbook argspec sample files to path.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.

    """
    # Set the resource_type to play-argspec
    cli_args["resource_type"] = "play-argspec"
    add = Add(
        Config(**cli_args),
    )
    add.run()
    result = capsys.readouterr().out
    assert "Note: Resource added to" in result

    # Verify the generated play-argspec files match the expected structure and content
    argspec_file_paths = [
        "argspec_validation_plays.yml",
        "argspec_validation_plays.meta.yml",
        "inventory/argspec_validation_inventory.yml",
    ]

    for file_path in argspec_file_paths:
        expected_file = tmp_path / file_path
        effective_file = FIXTURES_DIR / "project" / "playbook_project" / file_path
        cmp_file_result = cmp(expected_file, effective_file, shallow=False)
        assert cmp_file_result

    # Test for overwrite prompt and failure with no overwrite option, then confirm overwrite
    conflict_file = tmp_path / "argspec_validation_plays.yml"
    conflict_file.write_text('{ "version": "1" }')

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

    monkeypatch.setattr("builtins.input", lambda _: "y")
    add.run()
    result = capsys.readouterr().out
    assert "already exists" in result, result
    assert "Note: Resource added to" in result
