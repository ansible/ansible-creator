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
def cli_args(tmp_path, output: Output) -> dict:
    """Create an Init class object as fixture.

    :param tmp_path: App configuration object.
    """
    return {
        "creator_version": "0.0.1",
        "subcommand": "init",
        "collection": "testorg.testcol",
        "init_path": tmp_path / "testorg" / "testcol",
        "output": output,
    }


def test_run_success_for_collection(
    capsys,
    tmp_path,
    cli_args,
) -> None:
    """Test Init.run()."""
    # successfully create new collection

    cli_args["project"] = "collection"
    init = Init(
        Config(**cli_args),
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
        f"The directory {tmp_path}/testorg/testcol is not empty."
        "\nYou can use --force to re-initialize this directory."
        "\nHowever it will delete ALL existing contents in it."
    )
    with pytest.raises(CreatorError, match=fail_msg):
        init.run()

    # override existing collection with force=true
    cli_args["force"] = True
    init = Init(
        Config(**cli_args),
    )
    init.run()
    result = capsys.readouterr().out
    assert (
        re.search("Warning: re-initializing existing directory", result) is not None
    ), result


def test_run_success_ansible_project(
    capsys,
    tmp_path,
    cli_args,
) -> None:
    """Test Init.run()."""
    # successfully create new ansible-project
    cli_args["collection"] = None
    cli_args["project"] = "ansible-project"
    cli_args["init_path"] = tmp_path / "new_project"
    cli_args["scm_org"] = "weather"
    cli_args["scm_project"] = "demo"
    init = Init(
        Config(**cli_args),
    )
    init.run()
    result = capsys.readouterr().out

    # check stdout
    assert re.search("Note: ansible project created", result) is not None

    # recursively assert files created
    dircmp(
        str(tmp_path / "new_project"),
        str(FIXTURES_DIR / "project" / "ansible_project"),
    ).report_full_closure()
    captured = capsys.readouterr()
    assert re.search("Differing files|Only in", captured.out) is None, captured.out

    # fail to override existing ansible-project directory with force=false (default)
    fail_msg = (
        f"The directory {tmp_path}/new_project is not empty."
        "\nYou can use --force to re-initialize this directory."
        "\nHowever it will delete ALL existing contents in it."
    )
    with pytest.raises(CreatorError, match=fail_msg):
        init.run()

    # override existing ansible-project directory with force=true
    cli_args["force"] = True
    init = Init(
        Config(**cli_args),
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
) -> None:
    """Test Init.run() when init_path ends with "collections" / "ansible_collections"""
    # successfully create new collection
    cli_args["project"] = "collection"
    cli_args["init_path"] = tmp_path / "collections" / "ansible_collections"
    final_path = cli_args["init_path"] / "testorg" / "testcol"
    init = Init(
        Config(**cli_args),
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


def test_error_1(
    tmp_path,
    cli_args,
) -> None:
    """Test Init.run()."""
    # Validation for: ansible-creator init --project=ansible-project
    cli_args["collection"] = None
    cli_args["project"] = "ansible-project"
    cli_args["init_path"] = tmp_path / "new_project"
    cli_args["scm_org"] = None
    cli_args["scm_project"] = None
    fail_msg = (
        "Parameters 'scm-org' and 'scm-project' are required when "
        "scaffolding an ansible-project."
    )
    with pytest.raises(CreatorError, match=fail_msg):
        init = Init(
            Config(**cli_args),
        )
        init.run()


def test_error_2(
    cli_args,
) -> None:
    """Test Init.run()."""
    # Validation for: ansible-creator init
    cli_args["collection"] = None
    cli_args["project"] = "collection"
    cli_args["init_path"] = None
    cli_args["scm_org"] = None
    cli_args["scm_project"] = None
    fail_msg = "The argument 'collection' is required when scaffolding a collection."
    with pytest.raises(CreatorError, match=fail_msg):
        init = Init(
            Config(**cli_args),
        )
        init.run()


def test_warning(
    capsys,
    tmp_path,
    cli_args,
) -> None:
    """Test Init.run()."""
    # Validation for: ansible-creator init testorg.testname --scm-org=weather
    # --scm-project=demo --project=collection
    cli_args["collection"] = "testorg.testname"
    cli_args["project"] = None
    cli_args["init_path"] = tmp_path / "testorg" / "testcol"
    cli_args["scm_org"] = "weather"
    cli_args["scm_project"] = "demo"
    init = Init(
        Config(**cli_args),
    )
    init.run()
    result = capsys.readouterr().out

    # this is required to handle random line breaks in CI, especially with macos runners
    mod_result = "".join([line.strip() for line in result.splitlines()])
    assert (
        re.search(
            rf"Warning:\s*The parameters\s*'scm-org'\s*and\s*'scm-project'"
            rf"\s*have\s*no\s*effect\s*when\s*project\s*is\s*not\s*set\s*to\s*ansible-project",
            mod_result,
        )
        is not None
    )
