"""Test running ansible-creator commands without input or --help."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.defaults import CREATOR_BIN


if TYPE_CHECKING:
    from tests.conftest import CliRunCallable


@pytest.mark.parametrize(
    argnames=("args", "error_msg"),
    argvalues=(
        pytest.param("add", "Missing required argument 'content-type'.", id="add"),
        pytest.param("add --help", "", id="add-help"),
        pytest.param(
            "add resource", "Missing required argument 'resource-type'.", id="add-resource"
        ),
        pytest.param("add resource --help", "", id="add-resource-help"),
        pytest.param("add plugin", "Missing required argument 'plugin-type'.", id="add-plugin"),
        pytest.param("add plugin --help", "", id="add-plugin-help"),
        pytest.param("init", "Missing required argument 'project-type'.", id="init"),
        pytest.param("init --help", "", id="init-help"),
    ),
)
def test_run_no_input(cli: CliRunCallable, args: str, error_msg: str) -> None:
    """Test running ansible-creator commands without input or --help.

    Args:
        cli: cli_run function.
        args: args to pass to the CLI.
        error_msg: Expected error message.
    """
    result = cli(f"{CREATOR_BIN} {args}", env={"NO_COLOR": "1"})
    if not error_msg:
        assert result.returncode == 0
    else:
        assert result.returncode != 0
        assert error_msg in result.stderr
