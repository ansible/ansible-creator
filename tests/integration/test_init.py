"""Unit tests for ansible-creator init."""

from __future__ import annotations

import re
import sys

from collections.abc import Callable
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from typing import Any


cli_type = Callable[[Any], CompletedProcess[str] | CalledProcessError]

CREATOR_BIN = Path(sys.executable).parent / "ansible-creator"


def test_run_help(cli: cli_type) -> None:
    """Test running ansible-creator --help.

    Args:
        cli: cli_run function.
    """
    # Get the path to the current python interpreter
    result = cli(f"{CREATOR_BIN} --help")
    assert result.returncode == 0, (result.stdout, result.stderr)

    assert "Print ansible-creator version and exit." in result.stdout
    assert "The subcommand to invoke." in result.stdout
    assert "Initialize an Ansible Collection." in result.stdout


def test_run_no_subcommand(cli: cli_type) -> None:
    """Test running ansible-creator without subcommand.

    Args:
        cli: cli_run function.
    """
    result = cli(str(CREATOR_BIN))
    assert result.returncode != 0
    assert "the following arguments are required: subcommand" in result.stderr


def test_run_init_no_input(cli: cli_type) -> None:
    """Test running ansible-creator init without any input.

    Args:
        cli: cli_run function.
    """
    result = cli(f"{CREATOR_BIN} init")
    assert result.returncode != 0
    assert (
        "Error: The argument 'collection' is required when scaffolding a collection"
        in result.stderr
    )


def test_run_init_basic(cli: cli_type, tmp_path: Path) -> None:
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
    assert re.search("Note: collection testorg.testcol created at", result.stdout) is not None

    # fail to override existing collection with force=false (default)
    result = cli(
        f"{CREATOR_BIN} init testorg.testcol --init-path {final_dest}",
    )

    assert result.returncode != 0

    # this is required to handle random line breaks in CI, especially with macos runners
    mod_stderr = "".join([line.strip() for line in result.stderr.splitlines()])
    assert (
        re.search(
            rf"Error:\s*The\s*directory\s*{final_dest}/testorg/testcol\s*is\s*not\s*empty.",
            mod_stderr,
        )
        is not None
    )
    assert "You can use --force to re-initialize this directory." in result.stderr
    assert "However it will delete ALL existing contents in it." in result.stderr

    # override existing collection with force=true
    result = cli(f"{CREATOR_BIN} init testorg.testcol --init-path {tmp_path} --force")
    assert result.returncode == 0
    assert re.search("Warning: re-initializing existing directory", result.stdout) is not None
