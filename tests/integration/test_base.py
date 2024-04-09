"""Unit tests for ansible-creator basic cli."""

from __future__ import annotations

import re
import sys
from textwrap import dedent


def test_run_help(cli):
    result = cli("ansible-creator --help")
    assert result.returncode == 0

    # temporary assertion fix until we write custom helper
    if sys.version_info < (3, 10):
        text = dedent(
            """\
            usage: ansible-creator [-h] [--version] {init,docs} ...

            Tool to scaffold Ansible Content. Get started by looking at the help text.

            optional arguments:
              -h, --help   show this help message and exit
              --version    Print ansible-creator version and exit.

            Commands:
              {init,docs}  The subcommand to invoke.
                init       Initialize an Ansible Collection.
                docs       (Re)generate documentation for an Ansible Collection.
            """,
        )
    else:
        text = dedent(
            """\
            usage: ansible-creator [-h] [--version] {init,docs} ...

            Tool to scaffold Ansible Content. Get started by looking at the help text.

            options:
              -h, --help   show this help message and exit
              --version    Print ansible-creator version and exit.

            Commands:
              {init,docs}  The subcommand to invoke.
                init       Initialize an Ansible Collection.
                docs       (Re)generate documentation for an Ansible Collection.
            """,
        )
    assert text in result.stdout


def test_run_no_subcommand(cli):
    result = cli("ansible-creator")
    assert result.returncode != 0
    assert (
        dedent(
            """\
            usage: ansible-creator [-h] [--version] {init,docs} ...
            ansible-creator: error: the following arguments are required: subcommand
            """,
        )
        in result.stderr
    )
