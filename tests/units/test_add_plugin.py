"""Unit tests for ansible-creator add: plugins (action, filter, lookup, module, test)."""

from __future__ import annotations

import subprocess

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


@pytest.mark.parametrize("skip_collection_check", (False, True))
def test_error_invalid_collection_path(
    capsys: pytest.CaptureFixture[str], cli_args: ConfigDict, *, skip_collection_check: bool
) -> None:
    """Test Add.run().

    Check if collection exists.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        cli_args: Dictionary, partial Add class object.
        skip_collection_check: Whether to check for a valid collection.

    """
    cli_args["plugin_type"] = "lookup"
    cli_args["skip_collection_check"] = skip_collection_check
    add = Add(
        Config(**cli_args),
    )

    if skip_collection_check:
        add.run()
        result = capsys.readouterr().out
        assert "Note: Lookup plugin added to" in result
    else:
        with pytest.raises(CreatorError) as exc_info:
            add.run()
        assert (
            "is not a valid Ansible collection path. "
            "Please provide the root path of a valid ansible collection."
        ) in str(
            exc_info.value,
        )


@pytest.mark.parametrize(
    ("plugin_type", "plugin_name", "expected_message", "expected_file_path"),
    (
        (
            "action",
            "sample_action",
            "Note: Action plugin added to",
            "plugins/action/sample_action.py",
        ),
        (
            "action",
            "sample_action",
            "Note: Action plugin added to",
            "plugins/modules/sample_action.py",
        ),
        (
            "filter",
            "sample_filter",
            "Note: Filter plugin added to",
            "plugins/filter/sample_filter.py",
        ),
        (
            "lookup",
            "sample_lookup",
            "Note: Lookup plugin added to",
            "plugins/lookup/sample_lookup.py",
        ),
        (
            "module",
            "sample_module",
            "Note: Module plugin added to",
            "plugins/modules/sample_module.py",
        ),
        (
            "test",
            "sample_test",
            "Note: Test plugin added to",
            "plugins/test/sample_test.py",
        ),
    ),
)
def test_run_success_add_plugin(  # noqa: PLR0913,PLR0917 # pylint: disable=too-many-positional-arguments
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
    plugin_type: str,
    plugin_name: str,
    expected_message: str,
    expected_file_path: str,
) -> None:
    """Test Add.run().

    Successfully add plugin to path
    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.
        plugin_type: Type of the plugin to add.
        plugin_name: Name of the plugin to add.
        expected_message: Expected success message.
        expected_file_path: Expected file path for the plugin.

    """
    # prevents test from failing due to the help formatter wrapping the output
    monkeypatch.setenv("COLUMNS", "2048")
    cli_args["plugin_type"] = plugin_type
    cli_args["plugin_name"] = plugin_name
    add = Add(Config(**cli_args))

    # Mock the "_check_collection_path" method
    def mock_check_collection_path() -> None:
        """Mock function to skip checking collection path."""

    monkeypatch.setattr(
        Add,
        "_check_collection_path",
        staticmethod(mock_check_collection_path),
    )

    # Mock the "update_galaxy_dependency" method (for action plugin)
    def mock_update_galaxy_dependency() -> None:
        """Mock function to skip updating galaxy file."""

    monkeypatch.setattr(
        Add,
        "update_galaxy_dependency",
        staticmethod(mock_update_galaxy_dependency),
    )

    add.run()
    result = capsys.readouterr().out
    assert expected_message in result

    expected_file = tmp_path / expected_file_path
    effective_file = FIXTURES_DIR / "collection" / "testorg" / "testcol" / expected_file_path
    cmp_result = cmp(expected_file, effective_file, shallow=False)
    if not cmp_result:
        diff = subprocess.run(
            f"diff -u {expected_file} {effective_file}",
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )
        assert False, f"Files are different:\n{diff.stdout}"  # noqa: B011, PT015
    assert cmp_result

    # Test conflict handling
    conflict_file = tmp_path / expected_file_path
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

    # expect a warning followed by plugin addition msg
    # when response to overwrite is yes.
    monkeypatch.setattr("builtins.input", lambda _: "y")
    add.run()
    result = capsys.readouterr().out
    assert "already exists" in result, result
    assert expected_message in result


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
    cli_args["plugin_name"] = "sample_lookup"
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
    assert "Note: Lookup plugin added to" in result

    expected_file = tmp_path / "plugins" / "lookup" / "sample_lookup.py"
    effective_file = (
        FIXTURES_DIR
        / "collection"
        / "testorg"
        / "testcol"
        / "plugins"
        / "lookup"
        / "sample_lookup.py"
    )
    cmp_result = cmp(expected_file, effective_file, shallow=False)
    assert cmp_result

    conflict_file = tmp_path / "plugins" / "lookup" / "sample_lookup.py"
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
