"""conftest."""

from __future__ import annotations

import os
import subprocess

from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from typing import Protocol

import pytest

from ansible_creator.output import Output
from ansible_creator.utils import TermFeatures


os.environ["HOME"] = str(Path.home())
os.environ["DEV_WORKSPACE"] = "collections/ansible_collections"


@pytest.fixture()
def cli() -> CliRunCallable:
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


@pytest.fixture()
def home_path() -> Path:
    """Create the home directory as a fixture.

    Returns:
        Path: Home directory.
    """
    return Path.home()


class CliRunCallable(Protocol):
    """Callable protocol for cli_run function."""

    def __call__(
        self,
        args: str,
        env: dict[str, str] | None = None,
    ) -> CompletedProcess[str] | CalledProcessError:
        """Run a command using subprocess.

        Args:
            args: Command to run.
            env: Supplemental environment variables.

        Returns:
            CompletedProcess: CompletedProcess object.
            CalledProcessError: CalledProcessError object.
        """


def cli_run(
    args: str,
    env: dict[str, str] | None = None,
) -> CompletedProcess[str] | CalledProcessError:
    """Run a command using subprocess.

    Args:
        args: Command to run.
        env: Supplemental environment variables.

    Returns:
        CompletedProcess: CompletedProcess object.
        CalledProcessError: CalledProcessError object.
    """
    updated_env = os.environ.copy()
    # this helps asserting stdout/stderr
    updated_env.update({"LINES": "40", "COLUMNS": "300", "TERM": "xterm-256color"})
    if env:
        updated_env.update(env)
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
