# cspell: ignore dcmp, subdcmp
"""Unit tests for ansible-creator init decision environment projects."""

from __future__ import annotations

import json

from filecmp import dircmp
from pathlib import Path
from typing import TypedDict

import pytest

from ansible_creator.config import Config
from ansible_creator.output import Output
from ansible_creator.subcommands.init import Init
from ansible_creator.utils import TermFeatures
from tests.defaults import FIXTURES_DIR


class ConfigDict(TypedDict, total=False):
    """Type hint for Config dictionary.

    Attributes:
        creator_version: The version of the creator.
        output: The output object to use for logging.
        subcommand: The subcommand to execute.
        collection: The name of the collection.
        init_path: Path to initialize the project.
        project: The type of project to scaffold.
        force: Force overwrite of existing directory.
        overwrite: To overwrite files in an existing directory.
        no_overwrite: To not overwrite files in an existing directory.
        ee_config: Inline JSON string containing EE parameters.
        ee_config_file: Path to a JSON/YAML config file for EE parameters.
        base_image: Base image for execution environment.
        ee_collections: List of Ansible collections for execution environment.
        ee_python_deps: List of Python dependencies for execution environment.
        ee_system_packages: List of system packages for execution environment.
        ee_name: Name/tag for the execution environment image.
        ee_file_name: Name of the EE definition file.
        ee_build_arg_defaults: EE build ARG defaults as KEY=VALUE strings (CLI).
        registry_tls_verify: Whether to verify TLS for container registries.
        scm_provider: SCM provider for EE CI (github or gitlab).
    """

    creator_version: str
    output: Output
    subcommand: str
    collection: str
    init_path: str
    project: str
    force: bool
    overwrite: bool
    no_overwrite: bool
    ee_config: str | None
    ee_config_file: str | None
    base_image: str
    ee_collections: list[str]
    ee_python_deps: list[str]
    ee_system_packages: list[str]
    ee_name: str
    ee_file_name: str
    ee_build_arg_defaults: list[str]
    registry_tls_verify: bool | None
    scm_provider: str


@pytest.fixture(name="output")
def fixture_output() -> Output:
    """Create an Output class object as fixture.

    Returns:
        Output class object.
    """
    return Output(
        display="text",
        log_file=str(Path.cwd() / "ansible-creator.log"),
        log_level="notset",
        log_append="false",
        term_features=TermFeatures(color=False, links=False),
        verbosity=0,
    )


@pytest.fixture(name="cli_args")
def fixture_cli_args(tmp_path: Path, output: Output) -> ConfigDict:
    """Create a dict to use for a Init class object as fixture.

    Args:
        tmp_path: Temporary directory path.
        output: Output class object.

    Returns:
        ConfigDict: Dictionary with Init class arguments.
    """
    return {
        "creator_version": "0.0.1",
        "output": output,
        "subcommand": "init",
        "collection": "testorg.testcol",
        "init_path": str(tmp_path),
        "project": "",
        "force": False,
        "overwrite": False,
        "no_overwrite": False,
        "scm_provider": "github",
    }


def has_differences(dcmp: dircmp[str], errors: list[str]) -> list[str]:
    """Recursively check for differences in dircmp object.

    Args:
        dcmp: dircmp object.
        errors: List of errors.

    Returns:
        List of errors.
    """
    errors.extend([f"Only in {dcmp.left}: {f}" for f in dcmp.left_only])
    errors.extend([f"Only in {dcmp.right}: {f}" for f in dcmp.right_only])
    errors.extend([f"Diff files: {dcmp.diff_files}" for _ in dcmp.diff_files])
    for subdcmp in dcmp.subdirs.values():
        has_differences(subdcmp, errors)
    return errors


def test_run_success_de_project(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Init decision_environment applies DE defaults (base image, deps, collections).

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "decision_environment"
    cli_args["init_path"] = str(tmp_path / "de_project")
    init = Init(Config(**cli_args))

    init.run()
    result = capsys.readouterr().out

    assert r"Note: decision_environment project created" in result

    cmp = dircmp(
        str(tmp_path / "de_project"),
        str(FIXTURES_DIR / "project" / "de_project"),
    )
    diff = has_differences(dcmp=cmp, errors=[])
    assert not diff, diff


def test_de_project_cli_override(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    output: Output,
) -> None:
    """CLI flags override DE defaults when init decision_environment.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        output: Output object for logging.
    """
    dest = tmp_path / "de_override"
    config = Config(
        creator_version="0.0.1",
        output=output,
        subcommand="init",
        project="decision_environment",
        init_path=str(dest),
        base_image="my-custom-de:latest",
        ee_name="custom_de",
        scm_provider="github",
    )
    Init(config=config).run()
    result = capsys.readouterr().out

    assert r"Note: decision_environment project created" in result

    ee_yml = dest / "execution-environment.yml"
    content = ee_yml.read_text()
    assert "my-custom-de:latest" in content
    assert "custom_de" in content
    assert "ansible-rulebook" in content
    assert "ansible.eda" in content


def test_de_project_with_config_file(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    output: Output,
) -> None:
    """Config file takes full precedence over DE defaults.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        output: Output object for logging.
    """
    config_data = {
        "base_image": "custom-from-file:latest",
        "ee_name": "file_de",
        "collections": [{"name": "ansible.netcommon"}],
    }
    config_path = tmp_path / "de-config.json"
    config_path.write_text(json.dumps(config_data))

    dest = tmp_path / "de_from_file"
    config = Config(
        creator_version="0.0.1",
        output=output,
        subcommand="init",
        project="decision_environment",
        init_path=str(dest),
        ee_config_file=str(config_path),
        scm_provider="github",
    )
    Init(config=config).run()
    result = capsys.readouterr().out

    assert r"Note: decision_environment project created" in result

    ee_yml = dest / "execution-environment.yml"
    content = ee_yml.read_text()
    assert "custom-from-file:latest" in content
    assert "file_de" in content
    assert "ansible.netcommon" in content
    assert "ansible-rulebook" not in content
    assert "ansible.eda" not in content
