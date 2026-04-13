# cspell: ignore dcmp, subdcmp, microdnf
# pylint: disable=too-many-lines
"""Unit tests for ansible-creator init execution environment projects."""

from __future__ import annotations

import argparse
import json

from filecmp import dircmp
from pathlib import Path
from typing import TypedDict

import pytest

from ansible_creator.config import Config
from ansible_creator.exceptions import CreatorError
from ansible_creator.output import Output
from ansible_creator.schema import _extract_action_info, for_command
from ansible_creator.subcommands.init import Init
from ansible_creator.types import EECollection, EEConfig, GalaxyServer, ScmServer
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


def _galaxy_server_ini_section(ansible_cfg: str, server_id: str) -> str:
    """Return the body of a ``[galaxy_server.<server_id>]`` INI section.

    The slice starts immediately after the header line and ends before the next
    ``[`` at the beginning of a line (next section) or EOF.

    Args:
        ansible_cfg: Full ``ansible.cfg`` file contents.
        server_id: Galaxy server id matching the section name.

    Returns:
        Text after ``[galaxy_server.<server_id>]`` through the line before the
        next section header.
    """
    header = f"[galaxy_server.{server_id}]"
    start = ansible_cfg.index(header) + len(header)
    tail = ansible_cfg[start:]
    next_idx = tail.find("\n[")
    if next_idx == -1:
        return tail
    return tail[:next_idx]


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
    cli_args["ee_file_name"] = "my-ee.yml"

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "custom_ee_project" / "my-ee.yml"
    assert ee_file.exists()
    assert not (tmp_path / "custom_ee_project" / "execution-environment.yml").exists()

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


def test_run_success_ee_project_with_build_arg_defaults_cli(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init.run() writes build_arg_defaults from CLI.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_pre")
    cli_args["ee_build_arg_defaults"] = ["ANSIBLE_GALAXY_CLI_COLLECTION_OPTS=--pre"]

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_pre" / "execution-environment.yml"
    ee_content = ee_file.read_text()
    assert "build_arg_defaults:" in ee_content
    assert "ANSIBLE_GALAXY_CLI_COLLECTION_OPTS" in ee_content
    assert "--pre" in ee_content


def test_ee_project_build_arg_defaults_cli_invalid(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init rejects malformed ee_build_arg_defaults entries.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_bad_arg")
    cli_args["ee_build_arg_defaults"] = ["not-key-value"]

    with pytest.raises(CreatorError, match="Invalid --ee-build-arg-default"):
        Init(Config(**cli_args))


def test_ee_project_build_arg_defaults_cli_empty_key(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init rejects KEY=VALUE when KEY is empty (e.g. ``=value``).

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_empty_key")
    cli_args["ee_build_arg_defaults"] = ["=only-a-value"]

    with pytest.raises(CreatorError, match="empty key"):
        Init(Config(**cli_args))


def test_ee_project_build_arg_defaults_merge_config_and_cli(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """CLI build_arg_defaults overlay values from --ee-config.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_merge")
    cli_args["ee_config"] = json.dumps(
        {
            "build_arg_defaults": {
                "ANSIBLE_GALAXY_CLI_COLLECTION_OPTS": "--stable",
                "OTHER_ARG": "x",
            },
        },
    )
    cli_args["ee_build_arg_defaults"] = ["ANSIBLE_GALAXY_CLI_COLLECTION_OPTS=--pre"]

    init = Init(Config(**cli_args))
    init.run()
    assert r"Note: execution_env project created" in capsys.readouterr().out

    ee_content = (tmp_path / "ee_merge" / "execution-environment.yml").read_text()
    assert "--pre" in ee_content
    assert "OTHER_ARG" in ee_content
    assert "x" in ee_content
    assert "--stable" not in ee_content


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
    cli_args["ee_config_file"] = str(config_file)

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


def test_ee_project_inline_json_config(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with inline JSON via --ee-config.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    config_data = {
        "name": "inline-json-ee",
        "base_image": "quay.io/fedora/fedora:41",
        "collections": [{"name": "ansible.posix"}],
        "python_deps": ["jmespath"],
        "system_packages": ["git"],
    }

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_inline_json")
    cli_args["ee_config"] = json.dumps(config_data)

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_inline_json" / "execution-environment.yml"
    ee_content = ee_file.read_text()

    assert "inline-json-ee" in ee_content
    assert "ansible.posix" in ee_content
    assert "jmespath" in ee_content
    assert "git" in ee_content


def test_ee_project_inline_json_invalid(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init with invalid inline JSON via --ee-config.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_bad_json")
    cli_args["ee_config"] = "{not valid json"

    with pytest.raises(CreatorError, match="Invalid JSON in --ee-config"):
        Init(Config(**cli_args))


def test_ee_project_inline_json_not_object(
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init rejects non-object JSON via --ee-config.

    Args:
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_list_json")
    cli_args["ee_config"] = '["not", "an", "object"]'

    with pytest.raises(CreatorError, match="must be a JSON object"):
        Init(Config(**cli_args))


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
    cli_args["ee_config_file"] = str(tmp_path / "nonexistent.yaml")

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
    cli_args["ee_config_file"] = str(config_file)

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
    cli_args["ee_config_file"] = str(config_file)

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
    cli_args["ee_config_file"] = str(config_file)

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
    cli_args["ee_config_file"] = str(config_file)

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
    cli_args["ee_config_file"] = str(config_file)

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
    cli_args["ee_config_file"] = str(config_file)

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
    cli_args["ee_config_file"] = str(config_file)

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
    cli_args["ee_config_file"] = str(config_file)

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
    """Test that official EE images get minimal skeleton without ansible_core/runner.

    Official EE images already have ansible-core and ansible-runner pre-installed,
    so we should not include them in the EE definition to avoid conflicts.

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

    # Official EE images should have microdnf
    assert "package_manager_path: /usr/bin/microdnf" in ee_content

    # Official EE images should NOT have ansible_core/ansible_runner (pre-installed)
    assert "ansible_core:" not in ee_content
    assert "ansible_runner:" not in ee_content
    assert "package_pip: ansible-core" not in ee_content
    assert "package_pip: ansible-runner" not in ee_content

    # Should have python_interpreter with python3.11 for official EE images
    assert "python_interpreter:" in ee_content
    assert "python_path: /usr/bin/python3.12" in ee_content

    # Official EE images should NOT have pip upgrade or the default sample tag
    assert "RUN $PYCMD -m pip install -U pip" not in ee_content
    assert "ansible_sample_ee" not in ee_content

    # Without galaxy_servers and no custom build steps, additional_build_steps
    # should be omitted entirely for official images
    assert "additional_build_steps:" not in ee_content

    # Without galaxy_servers, no ansible.cfg or prepend_galaxy should be generated
    assert "prepend_galaxy:" not in ee_content
    ansible_cfg_file = tmp_path / "ee_official_image" / "ansible.cfg"
    assert not ansible_cfg_file.exists()


def test_ee_project_with_galaxy_servers(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test scaffolding with galaxy_servers generates ansible.cfg and token plumbing.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    galaxy_config = {
        "base_image": "registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel8:latest",
        "galaxy_servers": [
            {
                "id": "automation_hub",
                "url": "https://console.redhat.com/api/automation-hub/content/published/",
                "auth_url": "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token",
                "token_required": True,
            },
            {
                "id": "private_hub",
                "url": "https://pah.corp.example.com/api/galaxy/content/published/",
                "token_required": True,
                "validate_certs": False,
            },
            {
                "id": "galaxy",
                "url": "https://galaxy.ansible.com/",
            },
        ],
    }

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_galaxy")
    cli_args["ee_config"] = json.dumps(galaxy_config)

    Init(Config(**cli_args)).run()
    capsys.readouterr()

    # ansible.cfg should be generated from galaxy_servers
    ansible_cfg_file = tmp_path / "ee_galaxy" / "ansible.cfg"
    assert ansible_cfg_file.exists()
    cfg = ansible_cfg_file.read_text()

    assert "server_list = automation_hub, private_hub, galaxy" in cfg
    assert "[galaxy_server.automation_hub]" in cfg
    assert "console.redhat.com/api/automation-hub" in cfg
    assert "auth_url = https://sso.redhat.com/" in cfg
    assert "[galaxy_server.private_hub]" in cfg
    assert "pah.corp.example.com" in cfg
    private_hub_section = _galaxy_server_ini_section(cfg, "private_hub")
    assert "validate_certs = false" in private_hub_section
    assert private_hub_section.count("validate_certs = false") == 1
    assert "validate_certs = false" not in _galaxy_server_ini_section(cfg, "automation_hub")
    assert "validate_certs = false" not in _galaxy_server_ini_section(cfg, "galaxy")
    assert cfg.count("validate_certs = false") == 1
    assert "[galaxy_server.galaxy]" in cfg
    assert "galaxy.ansible.com" in cfg
    # Token comments for servers with token_required
    assert "# Token: set ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN" in cfg
    assert "# Token: set ANSIBLE_GALAXY_SERVER_PRIVATE_HUB_TOKEN" in cfg
    # No token values should appear in ansible.cfg
    assert "token =" not in cfg
    assert "token=" not in cfg

    # EE definition should have ARG directives for token servers
    ee_file = tmp_path / "ee_galaxy" / "execution-environment.yml"
    ee_content = ee_file.read_text()
    assert "prepend_galaxy:" in ee_content
    assert "ARG ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN" in ee_content
    assert "ARG ANSIBLE_GALAXY_SERVER_PRIVATE_HUB_TOKEN" in ee_content
    # Galaxy server (no token) should NOT have an ARG
    assert "ARG ANSIBLE_GALAXY_SERVER_GALAXY_TOKEN" not in ee_content

    # Workflow should reference the token env vars
    wf_file = tmp_path / "ee_galaxy" / ".github" / "workflows" / "ee-build.yml"
    wf_content = wf_file.read_text()
    assert "ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN" in wf_content
    assert "ANSIBLE_GALAXY_SERVER_PRIVATE_HUB_TOKEN" in wf_content


def test_ee_project_no_galaxy_servers_no_ansible_cfg(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test that no ansible.cfg is generated when galaxy_servers is empty.

    This applies even when the base image is an official Red Hat EE image.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_no_servers")
    cli_args["base_image"] = (
        "registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel8:latest"
    )

    Init(Config(**cli_args)).run()
    capsys.readouterr()

    ansible_cfg_file = tmp_path / "ee_no_servers" / "ansible.cfg"
    assert not ansible_cfg_file.exists()

    ee_content = (tmp_path / "ee_no_servers" / "execution-environment.yml").read_text()
    assert "prepend_galaxy:" not in ee_content


def test_ee_project_no_overwrite_ansible_cfg(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test that --no-overwrite skips existing ansible.cfg when galaxy_servers are set.

    Pre-plant only ``ansible.cfg`` (not the template files) so the copier
    ``has_conflicts()`` check passes, letting ``_write_optional_files()``
    exercise the ``--no-overwrite`` guard.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    project_dir = tmp_path / "ee_no_overwrite"
    project_dir.mkdir()
    custom = "# custom ansible.cfg\n"
    (project_dir / "ansible.cfg").write_text(custom, encoding="utf-8")

    galaxy_config = {
        "galaxy_servers": [
            {"id": "galaxy", "url": "https://galaxy.ansible.com/"},
        ],
    }

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(project_dir)
    cli_args["no_overwrite"] = True
    cli_args["ee_config"] = json.dumps(galaxy_config)

    Init(Config(**cli_args)).run()
    capsys.readouterr()

    assert (project_dir / "ansible.cfg").read_text() == custom


def test_ee_project_official_image_aap26_python312(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test that AAP 2.6 EE images use Python 3.12 interpreter.

    AAP 2.6 switched from Python 3.11 to Python 3.12.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_aap26_image")
    cli_args["base_image"] = (
        "registry.redhat.io/ansible-automation-platform-26/ee-minimal-rhel9:latest"
    )

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_aap26_image" / "execution-environment.yml"
    ee_content = ee_file.read_text()

    # AAP 2.6 should use Python 3.12
    assert "python_path: /usr/bin/python3.12" in ee_content


def test_ee_project_official_image_fallback_python(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test that non-versioned official EE images use Python 3.11.

    Images like ee-dellos or ee-29-rhel are official but not tied to a
    specific AAP version, so they map to Python 3.11 in OFFICIAL_EE_IMAGES.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_dellos_image")
    cli_args["base_image"] = "registry.redhat.io/ee-dellos-rhel8:latest"

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_dellos_image" / "execution-environment.yml"
    ee_content = ee_file.read_text()

    # Non-versioned official image uses Python 3.11
    assert "python_path: /usr/bin/python3.11" in ee_content
    # Should still be detected as official EE (microdnf)
    assert "package_manager_path: /usr/bin/microdnf" in ee_content


def test_ee_project_custom_registry(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test that registry and image_name are templated into the CI workflow.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_custom_registry")
    cli_args["ee_config"] = json.dumps(
        {
            "registry": "quay.io",
            "image_name": "my-org/my-ee",
        }
    )

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    workflow_file = tmp_path / "ee_custom_registry" / ".github" / "workflows" / "ee-build.yml"
    workflow_content = workflow_file.read_text()

    assert "vars.EE_REGISTRY || 'quay.io'" in workflow_content
    assert "vars.EE_IMAGE_NAME || github.repository" in workflow_content


def test_ee_project_registry_tls_verify_disabled(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test that --no-registry-tls-verify produces 'false' in the CI workflow.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_tls_verify")
    cli_args["registry_tls_verify"] = False

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    workflow_file = tmp_path / "ee_tls_verify" / ".github" / "workflows" / "ee-build.yml"
    workflow_content = workflow_file.read_text()

    assert "EE_REGISTRY_TLS_VERIFY || 'false'" in workflow_content
    assert 'default: "false"' in workflow_content
    assert "--tls-verify=${{ env.EE_REGISTRY_TLS_VERIFY }}" in workflow_content


def test_ee_project_registry_tls_verify_explicit_true_overrides_config(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test --registry-tls-verify overrides an EE config that sets it to false.

    When the EE config file sets registry_tls_verify: false but the user
    explicitly passes --registry-tls-verify, the CLI flag must win.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_tls_override")
    cli_args["ee_config"] = json.dumps({"registry_tls_verify": False})
    cli_args["registry_tls_verify"] = True

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    workflow_file = tmp_path / "ee_tls_override" / ".github" / "workflows" / "ee-build.yml"
    workflow_content = workflow_file.read_text()

    assert "EE_REGISTRY_TLS_VERIFY || 'true'" in workflow_content
    assert 'default: "true"' in workflow_content


def test_ee_project_registry_tls_verify_none_preserves_config(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test that omitting the CLI flag preserves the EE config file value.

    When the user does not pass --registry-tls-verify or --no-registry-tls-verify,
    config.registry_tls_verify is None and the EE config file value is kept.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_tls_none")
    cli_args["ee_config"] = json.dumps({"registry_tls_verify": False})

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    workflow_file = tmp_path / "ee_tls_none" / ".github" / "workflows" / "ee-build.yml"
    workflow_content = workflow_file.read_text()

    assert "EE_REGISTRY_TLS_VERIFY || 'false'" in workflow_content
    assert 'default: "false"' in workflow_content


def test_ee_project_non_official_image_no_microdnf(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test that non-official images get full skeleton with ansible_core/runner.

    Non-official images need ansible-core and ansible-runner installed via pip.
    They should NOT have the ansible.cfg file or additional_build_files for it.

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

    # Non-official images should NOT have microdnf
    assert "package_manager_path" not in ee_content

    # Non-official images SHOULD have ansible_core and ansible_runner
    assert "ansible_core:" in ee_content
    assert "ansible_runner:" in ee_content
    assert "package_pip: ansible-core" in ee_content
    assert "package_pip: ansible-runner" in ee_content

    # Non-official images should use generic python3 path
    assert "python_path: /usr/bin/python3" in ee_content

    # Without galaxy_servers, no ansible.cfg or prepend_galaxy
    assert "src: ansible.cfg" not in ee_content
    assert "prepend_galaxy:" not in ee_content

    ansible_cfg_file = tmp_path / "ee_fedora_image" / "ansible.cfg"
    assert not ansible_cfg_file.exists()


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
    cli_args["ee_config_file"] = str(config_file)

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


def test_ee_project_git_url_edge_cases(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test edge case Git URL formats without protocol separator.

    These test cases cover code paths for URLs without :// separator,
    such as git@host:path or simple host/path formats.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_git_edge")
    cli_args["ee_collections"] = [
        # SSH-style URL with :git suffix (hits line 393 - 2 parts after rsplit)
        "git@github.com/org/ns.col1:git",
        # SSH-style URL without :git suffix (hits line 410 - fallback case)
        "git@github.com/org/ns.col2",
    ]

    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out

    assert r"Note: execution_env project created" in result

    ee_file = tmp_path / "ee_git_edge" / "execution-environment.yml"
    ee_content = ee_file.read_text()

    # SSH-style URL with :git suffix
    assert "git@github.com/org/ns.col1" in ee_content
    assert "type: git" in ee_content

    # SSH-style URL without :git suffix (fallback)
    assert "git@github.com/org/ns.col2" in ee_content


# ---------------------------------------------------------------------------
# EEConfig / EECollection dataclass tests
# ---------------------------------------------------------------------------


def test_ee_config_from_dict_full() -> None:
    """Test EEConfig.from_dict with all supported fields."""
    data = {
        "ee_name": "my-ee",
        "base_image": "quay.io/custom:latest",
        "collections": [{"name": "ansible.posix", "version": ">=1.0"}],
        "python_deps": ["jmespath"],
        "system_packages": ["git"],
        "additional_build_files": [{"src": "a.cfg", "dest": "configs"}],
        "additional_build_steps": {"prepend_base": ["RUN echo hi"]},
        "options": {"package_manager_path": "/usr/bin/dnf"},
        "ansible_cfg": "[galaxy]\nserver_list = hub\n",
        "build_arg_defaults": {"ANSIBLE_GALAXY_CLI_COLLECTION_OPTS": "--pre"},
    }
    cfg = EEConfig.from_dict(data)

    assert cfg.ee_name == "my-ee"
    assert cfg.base_image == "quay.io/custom:latest"
    assert len(cfg.collections) == 1
    assert cfg.collections[0].name == "ansible.posix"
    assert cfg.collections[0].version == ">=1.0"
    assert cfg.python_deps == ("jmespath",)
    assert cfg.system_packages == ("git",)
    assert cfg.additional_build_files == ({"src": "a.cfg", "dest": "configs"},)
    assert cfg.additional_build_steps == {"prepend_base": ["RUN echo hi"]}
    assert cfg.options == {"package_manager_path": "/usr/bin/dnf"}
    assert cfg.build_arg_defaults == {"ANSIBLE_GALAXY_CLI_COLLECTION_OPTS": "--pre"}
    assert "server_list" in cfg.ansible_cfg
    assert not cfg.galaxy_servers


def test_ee_config_from_dict_galaxy_servers() -> None:
    """Test EEConfig.from_dict with galaxy_servers list."""
    data = {
        "galaxy_servers": [
            {
                "id": "automation_hub",
                "url": "https://console.redhat.com/api/automation-hub/content/published/",
                "auth_url": "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token",
                "token_required": True,
            },
            {
                "id": "private_hub",
                "url": "https://pah.corp.example.com/api/galaxy/content/published/",
                "token_required": True,
                "validate_certs": False,
            },
            {
                "id": "galaxy",
                "url": "https://galaxy.ansible.com/",
            },
        ],
    }
    cfg = EEConfig.from_dict(data)

    assert len(cfg.galaxy_servers) == 3  # noqa: PLR2004
    assert cfg.galaxy_servers[0].id == "automation_hub"
    assert "console.redhat.com" in cfg.galaxy_servers[0].url
    assert "sso.redhat.com" in cfg.galaxy_servers[0].auth_url
    assert cfg.galaxy_servers[0].token_required is True
    assert cfg.galaxy_servers[0].validate_certs is True
    assert cfg.galaxy_servers[1].id == "private_hub"
    assert cfg.galaxy_servers[1].token_required is True
    assert cfg.galaxy_servers[1].validate_certs is False
    assert cfg.galaxy_servers[2].id == "galaxy"
    assert cfg.galaxy_servers[2].token_required is False
    assert cfg.galaxy_servers[2].validate_certs is True


def test_ee_config_from_dict_registry_and_image_name() -> None:
    """Test EEConfig.from_dict with registry and image_name."""
    cfg = EEConfig.from_dict({"registry": "quay.io", "image_name": "my-org/my-ee"})
    assert cfg.registry == "quay.io"
    assert cfg.image_name == "my-org/my-ee"

    cfg_default = EEConfig.from_dict({})
    assert cfg_default.registry == "ghcr.io"
    assert cfg_default.image_name == ""


def test_ee_config_from_dict_registry_rejects_url() -> None:
    """Test EEConfig.from_dict rejects registry with URL scheme."""
    with pytest.raises(CreatorError, match="Invalid registry"):
        EEConfig.from_dict({"registry": "https://ghcr.io"})

    with pytest.raises(CreatorError, match="Invalid registry"):
        EEConfig.from_dict({"registry": "http://quay.io"})


def test_ee_config_from_dict_ee_file_name() -> None:
    """Test EEConfig.from_dict with custom ee_file_name."""
    cfg = EEConfig.from_dict({"ee_file_name": "my-ee.yml"})
    assert cfg.ee_file_name == "my-ee.yml"

    cfg_yaml = EEConfig.from_dict({"ee_file_name": "custom.yaml"})
    assert cfg_yaml.ee_file_name == "custom.yaml"

    cfg_default = EEConfig.from_dict({})
    assert cfg_default.ee_file_name == "execution-environment.yml"


def test_ee_config_ee_file_name_validation() -> None:
    """Test that ee_file_name rejects paths and non-YAML extensions."""
    with pytest.raises(ValueError, match="plain filename"):
        EEConfig.from_dict({"ee_file_name": "../etc/evil.yml"})

    with pytest.raises(ValueError, match="plain filename"):
        EEConfig.from_dict({"ee_file_name": "sub/dir/ee.yml"})

    with pytest.raises(ValueError, match="plain filename"):
        EEConfig.from_dict({"ee_file_name": "sub\\dir\\ee.yml"})

    with pytest.raises(ValueError, match=r"\.yml or \.yaml"):
        EEConfig.from_dict({"ee_file_name": "ee-def.json"})

    with pytest.raises(ValueError, match=r"\.yml or \.yaml"):
        EEConfig.from_dict({"ee_file_name": "ee-def.txt"})


def test_ee_config_from_dict_defaults() -> None:
    """Test EEConfig.from_dict with empty dict uses defaults."""
    cfg = EEConfig.from_dict({})

    assert cfg.ee_name == "ansible_sample_ee"
    assert cfg.base_image == "quay.io/fedora/fedora:41"
    assert cfg.registry == "ghcr.io"
    assert cfg.image_name == ""
    assert not cfg.collections
    assert not cfg.python_deps
    assert not cfg.galaxy_servers
    assert not cfg.scm_servers
    assert not cfg.build_arg_defaults


def test_ee_config_from_dict_build_arg_defaults_invalid() -> None:
    """Test EEConfig.from_dict rejects non-string build_arg_defaults values."""
    with pytest.raises(CreatorError, match="build_arg_defaults"):
        EEConfig.from_dict({"build_arg_defaults": "not-a-mapping"})

    with pytest.raises(CreatorError, match="build_arg_defaults"):
        EEConfig.from_dict({"build_arg_defaults": {"FOO": 1}})


def test_ee_collection_from_dict_invalid_name() -> None:
    """Test EECollection.from_dict rejects invalid collection names."""
    with pytest.raises(CreatorError, match="Invalid collection name"):
        EECollection.from_dict({"name": "bad-name"})


def test_ee_collection_as_dict_sparse() -> None:
    """Test EECollection.as_dict only includes non-empty fields."""
    col = EECollection(name="ansible.posix")
    assert col.as_dict() == {"name": "ansible.posix"}

    col_full = EECollection(name="ansible.posix", version="1.0", type="galaxy")
    result = col_full.as_dict()
    assert result == {"name": "ansible.posix", "version": "1.0", "type": "galaxy"}


def test_ee_config_from_dict_rejects_unknown_keys() -> None:
    """Test EEConfig.from_dict rejects unknown keys."""
    with pytest.raises(CreatorError, match=r"Unknown key.*EE config.*bogus"):
        EEConfig.from_dict({"bogus": "value"})

    with pytest.raises(CreatorError, match=r"Unknown key.*EE config.*collection_list"):
        EEConfig.from_dict({"base_image": "quay.io/test:1", "collection_list": []})

    with pytest.raises(CreatorError, match=r"Unknown key.*EE config.*base_images"):
        EEConfig.from_dict({"base_images": "quay.io/test:1"})


def test_ee_collection_from_dict_rejects_unknown_keys() -> None:
    """Test EECollection.from_dict rejects unknown keys."""
    with pytest.raises(CreatorError, match=r"Unknown key.*collection.*src"):
        EECollection.from_dict({"name": "ansible.posix", "src": "foo"})

    with pytest.raises(CreatorError, match=r"Unknown key.*collection.*extra"):
        EECollection.from_dict({"name": "ansible.posix", "extra": "bar"})


def test_ee_config_to_schema_shape() -> None:
    """Test EEConfig.to_schema returns expected structure."""
    schema = EEConfig.to_schema()

    assert schema["type"] == "object"
    props = schema["properties"]
    assert "ee_name" in props
    assert "base_image" in props
    assert "collections" in props
    assert props["collections"]["type"] == "array"
    assert props["collections"]["items"]["type"] == "object"
    assert "name" in props["collections"]["items"]["properties"]
    assert "python_deps" in props
    assert "system_packages" in props
    assert "ansible_cfg" in props
    assert "registry" in props
    assert "image_name" in props
    assert "galaxy_servers" in props
    assert props["galaxy_servers"]["type"] == "array"
    assert "scm_servers" in props
    assert props["scm_servers"]["type"] == "array"
    assert "ee_file_name" in props
    assert "build_arg_defaults" in props


def test_ee_config_schema_in_cli_schema() -> None:
    """Test that the CLI schema exposes EEConfig structure for ee_config."""
    schema = for_command("init", "execution_env")
    ee_config_schema = schema["parameters"]["properties"]["ee_config"]

    assert ee_config_schema["type"] == "object"
    assert "properties" in ee_config_schema
    assert "ee_name" in ee_config_schema["properties"]
    assert "base_image" in ee_config_schema["properties"]
    assert "collections" in ee_config_schema["properties"]


def test_extract_action_info_schema_class_no_option_strings() -> None:
    """Test _extract_action_info with schema_class but no option_strings."""
    action = argparse.Action(option_strings=[], dest="ee_config")
    action.help = "EE configuration"
    action.schema_class = EEConfig  # type: ignore[attr-defined]

    info = _extract_action_info(action)

    assert info["type"] == "object"
    assert info["description"] == "EE configuration"
    assert "aliases" not in info


def test_ee_collection_from_dict_git_url_formats() -> None:
    """Test that EECollection.from_dict accepts all Git URL formats."""
    git_urls = [
        "git://github.com/org/repo",
        "ssh://git@github.com/org/repo",
        "file:///local/path/to/collection",
        "git@github.com:org/repo.git",
        "https://github.com/org/repo",
    ]
    for url in git_urls:
        col = EECollection.from_dict({"name": url})
        assert col.name == url


def test_ee_config_file_json_non_object(tmp_path: Path) -> None:
    """Test that _load_ee_config_file rejects JSON files with non-object content.

    Args:
        tmp_path: Temporary directory path.
    """
    json_file = tmp_path / "bad.json"
    json_file.write_text('["a", "b"]')
    with pytest.raises(CreatorError, match="must contain a JSON object"):
        Init._load_ee_config_file(str(json_file))


def test_ee_config_file_yaml_non_mapping(tmp_path: Path) -> None:
    """Test that _load_ee_config_file rejects YAML files with non-mapping content.

    Args:
        tmp_path: Temporary directory path.
    """
    yaml_file = tmp_path / "bad.yml"
    yaml_file.write_text("- item1\n- item2\n")
    with pytest.raises(CreatorError, match="must contain a YAML mapping"):
        Init._load_ee_config_file(str(yaml_file))


def test_ee_config_both_sources_rejected(
    output: Output,
    tmp_path: Path,
) -> None:
    """Test that providing both ee_config and ee_config_file is rejected.

    Args:
        output: Output instance for logging.
        tmp_path: Temporary directory path.
    """
    config = Config(
        creator_version="0.0.1",
        output=output,
        subcommand="init",
        project="execution_env",
        init_path=str(tmp_path / "test-ee"),
        ee_config='{"ee_name": "test"}',
        ee_config_file="/some/file.yml",
    )
    with pytest.raises(CreatorError, match="Cannot specify both"):
        Init(config=config)


# ---------------------------------------------------------------------------
# GalaxyServer dataclass tests
# ---------------------------------------------------------------------------


def test_galaxy_server_from_dict_full() -> None:
    """Test GalaxyServer.from_dict with all fields."""
    data = {
        "id": "automation_hub",
        "url": "https://console.redhat.com/api/automation-hub/content/published/",
        "auth_url": "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token",
        "token_required": True,
    }
    server = GalaxyServer.from_dict(data)

    assert server.id == "automation_hub"
    assert "console.redhat.com" in server.url
    assert "sso.redhat.com" in server.auth_url
    assert server.token_required is True
    assert server.validate_certs is True


def test_galaxy_server_from_dict_validate_certs_false() -> None:
    """Test GalaxyServer.from_dict with validate_certs false."""
    server = GalaxyServer.from_dict(
        {
            "id": "internal_hub",
            "url": "https://10.0.0.1/api/galaxy/content/published/",
            "validate_certs": False,
        },
    )
    assert server.id == "internal_hub"
    assert server.validate_certs is False


def test_galaxy_server_from_dict_minimal() -> None:
    """Test GalaxyServer.from_dict with only required fields."""
    server = GalaxyServer.from_dict({"id": "galaxy", "url": "https://galaxy.ansible.com/"})

    assert server.id == "galaxy"
    assert server.url == "https://galaxy.ansible.com/"
    assert server.auth_url == ""
    assert server.token_required is False
    assert server.validate_certs is True


def test_galaxy_server_from_dict_missing_id() -> None:
    """Test GalaxyServer.from_dict rejects missing id."""
    with pytest.raises(CreatorError, match="must have an 'id' field"):
        GalaxyServer.from_dict({"url": "https://galaxy.ansible.com/"})


def test_galaxy_server_from_dict_missing_url() -> None:
    """Test GalaxyServer.from_dict rejects missing url."""
    with pytest.raises(CreatorError, match="must have a 'url' field"):
        GalaxyServer.from_dict({"id": "galaxy"})


def test_galaxy_server_from_dict_invalid_id() -> None:
    """Test GalaxyServer.from_dict rejects invalid server IDs."""
    with pytest.raises(CreatorError, match="Invalid galaxy server id"):
        GalaxyServer.from_dict({"id": "Bad-Id", "url": "https://example.com/"})

    with pytest.raises(CreatorError, match="Invalid galaxy server id"):
        GalaxyServer.from_dict({"id": "has.dot", "url": "https://example.com/"})


def test_galaxy_server_as_dict() -> None:
    """Test GalaxyServer.as_dict includes derived token_env_var."""
    server = GalaxyServer(
        id="automation_hub",
        url="https://example.com/",
        auth_url="https://sso.example.com/token",
        token_required=True,
        validate_certs=True,
    )
    result = server.as_dict()

    assert result["id"] == "automation_hub"
    assert result["url"] == "https://example.com/"
    assert result["auth_url"] == "https://sso.example.com/token"
    assert result["token_required"] is True
    assert result["validate_certs"] is True
    expected_var = "ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN"
    assert result["token_env_var"] == expected_var


def test_galaxy_server_as_dict_no_auth_url() -> None:
    """Test GalaxyServer.as_dict omits auth_url when empty."""
    server = GalaxyServer(id="galaxy", url="https://galaxy.ansible.com/")
    result = server.as_dict()

    assert "auth_url" not in result
    assert result["validate_certs"] is True
    expected_var = "ANSIBLE_GALAXY_SERVER_GALAXY_TOKEN"
    assert result["token_env_var"] == expected_var


def test_galaxy_server_to_schema() -> None:
    """Test GalaxyServer.to_schema returns expected structure."""
    schema = GalaxyServer.to_schema()

    assert schema["type"] == "object"
    assert "id" in schema["required"]
    assert "url" in schema["required"]
    props = schema["properties"]
    assert "id" in props
    assert "url" in props
    assert "auth_url" in props
    assert "token_required" in props
    assert "validate_certs" in props


# ---------------------------------------------------------------------------
# ScmServer dataclass tests
# ---------------------------------------------------------------------------


def test_scm_server_from_dict_full() -> None:
    """Test ScmServer.from_dict with all fields."""
    data = {
        "id": "github_org1",
        "hostname": "github.com",
        "token_env_var": "GITHUB_ORG1_TOKEN",
    }
    server = ScmServer.from_dict(data)

    assert server.id == "github_org1"
    assert server.hostname == "github.com"
    assert server.token_env_var == "GITHUB_ORG1_TOKEN"  # noqa: S105


def test_scm_server_from_dict_missing_id() -> None:
    """Test ScmServer.from_dict rejects missing id."""
    with pytest.raises(CreatorError, match="must have an 'id' field"):
        ScmServer.from_dict({"hostname": "github.com", "token_env_var": "TOKEN"})


def test_scm_server_from_dict_missing_hostname() -> None:
    """Test ScmServer.from_dict rejects missing hostname."""
    with pytest.raises(CreatorError, match="must have a 'hostname' field"):
        ScmServer.from_dict({"id": "github", "token_env_var": "TOKEN"})


def test_scm_server_from_dict_missing_token_env_var() -> None:
    """Test ScmServer.from_dict rejects missing token_env_var."""
    with pytest.raises(CreatorError, match="must have a 'token_env_var' field"):
        ScmServer.from_dict({"id": "github", "hostname": "github.com"})


def test_scm_server_from_dict_invalid_id() -> None:
    """Test ScmServer.from_dict rejects invalid server IDs."""
    with pytest.raises(CreatorError, match="Invalid SCM server id"):
        ScmServer.from_dict(
            {
                "id": "Bad-Id",
                "hostname": "github.com",
                "token_env_var": "TOKEN",
            }
        )


def test_scm_server_from_dict_invalid_token_env_var() -> None:
    """Test ScmServer.from_dict rejects invalid environment variable names."""
    with pytest.raises(CreatorError, match="Invalid token_env_var"):
        ScmServer.from_dict(
            {
                "id": "github",
                "hostname": "github.com",
                "token_env_var": "lowercase_bad",
            }
        )

    with pytest.raises(CreatorError, match="Invalid token_env_var"):
        ScmServer.from_dict(
            {
                "id": "github",
                "hostname": "github.com",
                "token_env_var": "HAS-DASHES",
            }
        )

    with pytest.raises(CreatorError, match="Invalid token_env_var"):
        ScmServer.from_dict(
            {
                "id": "github",
                "hostname": "github.com",
                "token_env_var": "123_STARTS_WITH_DIGIT",
            }
        )


def test_scm_server_as_dict() -> None:
    """Test ScmServer.as_dict returns all fields."""
    server = ScmServer(
        id="internal_gitlab",
        hostname="gitlab.corp.com",
        token_env_var="INTERNAL_GITLAB_TOKEN",  # noqa: S106
    )
    result = server.as_dict()

    assert result["id"] == "internal_gitlab"
    assert result["hostname"] == "gitlab.corp.com"
    expected_var = "INTERNAL_GITLAB_TOKEN"
    assert result["token_env_var"] == expected_var


def test_scm_server_to_schema() -> None:
    """Test ScmServer.to_schema returns expected structure."""
    schema = ScmServer.to_schema()

    assert schema["type"] == "object"
    assert "id" in schema["required"]
    assert "hostname" in schema["required"]
    assert "token_env_var" in schema["required"]
    props = schema["properties"]
    assert "id" in props
    assert "hostname" in props
    assert "token_env_var" in props


def test_ee_config_from_dict_scm_servers() -> None:
    """Test EEConfig.from_dict parses scm_servers list."""
    data = {
        "scm_servers": [
            {
                "id": "github_org1",
                "hostname": "github.com",
                "token_env_var": "GITHUB_ORG1_TOKEN",
            },
            {
                "id": "internal_gitlab",
                "hostname": "gitlab.corp.com",
                "token_env_var": "INTERNAL_GITLAB_TOKEN",
            },
        ],
    }
    cfg = EEConfig.from_dict(data)

    assert len(cfg.scm_servers) == 2  # noqa: PLR2004
    assert cfg.scm_servers[0].id == "github_org1"
    assert cfg.scm_servers[0].hostname == "github.com"
    assert cfg.scm_servers[0].token_env_var == "GITHUB_ORG1_TOKEN"  # noqa: S105
    assert cfg.scm_servers[1].id == "internal_gitlab"


def test_ee_project_with_scm_servers(
    output: Output,
    tmp_path: Path,
) -> None:
    """Test EE project scaffolding with scm_servers generates correct workflow.

    Args:
        output: Output instance for logging.
        tmp_path: Temporary directory path.
    """
    dest = tmp_path / "scm-ee"
    config = Config(
        creator_version="0.0.1",
        output=output,
        subcommand="init",
        project="execution_env",
        init_path=str(dest),
        ee_config=json.dumps(
            {
                "collections": [
                    {
                        "name": "https://${GITHUB_ORG1_TOKEN}@github.com/org1/my-collection",
                        "type": "git",
                    },
                    {"name": "cisco.ios"},
                ],
                "scm_servers": [
                    {
                        "id": "github_org1",
                        "hostname": "github.com",
                        "token_env_var": "GITHUB_ORG1_TOKEN",
                    },
                ],
            }
        ),
    )
    init = Init(config=config)
    init.run()

    wf_path = dest / ".github" / "workflows" / "ee-build.yml"
    wf_content = wf_path.read_text()

    assert "GITHUB_ORG1_TOKEN" in wf_content
    assert "envsubst" in wf_content
    assert "command -v envsubst" in wf_content
    assert "context/_build/requirements.yml" in wf_content
    assert "gettext-base" in wf_content
    assert "git-credentials" not in wf_content.lower()
    assert "AAP_EE_BUILDER_GITHUB_TOKEN" not in wf_content
    assert "AAP_EE_BUILDER_GITLAB_TOKEN" not in wf_content

    next_steps = dest / "NEXT_STEPS.md"
    assert next_steps.exists()
    ns_content = next_steps.read_text()
    assert "GITHUB_ORG1_TOKEN" in ns_content
    assert "github.com" in ns_content
