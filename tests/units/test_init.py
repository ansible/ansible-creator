"""Unit tests for ansible-creator init."""

from __future__ import annotations

import re

from typing import TYPE_CHECKING

import pytest

from ansible_creator.config import Config
from ansible_creator.output import Output
from ansible_creator.subcommands.init import Init
from ansible_creator.utils import TermFeatures

from tests.defaults import FIXTURES_DIR
from tests.utils import run_diff


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def init_class(tmp_path: Path) -> Init:
    """Create an Init class object as fixture.

    :param tmp_path: App configuration object.
    """
    cli_args: dict = {
        "creator_version": "0.0.1",
        "json": True,
        "log_append": True,
        "log_file": tmp_path / "ansible-creator.log",
        "log_level": "debug",
        "no_ansi": False,
        "subcommand": "init",
        "verbose": 0,
        "collection": "testorg.testcol",
        "init_path": tmp_path,
    }
    return Init(
        Config(**cli_args),
        output=Output(
            display="text",
            log_file=str(tmp_path) + "ansible-creator.log",
            log_level="notset",
            log_append="false",
            term_features=TermFeatures(color=False, links=False),
            verbosity=0,
        ),
    )


def test_run(tmp_path, init_class) -> None:  # noqa: ANN001
    """Test Init.run()."""
    init_class.run()
    diff = run_diff(a=str(tmp_path), b=str(FIXTURES_DIR / "collection"))
    assert re.search("Differing files|Only in", diff) is None, diff
