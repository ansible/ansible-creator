"""Basic unit tests for ansible-creator."""

from __future__ import annotations

import re
import runpy
import sys

from pathlib import Path, PosixPath

import pytest

from ansible_creator.arg_parser import COMING_SOON
from ansible_creator.cli import Cli
from ansible_creator.cli import main as cli_main
from ansible_creator.config import Config
from ansible_creator.output import Output
from ansible_creator.utils import TermFeatures, expand_path


def test_configuration_class(output: Output) -> None:
    """Test Config() dataclass post_init.

    Args:
        output: Output dataclass object.
    """
    app_config = Config(
        creator_version="0.0.1",
        subcommand="init",
        collection="testorg.testcol",
        init_path="$HOME",
        output=output,
    )
    assert app_config.namespace == "testorg"
    assert app_config.collection_name == "testcol"
    home_path = Path.home()
    assert app_config.init_path == home_path


@pytest.mark.parametrize(
    argnames=["sysargs", "expected"],
    argvalues=[
        [
            ["ansible-creator", "init", "testorg.testcol"],
            {
                "subcommand": "init",
                "no_ansi": False,
                "log_file": str(Path.cwd() / "ansible-creator.log"),
                "log_level": "notset",
                "log_append": "true",
                "json": False,
                "verbose": 0,
                "collection": "testorg.testcol",
                "init_path": "./",
                "force": False,
                "no_overwrite": False,
                "overwrite": False,
                "project": "collection",  # default value
            },
        ],
        [
            [
                "ansible-creator",
                "init",
                "--project=ansible-project",
                f"--init-path={Path.home()}/my-ansible-project",
                "--scm-org=weather",
                "--scm-project=demo",
            ],
            {
                "subcommand": "init",
                "no_ansi": False,
                "log_file": str(Path.cwd() / "ansible-creator.log"),
                "log_level": "notset",
                "log_append": "true",
                "json": False,
                "verbose": 0,
                "collection": "weather.demo",
                "init_path": f"{Path.home()}/my-ansible-project",
                "force": False,
                "no_overwrite": False,
                "overwrite": False,
                "project": "playbook",
            },
        ],
        [
            [
                "ansible-creator",
                "init",
                "testorg.testcol",
                f"--init-path={Path.home()}",
                "-vvv",
                "--json",
                "--no-ansi",
                "--la=false",
                "--lf=test.log",
                "--ll=debug",
                "--force",
            ],
            {
                "subcommand": "init",
                "no_ansi": True,
                "log_file": "test.log",
                "log_level": "debug",
                "log_append": "false",
                "json": True,
                "verbose": 3,
                "collection": "testorg.testcol",
                "init_path": f"{Path.home()}",
                "force": True,
                "no_overwrite": False,
                "overwrite": False,
                "project": "collection",  # default value
            },
        ],
        [
            [
                "ansible-creator",
                "init",
                "--project=ansible-project",
                "--scm-org=weather",
                "--scm-project=demo",
                f"--init-path={Path.home()}/my-ansible-project",
                "-vvv",
                "--json",
                "--no-ansi",
                "--la=false",
                "--lf=test.log",
                "--ll=debug",
                "--force",
            ],
            {
                "subcommand": "init",
                "no_ansi": True,
                "log_file": "test.log",
                "log_level": "debug",
                "log_append": "false",
                "json": True,
                "verbose": 3,
                "collection": "weather.demo",
                "init_path": f"{Path.home()}/my-ansible-project",
                "force": True,
                "no_overwrite": False,
                "overwrite": False,
                "project": "playbook",
            },
        ],
        [
            [
                "ansible-creator",
                "init",
                "collection",
                "foo.bar",
                "/test/test",
                "--lf=test.log",
            ],
            {
                "subcommand": "init",
                "project": "collection",
                "collection": "foo.bar",
                "init_path": "/test/test",
                "force": False,
                "no_overwrite": False,
                "overwrite": False,
                "json": False,
                "log_append": "true",
                "log_file": "test.log",
                "log_level": "notset",
                "no_ansi": False,
                "verbose": 0,
            },
        ],
        [
            [
                "ansible-creator",
                "init",
                "playbook",
                "foo.bar",
                "/test/test",
                "--lf=test.log",
            ],
            {
                "subcommand": "init",
                "project": "playbook",
                "collection": "foo.bar",
                "init_path": "/test/test",
                "force": False,
                "no_overwrite": False,
                "overwrite": False,
                "json": False,
                "log_append": "true",
                "log_file": "test.log",
                "log_level": "notset",
                "no_ansi": False,
                "verbose": 0,
            },
        ],
    ],
)
def test_cli_parser(
    monkeypatch: pytest.MonkeyPatch,
    sysargs: list[str],
    expected: dict[str, str | bool | None],
) -> None:
    """Test CLI args parsing.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        sysargs: List of CLI arguments.
        expected: Expected values for the parsed CLI arguments.
    """
    monkeypatch.setattr("sys.argv", sysargs)
    parsed_args = Cli().args
    assert parsed_args == expected


def test_missing_j2(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test missing Jinja2.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    fail_msg = (
        "jinja2 is required but does not appear to be installed."
        "It can be installed using `pip install jinja2`"
    )

    monkeypatch.setattr("sys.path", [])
    monkeypatch.delitem(sys.modules, "jinja2", raising=False)
    monkeypatch.delitem(sys.modules, "ansible_creator.templar", raising=False)

    import ansible_creator.templar

    assert ansible_creator.templar.HAS_JINJA2 is False
    with pytest.raises(ImportError, match=fail_msg):
        ansible_creator.templar.Templar()


def test_cli_init_output(monkeypatch: pytest.MonkeyPatch, home_path: PosixPath) -> None:
    """Test CLI init_output method.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        home_path: Home directory.
    """
    sysargs = [
        "ansible-creator",
        "init",
        "testorg.testcol",
        f"--init-path={home_path}",
        "-vvv",
        "--json",
        "--no-ansi",
        "--la=false",
        "--lf=test.log",
        "--ll=debug",
        "--force",
    ]
    output = Output(
        log_append="false",
        log_file=str(expand_path("test.log")),
        log_level="debug",
        term_features=TermFeatures(color=False, links=False),
        verbosity=3,
        display="json",
    )

    monkeypatch.setattr("sys.argv", sysargs)
    cli = Cli()
    cli.init_output()
    assert vars(cli.output) == vars(output)


def test_cli_main(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test CLI main method.

    Args:
        capsys: Pytest capsys fixture.
        tmp_path: Temporary path.
        monkeypatch: Pytest monkeypatch fixture.
    """
    sysargs = [
        "ansible-creator",
        "init",
        "testns.testcol",
        f"--init-path={tmp_path}/testns/testcol",
        "--json",
        "--force",
        "-vvv",
    ]

    monkeypatch.setattr("sys.argv", sysargs)
    cli = Cli()
    cli.init_output()
    cli.run()

    result = capsys.readouterr().out
    # check stdout
    assert re.search("collection project created", result) is not None


@pytest.mark.parametrize(argnames=["project"], argvalues=[["collection"], ["playbook"]])
def test_collection_name_short(
    project: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test invalid collection name.

    Args:
        project: The project type.
        monkeypatch: Pytest monkeypatch fixture.
    """
    sysargs = [
        "ansible-creator",
        "init",
        project,
        "a.b",
    ]
    monkeypatch.setattr("sys.argv", sysargs)

    cli = Cli()

    msg = "Both the collection namespace and name must be longer than 2 characters."
    assert any(msg in log.message for log in cli.pending_logs)


@pytest.mark.parametrize(argnames=["project"], argvalues=[["collection"], ["playbook"]])
def test_collection_name_invalid(
    project: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test invalid collection name.

    Args:
        project: The project type.
        monkeypatch: Pytest monkeypatch fixture.
    """
    sysargs = [
        "ansible-creator",
        "init",
        project,
        "$____.^____",
    ]
    monkeypatch.setattr("sys.argv", sysargs)

    cli = Cli()

    msg = (
        "Collection name can only contain lower case letters, underscores,"
        " and numbers and cannot begin with an underscore."
    )
    assert any(msg in log.message for log in cli.pending_logs)


def test_is_a_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test is a tty.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    sysargs = [
        "ansible-creator",
        "init",
        "testorg.testcol",
        f"{Path.home()}",
    ]

    monkeypatch.setattr("sys.argv", sysargs)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    cli = Cli()
    cli.init_output()
    assert cli.output.term_features.color is True
    assert cli.output.term_features.links is True
    assert cli.output.term_features.any_enabled() is True


def test_not_a_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test not a tty.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    sysargs = [
        "ansible-creator",
        "init",
        "testorg.testcol",
        f"{Path.home()}",
    ]

    monkeypatch.setattr("sys.argv", sysargs)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)

    cli = Cli()
    cli.init_output()
    assert cli.output.term_features.color is False
    assert cli.output.term_features.links is False
    assert cli.output.term_features.any_enabled() is False


def test_main(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Test cli main.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        capsys: Pytest capsys fixture.
    """
    monkeypatch.setattr("sys.argv", ["ansible-creator", "--help"])

    with pytest.raises(SystemExit):
        runpy.run_module("ansible_creator.cli", run_name="__main__")
    stdout, _stderr = capsys.readouterr()
    assert "The fastest way" in stdout


def test_proj_main(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Test project main.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        capsys: Pytest capsys fixture.
    """
    monkeypatch.setattr("sys.argv", ["ansible-creator", "--help"])

    with pytest.raises(SystemExit):
        runpy.run_module("ansible_creator", run_name="__main__")
    stdout, _stderr = capsys.readouterr()
    assert "The fastest way" in stdout


@pytest.mark.parametrize(argnames="args", argvalues=COMING_SOON, ids=lambda s: s.replace(" ", "_"))
def test_coming_soon(
    args: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test coming soon.

    Args:
        args: The name of the command.
        capsys: Pytest capsys fixture.
        monkeypatch: Pytest monkeypatch fixture.
    """
    arg_parts = args.split()
    resource = arg_parts[2]
    if resource in ("devcontainer", "devfile"):
        monkeypatch.setattr("sys.argv", ["ansible-creator", *arg_parts, "/foo"])
    elif resource in ("action", "filter", "lookup", "role"):
        monkeypatch.setattr("sys.argv", ["ansible-creator", *arg_parts, "name", "/foo"])
    else:
        pytest.fail("Fix this test with new COMING_SOON commands")

    with pytest.raises(SystemExit):
        cli_main()
    stdout, stderr = capsys.readouterr()
    assert f"`{args}` command is coming soon" in stdout
    assert "Goodbye" in stderr
