"""Unit tests for ansible-creator init execution environment projects: config validation."""

from __future__ import annotations

import json

from pathlib import Path
from typing import TypedDict

import pytest

from ansible_creator.config import Config
from ansible_creator.exceptions import CreatorError
from ansible_creator.output import Output
from ansible_creator.subcommands.init import Init
from ansible_creator.utils import TermFeatures


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
