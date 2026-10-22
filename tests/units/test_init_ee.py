# cspell: ignore dcmp, subdcmp, microdnf
"""Unit tests for ansible-creator init execution environment projects: scaffolding basics."""

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


def test_run_success_ee_project_gitlab(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Init scaffolds GitLab CI when ``scm_provider`` is gitlab.

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "execution_env"
    cli_args["init_path"] = str(tmp_path / "gitlab_ee")
    cli_args["scm_provider"] = "gitlab"
    init = Init(Config(**cli_args))
    init.run()
    result = capsys.readouterr().out
    assert r"Note: execution_env project created" in result

    assert not (tmp_path / "gitlab_ee" / ".github").exists()

    cmp_result = dircmp(
        str(tmp_path / "gitlab_ee"),
        str(FIXTURES_DIR / "project" / "ee_project_gitlab"),
    )
    diff = has_differences(dcmp=cmp_result, errors=[])
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

    # Without galaxy_servers, no ansible.cfg or prepend_galaxy
    assert "src: ansible.cfg" not in ee_content
    assert "prepend_galaxy:" not in ee_content

    ansible_cfg_file = tmp_path / "ee_fedora_image" / "ansible.cfg"
    assert not ansible_cfg_file.exists()


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
