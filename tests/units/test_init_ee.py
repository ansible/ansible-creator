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
from ansible_creator.types import EECollection, EEConfig
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
    They also get ansible.cfg with Portal anchors for Automation Hub configuration.

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
    assert "python_path: /usr/bin/python3.11" in ee_content

    # Official EE images should NOT have additional_build_files for ansible.cfg
    # (ansible.cfg is volume-mounted at build time, never COPY'd into a layer)
    assert "src: ansible.cfg" not in ee_content

    # Official EE images should have prepend_galaxy with ARG directives for tokens
    assert "prepend_galaxy:" in ee_content
    assert "ARG ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN" in ee_content
    assert "ARG ANSIBLE_GALAXY_SERVER_PRIVATE_HUB_TOKEN" in ee_content

    # Official EE images should NOT have pip upgrade or the default sample tag
    assert "RUN $PYCMD -m pip install -U pip" not in ee_content
    assert "ansible_sample_ee" not in ee_content

    # ansible.cfg should be generated with predefined server sections
    ansible_cfg_file = tmp_path / "ee_official_image" / "ansible.cfg"
    assert ansible_cfg_file.exists()
    ansible_cfg_content = ansible_cfg_file.read_text()
    assert "[galaxy]" in ansible_cfg_content
    assert "server_list = automation_hub, galaxy" in ansible_cfg_content
    assert "[galaxy_server.automation_hub]" in ansible_cfg_content
    assert "console.redhat.com/api/automation-hub" in ansible_cfg_content
    assert "auth_url = https://sso.redhat.com/" in ansible_cfg_content
    assert "[galaxy_server.galaxy]" in ansible_cfg_content
    # private_hub should be commented out by default
    assert "# [galaxy_server.private_hub]" in ansible_cfg_content
    # No token values should appear in ansible.cfg (auth_url contains "token" in the path)
    assert "token =" not in ansible_cfg_content
    assert "token=" not in ansible_cfg_content


def test_ee_project_official_image_with_private_hub_url(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test that private_hub_url activates the private_hub section in ansible.cfg.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_pah")
    cli_args["base_image"] = (
        "registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel8:latest"
    )
    cli_args["ee_config"] = (
        '{"private_hub_url": "https://pah.corp.example.com/api/galaxy/content/published/"}'
    )

    Init(Config(**cli_args)).run()
    capsys.readouterr()

    ansible_cfg_file = tmp_path / "ee_pah" / "ansible.cfg"
    assert ansible_cfg_file.exists()
    cfg = ansible_cfg_file.read_text()

    assert "server_list = automation_hub, private_hub, galaxy" in cfg
    assert "[galaxy_server.private_hub]" in cfg
    assert "pah.corp.example.com" in cfg
    assert "# [galaxy_server.private_hub]" not in cfg
    assert "auth_url = https://sso.redhat.com/" in cfg
    assert "token =" not in cfg
    assert "token=" not in cfg


def test_ee_project_official_image_custom_hub_no_auth_url(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test that auth_url is omitted when automation_hub_url is not Red Hat AH.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "ee_custom_hub")
    cli_args["base_image"] = (
        "registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel8:latest"
    )
    cli_args["ee_config"] = '{"automation_hub_url": "https://custom-ah.example.com/api/hub/"}'

    Init(Config(**cli_args)).run()
    capsys.readouterr()

    ansible_cfg_file = tmp_path / "ee_custom_hub" / "ansible.cfg"
    assert ansible_cfg_file.exists()
    cfg = ansible_cfg_file.read_text()

    assert "[galaxy_server.automation_hub]" in cfg
    assert "custom-ah.example.com" in cfg
    assert "auth_url" not in cfg
    assert "sso.redhat.com" not in cfg


def test_ee_project_official_image_no_overwrite_ansible_cfg(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test that --no-overwrite skips existing ansible.cfg for official EE images.

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

    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(project_dir)
    cli_args["no_overwrite"] = True
    cli_args["base_image"] = (
        "registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel9:latest"
    )

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

    # Non-official images should NOT have additional_build_files for ansible.cfg
    assert "src: ansible.cfg" not in ee_content
    assert "prepend_galaxy:" not in ee_content

    # ansible.cfg file should NOT be generated for non-official images
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
        "name": "my-ee",
        "base_image": "quay.io/custom:latest",
        "collections": [{"name": "ansible.posix", "version": ">=1.0"}],
        "python_deps": ["jmespath"],
        "system_packages": ["git"],
        "additional_build_files": [{"src": "a.cfg", "dest": "configs"}],
        "additional_build_steps": {"prepend_base": ["RUN echo hi"]},
        "options": {"package_manager_path": "/usr/bin/dnf"},
        "ansible_cfg": "[galaxy]\nserver_list = hub\n",
    }
    cfg = EEConfig.from_dict(data)

    assert cfg.name == "my-ee"
    assert cfg.base_image == "quay.io/custom:latest"
    assert len(cfg.collections) == 1
    assert cfg.collections[0].name == "ansible.posix"
    assert cfg.collections[0].version == ">=1.0"
    assert cfg.python_deps == ("jmespath",)
    assert cfg.system_packages == ("git",)
    assert cfg.additional_build_files == ({"src": "a.cfg", "dest": "configs"},)
    assert cfg.additional_build_steps == {"prepend_base": ["RUN echo hi"]}
    assert cfg.options == {"package_manager_path": "/usr/bin/dnf"}
    assert "server_list" in cfg.ansible_cfg
    # Defaults for new URL fields
    assert "console.redhat.com" in cfg.automation_hub_url
    assert cfg.private_hub_url == ""


def test_ee_config_from_dict_hub_urls() -> None:
    """Test EEConfig.from_dict with automation_hub_url and private_hub_url."""
    data = {
        "automation_hub_url": "https://custom-ah.example.com/api/hub/",
        "private_hub_url": "https://pah.corp.example.com/api/galaxy/content/published/",
    }
    cfg = EEConfig.from_dict(data)

    assert cfg.automation_hub_url == "https://custom-ah.example.com/api/hub/"
    assert cfg.private_hub_url == "https://pah.corp.example.com/api/galaxy/content/published/"


def test_ee_config_from_dict_defaults() -> None:
    """Test EEConfig.from_dict with empty dict uses defaults."""
    cfg = EEConfig.from_dict({})

    assert cfg.name == "ansible_sample_ee"
    assert cfg.base_image == "quay.io/fedora/fedora:41"
    assert not cfg.collections
    assert not cfg.python_deps


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


def test_ee_config_to_schema_shape() -> None:
    """Test EEConfig.to_schema returns expected structure."""
    schema = EEConfig.to_schema()

    assert schema["type"] == "object"
    props = schema["properties"]
    assert "name" in props
    assert "base_image" in props
    assert "collections" in props
    assert props["collections"]["type"] == "array"
    assert props["collections"]["items"]["type"] == "object"
    assert "name" in props["collections"]["items"]["properties"]
    assert "python_deps" in props
    assert "system_packages" in props
    assert "ansible_cfg" in props
    assert "automation_hub_url" in props
    assert "private_hub_url" in props


def test_ee_config_schema_in_cli_schema() -> None:
    """Test that the CLI schema exposes EEConfig structure for ee_config."""
    schema = for_command("init", "execution_env")
    ee_config_schema = schema["parameters"]["properties"]["ee_config"]

    assert ee_config_schema["type"] == "object"
    assert "properties" in ee_config_schema
    assert "name" in ee_config_schema["properties"]
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
        ee_config='{"name": "test"}',
        ee_config_file="/some/file.yml",
    )
    with pytest.raises(CreatorError, match="Cannot specify both"):
        Init(config=config)
