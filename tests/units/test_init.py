# cspell: ignore dcmp, subdcmp
"""Unit tests for ansible-creator init."""

from __future__ import annotations

import re
import shutil

from filecmp import dircmp
from pathlib import Path
from typing import TypedDict

import pytest

from ansible_creator.config import Config
from ansible_creator.exceptions import CreatorError
from ansible_creator.output import Output
from ansible_creator.subcommands.init import Init
from ansible_creator.utils import TermFeatures
from tests.defaults import FIXTURES_DIR


class ConfigDict(TypedDict):
    """Type hint for Config dictionary.

    Attributes:
        creator_version: The version of the creator.
        output: The output object to use for logging.
        subcommand: The subcommand to execute.
        collection: The name of the collection.
        init_path: Path to initialize the project.
        project: The type of project to scaffold.
        force: Force overwrite of existing directory.
        scm_org: The SCM organization for the project.
        scm_project: The SCM project for the project.
    """

    creator_version: str
    output: Output
    subcommand: str
    collection: str
    init_path: str
    project: str
    force: bool
    scm_org: str | None
    scm_project: str | None


@pytest.fixture(name="cli_args")
def fixture_cli_args(tmp_path: Path, output: Output) -> ConfigDict:
    """Create a dict to use for a Init class object as fixture.

    Args:
        tmp_path: App configuration object.
        output: Output class object.

    Returns:
        dict: Dictionary, partial Init class object.
    """
    return {
        "creator_version": "0.0.1",
        "output": output,
        "subcommand": "init",
        "collection": "testorg.testcol",
        "init_path": str(tmp_path / "testorg" / "testcol"),
        "project": "",
        "force": False,
        "scm_org": "",
        "scm_project": "",
    }


def has_differences(dcmp: dircmp[str], errors: list[str]) -> list[str]:
    """Recursively check for differences in dircmp object.

    Args:
        dcmp: dircmp object.
        errors: List of errors.

    Returns:
        list: List of errors.
    """
    errors.extend([f"Only in {dcmp.left}: {f}" for f in dcmp.left_only])
    errors.extend([f"Only in {dcmp.right}: {f}" for f in dcmp.right_only])
    errors.extend(
        [f"Differing files: {dcmp.left}/{f} {dcmp.right}/{f}" for f in dcmp.diff_files],
    )
    for subdcmp in dcmp.subdirs.values():
        errors = has_differences(subdcmp, errors)
    return errors


def test_run_success_for_collection(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init.run().

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "collection"
    init = Init(
        Config(**cli_args),
    )
    init.run()
    result = capsys.readouterr().out

    # check stdout
    assert re.search("Note: collection testorg.testcol created", result) is not None

    # recursively assert files created
    cmp = dircmp(str(tmp_path), str(FIXTURES_DIR / "collection"))
    diff = has_differences(dcmp=cmp, errors=[])
    assert diff == [], diff

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
    assert re.search("Warning: re-initializing existing directory", result) is not None, result


def test_run_success_ansible_project(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    cli_args: ConfigDict,
) -> None:
    """Test Init.run().

    Successfully create new ansible-project

    Args:
        capsys: Pytest fixture to capture stdout and stderr.
        tmp_path: Temporary directory path.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["collection"] = ""
    cli_args["project"] = "ansible-project"
    cli_args["init_path"] = str(tmp_path / "new_project")
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
    cmp = dircmp(
        str(tmp_path / "new_project"),
        str(FIXTURES_DIR / "project" / "playbook_project"),
    )
    diff = has_differences(dcmp=cmp, errors=[])
    assert diff == [], diff

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
    assert re.search("Warning: re-initializing existing directory", result) is not None, result


def test_run_success_collections_alt_dir(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    cli_args: ConfigDict,
) -> None:
    """Test Init.run() when init_path ends with "collections" / "ansible_collections.

    Successfully create new collection

    Args:
        tmp_path: Temporary directory path.
        capsys: Pytest fixture to capture stdout and stderr.
        cli_args: Dictionary, partial Init class object.
    """
    cli_args["project"] = "collection"
    cli_args["init_path"] = str(tmp_path / "collections" / "ansible_collections")
    final_path = Path(cli_args["init_path"]) / "testorg" / "testcol"
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


def test_delete_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test a remove fails gracefully.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary directory path.
    """
    (tmp_path / "file.txt").touch()

    init = Init(
        Config(
            creator_version="0.0.1",
            force=True,
            subcommand="init",
            collection="testorg.testcol",
            init_path=str(tmp_path),
            output=Output(
                log_file=str(tmp_path / "log.log"),
                log_level="DEBUG",
                log_append="false",
                term_features=TermFeatures(color=False, links=False),
                verbosity=0,
            ),
        ),
    )

    err = "Test thrown error"

    def rmtree(path: Path) -> None:  # noqa: ARG001
        raise OSError(err)

    monkeypatch.setattr(shutil, "rmtree", rmtree)

    with pytest.raises(CreatorError, match=err) as exc_info:
        init.run()
    assert "failed to remove existing directory" in str(exc_info.value)


def test_is_file_error(tmp_path: Path) -> None:
    """Test a file dest fails gracefully.

    Args:
        tmp_path: Temporary directory path.
    """
    file = tmp_path / "file.txt"
    file.touch()
    init = Init(
        Config(
            creator_version="0.0.1",
            force=True,
            subcommand="init",
            collection="testorg.testcol",
            init_path=str(file),
            output=Output(
                log_file=str(tmp_path / "log.log"),
                log_level="DEBUG",
                log_append="false",
                term_features=TermFeatures(color=False, links=False),
                verbosity=0,
            ),
        ),
    )

    with pytest.raises(CreatorError) as exc_info:
        init.run()
    assert "but is a file" in str(exc_info.value)
