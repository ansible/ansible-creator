"""conftest."""

import os
import subprocess
import pytest

os.environ["HOME"] = "/home/ansible"
os.environ["DEV_WORKSPACE"] = "collections/ansible_collections"


@pytest.fixture
def cli():
    """fixture to run CLI commands."""
    return cli_run


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
