"""conftest."""

from __future__ import annotations

import os
import subprocess

from subprocess import CalledProcessError, CompletedProcess
from typing import TYPE_CHECKING, Any

import pytest

from ansible_creator.output import Output
from ansible_creator.utils import TermFeatures


if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


os.environ["HOME"] = "/home/ansible"
os.environ["DEV_WORKSPACE"] = "collections/ansible_collections"


@pytest.fixture()
def cli() -> Callable[[Any], CompletedProcess[str] | CalledProcessError]:
    """Fixture to run CLI commands.

    Returns:
        function: cli_run function.
    """
    return cli_run


@pytest.fixture()
def output(tmp_path: Path) -> Output:
    """Create an Output class object as fixture.

    Args:
        tmp_path: Temporary path.

    Returns:
        Output: Output class object.
    """
    return Output(
        display="text",
        log_file=str(tmp_path) + "ansible-creator.log",
        log_level="notset",
        log_append="false",
        term_features=TermFeatures(color=False, links=False),
        verbosity=0,
    )


def cli_run(args: list[str]) -> CompletedProcess[str] | CalledProcessError:
    """Execute a command using subprocess.

    Args:
        args: Command to run.

    Returns:
        CompletedProcess: CompletedProcess object.
        CalledProcessError: CalledProcessError object.
    """
    updated_env = os.environ.copy()
    # this helps asserting stdout/stderr
    updated_env.update({"LINES": "40", "COLUMNS": "300", "TERM": "xterm-256color"})
    try:
        result = subprocess.run(
            args,
            shell=True,
            capture_output=True,
            check=True,
            text=True,
            env=updated_env,
        )
    except subprocess.CalledProcessError as err:
        return err
    return result
