"""Unit tests for ansible-creator init."""

from __future__ import annotations

import re

from typing import TYPE_CHECKING

import pytest

from tests.defaults import CREATOR_BIN


if TYPE_CHECKING:
    from pathlib import Path

    from tests.conftest import CliRunCallable


def test_run_help(cli: CliRunCallable) -> None:
    """Test running ansible-creator --help.

    Args:
        cli: cli_run function.
    """
    # Get the path to the current python interpreter
    result = cli(f"{CREATOR_BIN} --help", env={"NO_COLOR": "1"})
    assert result.returncode == 0, (result.stdout, result.stderr)

    assert "The fastest way to generate all your ansible content." in result.stdout
    assert re.search(r"positional arguments:", result.stdout, re.IGNORECASE)
    assert "add" in result.stdout
    assert "Add resources to an existing Ansible project." in result.stdout
    assert "init" in result.stdout
    assert "Initialize a new Ansible project." in result.stdout


def test_run_no_subcommand(cli: CliRunCallable) -> None:
    """Test running ansible-creator without subcommand.

    Args:
        cli: cli_run function.
    """
    result = cli(str(CREATOR_BIN))
    assert result.returncode != 0
    assert "the following arguments are required: command" in result.stderr


@pytest.mark.parametrize(
    argnames="command",
    argvalues=("init --project ansible-project", "init --init-path /tmp"),
    ids=["project_no_scm", "collection_no_name"],
)
def test_run_deprecated_failure(command: str, cli: CliRunCallable) -> None:
    """Test running ansible-creator init with deprecated options.

    Args:
        command: Command to run.
        cli: cli_run function.
    """
    result = cli(f"{CREATOR_BIN} {command}")
    assert result.returncode != 0
    assert "is no longer needed and will be removed." in result.stdout
    assert "The CLI has changed." in result.stderr


@pytest.mark.parametrize(
    argnames=("args", "expected"),
    argvalues=(
        ("a.b", "must be longer than 2 characters."),
        ("_a.b", "cannot begin with an underscore."),
        ("foo", "must be in the format '<namespace>.<name>'."),
    ),
    ids=("short", "underscore", "no_dot"),
)
@pytest.mark.parametrize("command", ("collection", "playbook"))
def test_run_init_invalid_name(command: str, args: str, expected: str, cli: CliRunCallable) -> None:
    """Test running ansible-creator init with invalid collection name.

    Args:
        command: Command to run.
        args: Arguments to pass to the CLI.
        expected: Expected error message.
        cli: cli_run function.
    """
    result = cli(f"{CREATOR_BIN} init {command} {args}")
    assert result.returncode != 0
    assert result.stderr.startswith("Critical:")
    assert expected in result.stderr


def test_run_init_basic(cli: CliRunCallable, tmp_path: Path) -> None:
    """Test running ansible-creator init with empty/non-empty/force.

    Args:
        cli: cli_run function.
        tmp_path: Temporary path.
    """
    final_dest = f"{tmp_path}/collections/ansible_collections"
    cli(f"mkdir -p {final_dest}")

    result = cli(
        f"{CREATOR_BIN} init testorg.testcol --init-path {final_dest}",
    )
    assert result.returncode == 0

    # check stdout
    assert r"Note: collection project created at" in result.stdout

    # fail to override existing collection with force=false (default)
    result = cli(
        f"{CREATOR_BIN} init testorg.testcol --init-path {final_dest}",
    )

    assert result.returncode != 0

    # override existing collection with force=true
    result = cli(f"{CREATOR_BIN} init testorg.testcol --init-path {tmp_path} --force")
    assert result.returncode == 0
    assert r"Warning: re-initializing existing directory" in result.stdout

    # override existing collection with override=true
    result = cli(f"{CREATOR_BIN} init testorg.testcol --init-path {tmp_path} --overwrite")
    assert result.returncode == 0
    assert re.search(f"Note: collection project created at {tmp_path}", result.stdout) is not None

    # use no-override=true
    result = cli(f"{CREATOR_BIN} init testorg.testcol --init-path {tmp_path} --no-overwrite")
    assert result.returncode != 0
    assert re.search(r"The flag `--no-overwrite` restricts overwriting.", result.stderr) is not None


def test_run_init_ee(cli: CliRunCallable, tmp_path: Path) -> None:
    """Test running ansible-creator init for ee_project.

    Args:
        cli: cli_run function.
        tmp_path: Temporary path.
    """
    final_dest = f"{tmp_path}/ee_project"
    cli(f"mkdir -p {final_dest}")

    result = cli(
        f"{CREATOR_BIN} init execution_env {final_dest}",
    )
    assert result.returncode == 0

    # check stdout
    assert r"Note: execution_env project created at" in result.stdout


def test_run_init_collection_include(cli: CliRunCallable, tmp_path: Path) -> None:
    """Test init collection with --include to cherry-pick bundles.

    Args:
        cli: cli_run function.
        tmp_path: Temporary path.
    """
    dest = tmp_path / "include_test"
    result = cli(
        f"{CREATOR_BIN} init collection testns.testcol {dest} --include gitignore",
    )
    assert result.returncode == 0
    assert r"Note: collection project created at" in result.stdout

    assert (dest / ".gitignore").exists(), ".gitignore should be created"
    assert not (dest / ".devcontainer").exists(), ".devcontainer should not be created"
    assert not (dest / "devfile.yaml").exists(), "devfile.yaml should not be created"
    assert not (dest / ".vscode").exists(), ".vscode should not be created"
    assert not (dest / "AGENTS.md").exists(), "AGENTS.md should not be created"
    assert not (dest / "roles").exists(), "roles/ should not be created"

    assert (dest / "galaxy.yml").exists(), "core project files should always be created"


def test_run_init_collection_exclude(cli: CliRunCallable, tmp_path: Path) -> None:
    """Test init collection with --exclude to remove specific bundles.

    Args:
        cli: cli_run function.
        tmp_path: Temporary path.
    """
    dest = tmp_path / "exclude_test"
    result = cli(
        f"{CREATOR_BIN} init collection testns.testcol {dest} --exclude ai devfile role",
    )
    assert result.returncode == 0
    assert r"Note: collection project created at" in result.stdout

    assert (dest / ".gitignore").exists(), ".gitignore should be created"
    assert (dest / ".devcontainer").exists(), ".devcontainer should be created"
    assert (dest / ".vscode").exists(), ".vscode should be created"
    assert not (dest / "AGENTS.md").exists(), "AGENTS.md should not be created (excluded)"
    assert not (dest / "devfile.yaml").exists(), "devfile.yaml should not be created (excluded)"
    assert not (dest / "roles").exists(), "roles/ should not be created (excluded)"

    assert (dest / "galaxy.yml").exists(), "core project files should always be created"


def test_run_init_playbook_include(cli: CliRunCallable, tmp_path: Path) -> None:
    """Test init playbook with --include to cherry-pick bundles.

    Args:
        cli: cli_run function.
        tmp_path: Temporary path.
    """
    dest = tmp_path / "playbook_include"
    result = cli(
        f"{CREATOR_BIN} init playbook testns.testcol {dest} --include devcontainer vscode",
    )
    assert result.returncode == 0
    assert r"Note: playbook project created at" in result.stdout

    assert (dest / ".devcontainer").exists(), ".devcontainer should be created"
    assert (dest / ".vscode").exists(), ".vscode should be created"
    assert not (dest / ".gitignore").exists(), ".gitignore should not be created"
    assert not (dest / "devfile.yaml").exists(), "devfile.yaml should not be created"
    assert not (dest / "AGENTS.md").exists(), "AGENTS.md should not be created"

    assert (dest / "site.yml").exists(), "core project files should always be created"


def test_run_init_collection_include_all(cli: CliRunCallable, tmp_path: Path) -> None:
    """Test init collection with --include all (default behavior).

    Args:
        cli: cli_run function.
        tmp_path: Temporary path.
    """
    dest = tmp_path / "include_all_test"
    result = cli(
        f"{CREATOR_BIN} init collection testns.testcol {dest} --include all",
    )
    assert result.returncode == 0

    assert (dest / ".gitignore").exists()
    assert (dest / ".devcontainer").exists()
    assert (dest / "devfile.yaml").exists()
    assert (dest / ".vscode").exists()
    assert (dest / "AGENTS.md").exists()
    assert (dest / "roles").exists()


def test_run_init_include_exclude_mutually_exclusive(
    cli: CliRunCallable,
    tmp_path: Path,
) -> None:
    """Test that --include and --exclude cannot be used together.

    Args:
        cli: cli_run function.
        tmp_path: Temporary path.
    """
    dest = tmp_path / "mutex_test"
    result = cli(
        f"{CREATOR_BIN} init collection testns.testcol {dest} --include gitignore --exclude ai",
    )
    assert result.returncode != 0
    assert "not allowed with argument" in result.stderr


def test_run_init_invalid_bundle_name(cli: CliRunCallable, tmp_path: Path) -> None:
    """Test that invalid bundle names are rejected.

    Args:
        cli: cli_run function.
        tmp_path: Temporary path.
    """
    dest = tmp_path / "invalid_test"
    result = cli(
        f"{CREATOR_BIN} init collection testns.testcol {dest} --include bogus",
    )
    assert result.returncode != 0
    assert "invalid choice" in result.stderr
