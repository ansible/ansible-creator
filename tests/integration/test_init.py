"""Unit tests for ansible-creator init."""

from __future__ import annotations

import re
import sys
from textwrap import dedent


def test_run_help(cli):
    result = cli("ansible-creator --help")
    assert result.returncode == 0

    # temporary assertion fix until we write custom helper
    if sys.version_info < (3, 10):
        assert (
            dedent(
                """\
                usage: ansible-creator [-h] [--version] {init} ...

                Tool to scaffold Ansible Content. Get started by looking at the help text.

                optional arguments:
                -h, --help  show this help message and exit
                --version   Print ansible-creator version and exit.

                Commands:
                {init}      The subcommand to invoke.
                    init      Initialize an Ansible Collection.
                """,
            )
            in result.stdout
        )
    else:
        assert (
            dedent(
                """\
                usage: ansible-creator [-h] [--version] {init} ...

                Tool to scaffold Ansible Content. Get started by looking at the help text.

                options:
                  -h, --help  show this help message and exit
                  --version   Print ansible-creator version and exit.

                Commands:
                  {init}      The subcommand to invoke.
                    init      Initialize an Ansible Collection.
                """,
            )
            in result.stdout
        )


def test_run_no_subcommand(cli):
    result = cli("ansible-creator")
    assert result.returncode != 0
    assert (
        dedent(
            """\
            usage: ansible-creator [-h] [--version] {init} ...
            ansible-creator: error: the following arguments are required: subcommand
            """,
        )
        in result.stderr
    )


def test_run_init_no_input(cli):
    result = cli("ansible-creator init")
    assert result.returncode != 0
    assert (
        "ansible-creator init: error: the following arguments are required: collection"
        in result.stderr
    )


def test_run_init_basic(cli, tmp_path):
    result = cli(f"ansible-creator init testorg.testcol --init-path {tmp_path}")
    assert result.returncode == 0

    # check stdout
    assert (
        re.search("Note: collection testorg.testcol created at", result.stdout)
        is not None
    )

    # fail to override existing collection with force=false (default)
    result = cli(f"ansible-creator init testorg.testcol --init-path {tmp_path}")
    assert result.returncode != 0
    assert (
        re.search(
            f"Error: The directory {tmp_path}/testorg/testcol already exists.",
            result.stderr,
        )
        is not None
    )
    assert "You can use --force to re-initialize this directory." in result.stderr
    assert "However it will delete ALL existing contents in it." in result.stderr

    # override existing collection with force=true
    result = cli(f"ansible-creator init testorg.testcol --init-path {tmp_path} --force")
    assert result.returncode == 0
    assert (
        re.search("Warning: re-initializing existing directory", result.stdout)
        is not None
    )