"""conftest."""

import os
import subprocess
import pytest

from ansible_creator.output import Output
from ansible_creator.utils import TermFeatures

os.environ["HOME"] = "/home/ansible"
os.environ["DEV_WORKSPACE"] = "collections/ansible_collections"


@pytest.fixture
def cli():
    """fixture to run CLI commands."""
    return cli_run


@pytest.fixture()
def output(tmp_path) -> Output:
    """Create an Output class object as fixture.

    :param tmp_path: App configuration object.
    """
    return Output(
        display="text",
        log_file=str(tmp_path) + "ansible-creator.log",
        log_level="notset",
        log_append="false",
        term_features=TermFeatures(color=False, links=False),
        verbosity=0,
    )


def cli_run(args):
    """execute a command using subprocess."""
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
        return result
    except subprocess.CalledProcessError as err:
        return err
