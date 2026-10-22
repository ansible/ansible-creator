"""Unit tests for ansible-creator init execution environment projects: collection sources."""

from __future__ import annotations

import json

from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse

import pytest

from ansible_creator.config import Config
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


def _ini_value_hostname(section: str, key: str) -> str | None:
    """Return the hostname of a ``key = <url>`` value within an INI section body.

    Args:
        section: INI section body text (e.g. from ``_galaxy_server_ini_section``).
        key: INI key to look up (e.g. ``"url"`` or ``"auth_url"``).

    Returns:
        The hostname of the URL assigned to ``key``, or ``None`` if the key is
        not present in the section.
    """
    prefix = f"{key} = "
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return urlparse(stripped[len(prefix) :].strip()).hostname
    return None


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
    automation_hub_section = _galaxy_server_ini_section(cfg, "automation_hub")
    assert _ini_value_hostname(automation_hub_section, "url") == "console.redhat.com"
    assert _ini_value_hostname(automation_hub_section, "auth_url") == "sso.redhat.com"
    assert "[galaxy_server.private_hub]" in cfg
    private_hub_section = _galaxy_server_ini_section(cfg, "private_hub")
    assert _ini_value_hostname(private_hub_section, "url") == "pah.corp.example.com"
    assert "validate_certs = false" in private_hub_section
    assert private_hub_section.count("validate_certs = false") == 1
    assert "validate_certs = false" not in automation_hub_section
    galaxy_section = _galaxy_server_ini_section(cfg, "galaxy")
    assert "validate_certs = false" not in galaxy_section
    assert cfg.count("validate_certs = false") == 1
    assert "[galaxy_server.galaxy]" in cfg
    assert _ini_value_hostname(galaxy_section, "url") == "galaxy.ansible.com"
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
    # Hostname is rendered as a backtick-delimited token (not a URL), so match
    # the exact token rather than a bare substring of the hostname.
    assert "`github.com`" in ns_content


def test_ee_project_with_scm_servers_gitlab(
    output: Output,
    tmp_path: Path,
) -> None:
    """EE project with scm_servers and GitLab CI includes envsubst (no git-credentials).

    Args:
        output: Output object for logging.
        tmp_path: Temporary directory path.
    """
    dest = tmp_path / "scm-ee-gl"
    config = Config(
        creator_version="0.0.1",
        output=output,
        subcommand="init",
        project="execution_env",
        init_path=str(dest),
        scm_provider="gitlab",
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
    Init(config=config).run()

    gl = dest / ".gitlab-ci.yml"
    assert gl.exists()
    wf_content = gl.read_text()
    assert "GITHUB_ORG1_TOKEN" in wf_content
    assert "envsubst" in wf_content
    assert "context/_build/requirements.yml" in wf_content
    assert "git-credentials" not in wf_content.lower()

    next_steps = dest / "NEXT_STEPS.md"
    ns = next_steps.read_text()
    assert "CI/CD" in ns
    assert "Actions" not in ns
