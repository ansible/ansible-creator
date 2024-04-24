"""Basic unit tests for ansible-creator."""

from pathlib import Path

import pytest
import re
import sys

from ansible_creator.cli import Cli
from ansible_creator.config import Config
from ansible_creator.utils import expand_path, TermFeatures
from ansible_creator.output import Output


def test_expand_path() -> None:
    """Test expand_path utils."""
    assert (
        expand_path("~/$DEV_WORKSPACE/namespace/collection")
        == "/home/ansible/collections/ansible_collections/namespace/collection"
    )


def test_configuration_class(output: Output) -> None:
    """Test Config() dataclass post_init."""
    cli_args: dict = {
        "creator_version": "0.0.1",
        "subcommand": "init",
        "collection": "testorg.testcol",
        "init_path": "$HOME",
        "output": output,
    }
    app_config = Config(**cli_args)
    assert app_config.namespace == "testorg"
    assert app_config.collection_name == "testcol"
    assert app_config.init_path == "/home/ansible"


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
def test_cli_parser(monkeypatch, sysargs, expected) -> None:
    """Test CLI args parsing."""
    monkeypatch.setattr("sys.argv", sysargs)
    assert vars(Cli().parse_args()) == expected


def test_missing_j2(monkeypatch) -> None:
    """Test missing Jinja2."""

    fail_msg = (
        "jinja2 is required but does not appear to be installed."
        "It can be installed using `pip install jinja2`"
    )

    monkeypatch.setattr("sys.path", [])
    monkeypatch.delitem(sys.modules, "jinja2", raising=False)
    monkeypatch.delitem(sys.modules, "ansible_creator.templar", raising=False)

    import ansible_creator.templar

    assert ansible_creator.templar.HAS_JINJA2 == False
    with pytest.raises(ImportError, match=fail_msg):
        ansible_creator.templar.Templar()


def test_cli_init_output(monkeypatch) -> None:
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
        log_file=expand_path("test.log"),
        log_level="debug",
        term_features=TermFeatures(color=False, links=False),
        verbosity=3,
        display="json",
    )

    monkeypatch.setattr("sys.argv", sysargs)
    cli = Cli()
    cli.init_output()
    assert vars(cli.output) == vars(output)


def test_cli_main(capsys, tmp_path, monkeypatch) -> None:
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
