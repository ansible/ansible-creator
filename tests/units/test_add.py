# cspell: ignore dcmp, subdcmp
"""Unit tests for ansible-creator add."""

from __future__ import annotations

import re

from filecmp import cmp, dircmp
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
        type: The type of the project for which the resource is being scaffolded.
        path: The file path where the resource should be added.
        force: Force overwrite of existing directory.
        overwrite: To overwrite files in an existing directory.
        no_overwrite: To not overwrite files in an existing directory.
    """

    creator_version: str
    output: Output
    subcommand: str
    resource_type: str
    type: str
    path: str
    force: bool
    overwrite: bool
    no_overwrite: bool


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
        "resource_type": "devfile",
        "path": str(tmp_path),
        "force": False,
        "overwrite": False,
        "no_overwrite": False,
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

    # expect a warning followed by playbook project creation msg
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
    add = Add(
        Config(**cli_args),
    )
    # Mock the _resource_type to bypass the validation step
    monkeypatch.setattr(add, "_resource_type", "unsupported_type")

    # Expect a CreatorError with the appropriate message
    with pytest.raises(CreatorError) as exc_info:
        add.run()
    assert "Unsupported resource type: unsupported_type" in str(exc_info.value)
