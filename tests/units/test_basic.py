"""Basic unit tests for ansible-creator."""

from __future__ import annotations

import re
import sys

from pathlib import Path

import pytest

from ansible_creator.cli import Cli
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
    linux_path = Path("/home/ansible")
    mac_os_path = Path("/System/Volumes/Data/home/ansible")
    assert app_config.init_path in [linux_path, mac_os_path]


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
                "project": "collection",  # default value
                "scm_org": None,
                "scm_project": None,
            },
        ],
        [
            [
                "ansible-creator",
                "init",
                "--project=ansible-project",
                "--init-path=/home/ansible/my-ansible-project",
            ],
            {
                "subcommand": "init",
                "no_ansi": False,
                "log_file": str(Path.cwd() / "ansible-creator.log"),
                "log_level": "notset",
                "log_append": "true",
                "json": False,
                "verbose": 0,
                "collection": None,
                "init_path": "/home/ansible/my-ansible-project",
                "force": False,
                "project": "ansible-project",
                "scm_org": None,
                "scm_project": None,
            },
        ],
        [
            [
                "ansible-creator",
                "init",
                "testorg.testcol",
                "--init-path=/home/ansible",
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
                "init_path": "/home/ansible",
                "force": True,
                "project": "collection",  # default value
                "scm_org": None,
                "scm_project": None,
            },
        ],
        [
            [
                "ansible-creator",
                "init",
                "--project=ansible-project",
                "--scm-org=weather",
                "--scm-project=demo",
                "--init-path=/home/ansible/my-ansible-project",
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
                "collection": None,
                "init_path": "/home/ansible/my-ansible-project",
                "force": True,
                "project": "ansible-project",
                "scm_org": "weather",
                "scm_project": "demo",
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
    assert vars(Cli().parse_args()) == expected


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


def test_cli_init_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test CLI init_output method.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    sysargs = [
        "ansible-creator",
        "init",
        "testorg.testcol",
        "--init-path=/home/ansible",
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
    assert re.search("collection testns.testcol created", result) is not None
