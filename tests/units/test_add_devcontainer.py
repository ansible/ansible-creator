# cspell: ignore dcmp, subdcmp
"""Unit tests for ansible-creator add: devcontainer and execution-environment CI resources."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

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


def test_run_success_add_ee_ci(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test Add.run() for adding an EE CI workflow (default: GitHub Actions).

    Successfully adds EE CI workflow to path.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
        monkeypatch: Pytest monkeypatch fixture.

    """
    # Set the resource_type to ee-ci
    cli_args["resource_type"] = "ee-ci"
    add = Add(
        Config(**cli_args),
    )
    add.run()
    result = capsys.readouterr().out
    assert "Note: Resource added to" in result

    assert not (tmp_path / ".gitlab-ci.yml").exists()

    # Verify the generated ee-ci files match the expected structure
    expected_ci = tmp_path / ".github" / "workflows"
    effective_ci = FIXTURES_DIR / "common" / "ee-ci" / ".github" / "workflows"

    cmp_result = dircmp(expected_ci, effective_ci)
    diff = has_differences(dcmp=cmp_result, errors=[])
    assert diff == [], diff

    # Test for overwrite prompt and failure with no overwrite option
    conflict_file = tmp_path / ".github" / "workflows" / "ee-build.yml"
    conflict_file.write_text("name: conflict")

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

    # expect a warning followed by ee-ci resource creation msg
    # when response to overwrite is yes.
    monkeypatch.setattr("builtins.input", lambda _: "y")
    add.run()
    result = capsys.readouterr().out
    assert "already exists" in result, result
    assert "Note: Resource added to" in result


def test_run_success_add_ee_ci_gitlab(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Add.run() scaffolds GitLab CI for EE when ``scm_provider`` is gitlab.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Add class object.
    """
    cli_args["resource_type"] = "ee-ci"
    cli_args["scm_provider"] = "gitlab"
    add = Add(Config(**cli_args))
    add.run()
    result = capsys.readouterr().out
    assert "Note: Resource added to" in result

    assert not (tmp_path / ".github").exists()
    expected_gitlab_ci = tmp_path / ".gitlab-ci.yml"
    effective_gitlab_ci = FIXTURES_DIR / "common" / "ee-ci" / ".gitlab-ci.yml"
    assert expected_gitlab_ci.exists()
    assert cmp(expected_gitlab_ci, effective_gitlab_ci, shallow=False)


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
    # prevents test from failing due to the help formatter wrapping the output
    monkeypatch.setenv("COLUMNS", "2048")
    # Set the resource_type to devcontainer
    cli_args["resource_type"] = "devcontainer"
    cli_args["image"] = "auto"
    add = Add(
        Config(**cli_args),
    )
    add.run()
    result = capsys.readouterr().out
    assert "Note: Resource added to" in result

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
    assert "already exists" in result, result
    assert "Note: Resource added to" in result


@pytest.mark.skipif(
    sys.platform == "darwin"
    and os.environ.get("CI", "false") == "true"
    and not shutil.which("docker"),
    reason="Skip devcontainer test on CI macOS due to unavailability of docker.",
)
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
    assert "Note: Resource added to" in result

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
