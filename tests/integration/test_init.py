"""Unit tests for ansible-creator init."""

from __future__ import annotations

import re
import sys

from pathlib import Path
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from tests.conftest import CliRunCallable


CREATOR_BIN = Path(sys.executable).parent / "ansible-creator"


def test_run_help(cli: CliRunCallable) -> None:
    """Test running ansible-creator --help.

    Args:
        cli: cli_run function.
    """
    # Get the path to the current python interpreter
    result = cli(f"{CREATOR_BIN} --help")
    assert result.returncode == 0, (result.stdout, result.stderr)

    assert "The fastest way to generate all your ansible content." in result.stdout
    assert "Positional arguments:" in result.stdout
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


def test_run_init_no_input(cli: CliRunCallable) -> None:
    """Test running ansible-creator init without any input.

    Args:
        cli: cli_run function.
    """
    result = cli(f"{CREATOR_BIN} init")
    assert result.returncode != 0
    err = "the following arguments are required: project-type"
    assert err in result.stderr


@pytest.mark.parametrize(
    argnames="command",
    argvalues=["init --project ansible-project", "init --init-path /tmp"],
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
    assert re.search("Note: collection project created at", result.stdout) is not None

    # fail to override existing collection with force=false (default)
    result = cli(
        f"{CREATOR_BIN} init testorg.testcol --init-path {final_dest}",
    )

    assert result.returncode != 0

    # override existing collection with force=true
    result = cli(f"{CREATOR_BIN} init testorg.testcol --init-path {tmp_path} --force")
    assert result.returncode == 0
    assert re.search("Warning: re-initializing existing directory", result.stdout) is not None

    # override existing collection with override=true
    result = cli(f"{CREATOR_BIN} init testorg.testcol --init-path {tmp_path} --overwrite")
    assert result.returncode == 0
    assert re.search(f"Note: collection project created at {tmp_path}", result.stdout) is not None

    # use no-override=true
    result = cli(f"{CREATOR_BIN} init testorg.testcol --init-path {tmp_path} --no-overwrite")
    assert result.returncode != 0
    assert re.search("The flag `--no-overwrite` restricts overwriting.", result.stderr) is not None
