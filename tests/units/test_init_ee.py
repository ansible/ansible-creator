# cspell: ignore dcmp, subdcmp, microdnf
"""Unit tests for ansible-creator init execution environment projects."""

from __future__ import annotations

from filecmp import dircmp
from pathlib import Path
from typing import TypedDict

import pytest

from ansible_creator.config import Config
from ansible_creator.exceptions import CreatorError
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
        ee_config: Path to a JSON/YAML config file for EE parameters.
        base_image: Base image for execution environment.
        ee_collections: List of Ansible collections for execution environment.
        ee_python_deps: List of Python dependencies for execution environment.
        ee_system_packages: List of system packages for execution environment.
        ee_name: Name/tag for the execution environment image.
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
    base_image: str
    ee_collections: list[str]
    ee_python_deps: list[str]
    ee_system_packages: list[str]
    ee_name: str


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


def test_run_success_ee_project(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init.run() successfully creates new ee project.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "new_project")
    init = Init(Config(**cli_args))

    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    cmp = dircmp(
        str(tmp_path / "new_project"),
        str(FIXTURES_DIR / "project" / "ee_project"),
    )
    diff = has_differences(dcmp=cmp, errors=[])
    assert not diff, diff


def test_run_success_ee_project_with_params(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init.run() with dynamic EE parameters.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "custom_ee_project")
    cli_args["base_image"] = "quay.io/ansible/ee-minimal-rhel9:latest"
    cli_args["ee_collections"] = [
        "ansible.posix",
        "ansible.netcommon:>=1.0.0",
        "my.collection:1.0.0:galaxy:https://custom.galaxy.example.com",
    ]
    cli_args["ee_python_deps"] = ["requests", "boto3"]
    cli_args["ee_system_packages"] = ["git", "openssh-clients"]
    cli_args["ee_name"] = "my-custom-ee"

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "custom_ee_project" / "execution-environment.yml"
    assert ee_file.exists()

    ee_content = ee_file.read_text()

    assert "quay.io/ansible/ee-minimal-rhel9:latest" in ee_content
    assert "ansible.posix" in ee_content
    assert "ansible.netcommon" in ee_content
    assert '">=' in ee_content or ">=1.0.0" in ee_content
    assert "my.collection" in ee_content
    assert "type: galaxy" in ee_content
    assert "source: https://custom.galaxy.example.com" in ee_content
    assert "requests" in ee_content
    assert "boto3" in ee_content
    assert "git" in ee_content
    assert "openssh-clients" in ee_content
    assert "my-custom-ee" in ee_content


def test_ee_project_invalid_collection_name(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with invalid collection name format.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "invalid_ee_project")
    cli_args["ee_collections"] = ["invalid-collection-name"]

    with pytest.raises(CreatorError, match="Invalid collection name"):
        Init(Config(**cli_args))


def test_ee_project_invalid_collection_type(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with invalid collection type.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "invalid_ee_project")
    cli_args["ee_collections"] = ["ansible.posix:1.0.0:invalidtype"]

    with pytest.raises(CreatorError, match="Invalid collection type"):
        Init(Config(**cli_args))


def test_ee_project_invalid_collection_source_url(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with invalid collection source URL.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "invalid_ee_project")
    cli_args["ee_collections"] = ["ansible.posix:1.0.0:galaxy:https://"]

    with pytest.raises(CreatorError, match="Invalid source URL"):
        Init(Config(**cli_args))


def test_ee_project_collection_with_file_source(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with collection using file source (non-URL).

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_file_source")
    cli_args["ee_collections"] = ["ansible.posix:1.0.0:file:/path/to/collection"]

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_file_source" / "execution-environment.yml"
    ee_content = ee_file.read_text()

    assert "ansible.posix" in ee_content
    assert "type: file" in ee_content
    assert "source: /path/to/collection" in ee_content


def test_ee_project_with_config_file(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with EE config file.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    config_content = """
name: config-file-ee
base_image: registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel8:latest

collections:
  - name: ansible.netcommon
    version: ">=5.0.0"
  - name: ansible.utils

python_deps:
  - paramiko
  - netaddr

system_packages:
  - openssh-clients

options:
  package_manager_path: /usr/bin/microdnf

additional_build_files:
  - src: ansible.cfg
    dest: configs

additional_build_steps:
  prepend_base:
    - RUN mkdir -p /etc/ansible
  append_final:
    - COPY _build/configs/ansible.cfg /etc/ansible/ansible.cfg

ansible_cfg: |
  [galaxy]
  server_list = automation_hub

  [galaxy_server.automation_hub]
  url = https://console.redhat.com/api/automation-hub/content/published/
"""
    config_file = tmp_path / "ee-config.yaml"
    config_file.write_text(config_content)

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_from_config")
    cli_args["ee_config"] = str(config_file)

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_from_config" / "execution-environment.yml"
    ee_content = ee_file.read_text()

    assert "ee-minimal-rhel8" in ee_content
    assert "ansible.netcommon" in ee_content
    assert "ansible.utils" in ee_content
    assert "paramiko" in ee_content
    assert "openssh-clients" in ee_content
    assert "package_manager_path: /usr/bin/microdnf" in ee_content
    assert "config-file-ee" in ee_content
    assert "additional_build_files:" in ee_content
    assert "prepend_base:" in ee_content
    assert "append_final:" in ee_content

    ansible_cfg = tmp_path / "ee_from_config" / "ansible.cfg"
    assert ansible_cfg.exists()
    cfg_content = ansible_cfg.read_text()
    assert "automation_hub" in cfg_content


def test_ee_project_config_file_not_found(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with non-existent config file.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_missing_config")
    cli_args["ee_config"] = str(tmp_path / "nonexistent.yaml")

    with pytest.raises(CreatorError, match="EE config file not found"):
        Init(Config(**cli_args))


def test_ee_project_valid_json_config(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with valid JSON config file.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    config_content = '{"name": "json-ee", "collections": [{"name": "ansible.utils"}]}'
    config_file = tmp_path / "valid.json"
    config_file.write_text(config_content)

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_valid_json")
    cli_args["ee_config"] = str(config_file)

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_valid_json" / "execution-environment.yml"
    ee_content = ee_file.read_text()
    assert "json-ee" in ee_content
    assert "ansible.utils" in ee_content


def test_ee_project_invalid_json_config(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with invalid JSON config file.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    config_file = tmp_path / "invalid.json"
    config_file.write_text("{invalid json content")

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_invalid_json")
    cli_args["ee_config"] = str(config_file)

    with pytest.raises(CreatorError, match="Invalid JSON"):
        Init(Config(**cli_args))


def test_ee_project_invalid_yaml_config(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with invalid YAML config file.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("invalid: yaml: content: [")

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_invalid_yaml")
    cli_args["ee_config"] = str(config_file)

    with pytest.raises(CreatorError, match="Invalid YAML"):
        Init(Config(**cli_args))


def test_ee_project_config_collection_validation(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init validates collections from config file.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    config_content = """
collections:
  - name: invalid-collection
"""
    config_file = tmp_path / "invalid-collection.yaml"
    config_file.write_text(config_content)

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_invalid_config_collection")
    cli_args["ee_config"] = str(config_file)

    with pytest.raises(CreatorError, match="Invalid collection name"):
        Init(Config(**cli_args))


def test_ee_project_config_collection_missing_name(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with collection dict missing 'name' field.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    config_content = """
collections:
  - version: "1.0.0"
"""
    config_file = tmp_path / "missing-name.yaml"
    config_file.write_text(config_content)

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_missing_name")
    cli_args["ee_config"] = str(config_file)

    with pytest.raises(CreatorError, match="must have a 'name' field"):
        Init(Config(**cli_args))


def test_ee_project_config_collection_invalid_type(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with collection dict having invalid type.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    config_content = """
collections:
  - name: ansible.utils
    type: invalid_type
"""
    config_file = tmp_path / "invalid-type.yaml"
    config_file.write_text(config_content)

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_invalid_type")
    cli_args["ee_config"] = str(config_file)

    with pytest.raises(CreatorError, match="Invalid collection type"):
        Init(Config(**cli_args))


def test_ee_project_config_collection_invalid_source_url(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with collection dict having invalid source URL.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    config_content = """
collections:
  - name: ansible.utils
    source: "https://"
"""
    config_file = tmp_path / "invalid-url.yaml"
    config_file.write_text(config_content)

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_invalid_url")
    cli_args["ee_config"] = str(config_file)

    with pytest.raises(CreatorError, match="Invalid source URL"):
        Init(Config(**cli_args))


def test_ee_project_config_collection_valid_type_and_source(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with collection dict having valid type and source URL.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    config_content = """
collections:
  - name: ansible.utils
    type: galaxy
    source: "https://galaxy.ansible.com"
"""
    config_file = tmp_path / "valid-type-source.yaml"
    config_file.write_text(config_content)

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_valid_type_source")
    cli_args["ee_config"] = str(config_file)

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_valid_type_source" / "execution-environment.yml"
    ee_content = ee_file.read_text()
    assert "ansible.utils" in ee_content
    assert "type: galaxy" in ee_content
    assert "source: https://galaxy.ansible.com" in ee_content


def test_ee_project_official_image_microdnf(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test that official EE images automatically get microdnf as package manager.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_official_image")
    cli_args["base_image"] = (
        "registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel8:latest"
    )

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_official_image" / "execution-environment.yml"
    ee_content = ee_file.read_text()

    assert "package_manager_path: /usr/bin/microdnf" in ee_content


def test_ee_project_non_official_image_no_microdnf(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test that non-official images don't get microdnf automatically.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_fedora_image")

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_fedora_image" / "execution-environment.yml"
    ee_content = ee_file.read_text()

    assert "package_manager_path" not in ee_content


def test_ee_project_git_url_collection_cli(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with Git URL collection via CLI argument.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_git_url")
    cli_args["ee_collections"] = [
        "cisco.nxos",
        "https://${AAP_EE_BUILDER_GITHUB_MY_ORG}@github.com/my_org/my_ns.my_col:1.0.0:git",
    ]

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_git_url" / "execution-environment.yml"
    ee_content = ee_file.read_text()

    assert "cisco.nxos" in ee_content
    assert "https://${AAP_EE_BUILDER_GITHUB_MY_ORG}@github.com/my_org/my_ns.my_col" in ee_content
    assert "type: git" in ee_content
    assert "1.0.0" in ee_content


def test_ee_project_git_url_collection_config(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with Git URL collection via config file.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    config_content = """
collections:
  - name: cisco.nxos
  - name: https://${AAP_EE_BUILDER_GITHUB_MY_ORG}@github.com/my_org/my_ns.my_col
    type: git
    version: "1.0.0"
"""
    config_file = tmp_path / "git-url-config.yaml"
    config_file.write_text(config_content)

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_git_url_config")
    cli_args["ee_config"] = str(config_file)

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_git_url_config" / "execution-environment.yml"
    ee_content = ee_file.read_text()

    assert "cisco.nxos" in ee_content
    assert "https://${AAP_EE_BUILDER_GITHUB_MY_ORG}@github.com/my_org/my_ns.my_col" in ee_content
    assert "type: git" in ee_content


def test_ee_project_git_url_formats(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test various Git URL collection formats for full coverage.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_git_formats")
    cli_args["ee_collections"] = [
        # URL:git format (no version)
        "https://github.com/org/ns.col:git",
        # URL:version format (no explicit git type, assumes git)
        "https://github.com/org/ns.col2:2.0.0",
        # Plain URL format (no version, no git suffix)
        "https://github.com/org/ns.col3",
    ]

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_git_formats" / "execution-environment.yml"
    ee_content = ee_file.read_text()

    # URL:git format should have type but no version
    assert "https://github.com/org/ns.col" in ee_content
    assert "type: git" in ee_content

    # URL:version format should have version and assume git type
    assert "https://github.com/org/ns.col2" in ee_content
    assert "2.0.0" in ee_content

    # Plain URL format should work too
    assert "https://github.com/org/ns.col3" in ee_content
