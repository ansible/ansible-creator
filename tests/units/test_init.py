"""Unit tests for ansible-creator init."""

from __future__ import annotations

import re

from filecmp import dircmp

import pytest

from ansible_creator.config import Config
from ansible_creator.exceptions import CreatorError
from ansible_creator.output import Output
from ansible_creator.subcommands.init import Init
from ansible_creator.utils import TermFeatures

from tests.defaults import FIXTURES_DIR


@pytest.fixture()
def cli_args(tmp_path) -> dict:
    """Create an Init class object as fixture.

    :param tmp_path: App configuration object.
    """
    return {
        "creator_version": "0.0.1",
        "json": True,
        "log_append": True,
        "log_file": tmp_path / "ansible-creator.log",
        "log_level": "debug",
        "no_ansi": False,
        "subcommand": "init",
        "verbose": 0,
        "collection": "testorg.testcol",
        "init_path": tmp_path / "testorg" / "testcol",
    }


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


def test_run_success(
    capsys,
    tmp_path,
    cli_args,
    output,
) -> None:
    """Test Init.run()."""
    # successfully create new collection
    init = Init(
        Config(**cli_args),
        output=output,
    )
    init.run()
    result = capsys.readouterr().out

    # check stdout
    assert re.search("Note: collection testorg.testcol created", result) is not None

    # recursively assert files created
    dircmp(str(tmp_path), str(FIXTURES_DIR / "collection")).report_full_closure()
    captured = capsys.readouterr()
    assert re.search("Differing files|Only in", captured.out) is None, captured.out

    # fail to override existing collection with force=false (default)
    fail_msg = (
        f"The directory {tmp_path}/testorg/testcol already exists."
        "\nYou can use --force to re-initialize this directory."
        "\nHowever it will delete ALL existing contents in it."
    )
    with pytest.raises(CreatorError, match=fail_msg):
        init.run()

    # override existing collection with force=true
    cli_args["force"] = True
    init = Init(
        Config(**cli_args),
        output=output,
    )
    init.run()
    result = capsys.readouterr().out
    assert (
        re.search("Warning: re-initializing existing directory", result) is not None
    ), result


def test_run_success_collections_alt_dir(
    tmp_path,
    capsys,
    cli_args,
    output,
) -> None:
    """Test Init.run() when init_path ends with "collections" / "ansible_collections"""
    # successfully create new collection
    cli_args["init_path"] = tmp_path / "collections" / "ansible_collections"
    final_path = cli_args["init_path"] / "testorg" / "testcol"
    init = Init(
        Config(**cli_args),
        output=output,
    )
    init.run()
    result = capsys.readouterr().out

    # this is required to handle random line breaks in CI, especially with macos runners
    mod_result = "".join([line.strip() for line in result.splitlines()])

    assert (
        re.search(
            rf"Note:\s*collection\s*testorg.testcol\s*created\s*at\s*{final_path}",
            mod_result,
        )
        is not None
    )
