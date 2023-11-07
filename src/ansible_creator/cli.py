"""The ansible-creator Cli."""

from __future__ import annotations

import argparse
import os
import sys

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

from ansible_creator.config import Config
from ansible_creator.exceptions import CreatorError
from ansible_creator.output import Output
from ansible_creator.utils import TermFeatures, expand_path


try:
    from ._version import version as __version__
except ImportError:
    __version__ = "source"

if TYPE_CHECKING:
    from argparse import Namespace


class Cli:
    """Class representing the ansible-creator Cli."""

    def __init__(self: Cli) -> None:
        """Initialize the Cli and parse Cli args."""
        self.args: Namespace = self.parse_args()
        self.output: Output
        self.term_features: TermFeatures

    def init_output(self: Cli) -> None:
        """Initialize the output object."""
        no_ansi = self.args.no_ansi
        if not sys.stdout.isatty():
            self.term_features = TermFeatures(color=False, links=False)
        else:
            self.term_features = TermFeatures(
                color=False if os.environ.get("NO_COLOR") else not no_ansi,
                links=not no_ansi,
            )

        self.output = Output(
            log_append=self.args.log_append,
            log_file=expand_path(self.args.log_file),
            log_level=self.args.log_level,
            term_features=self.term_features,
            verbosity=self.args.verbose,
            display="json" if self.args.json else "text",
        )

    def parse_args(self: Cli) -> argparse.Namespace:
        """Start parsing args passed from Cli.

        :returns: A dictionary of Cli args.
        """
        parent_parser = argparse.ArgumentParser(add_help=False)

        parent_parser.add_argument(
            "--na",
            "--no-ansi",
            action="store_true",
            default=False,
            dest="no_ansi",
            help="Disable the use of ANSI codes for terminal color.",
        )

        parent_parser.add_argument(
            "--lf",
            "--log-file <file>",
            dest="log_file",
            default=str(Path.cwd() / "ansible-creator.log"),
            help="Log file to write to.",
        )

        parent_parser.add_argument(
            "--ll",
            "--log-level <level>",
            dest="log_level",
            default="notset",
            choices=["notset", "debug", "info", "warning", "error", "critical"],
            help="Log level for file output.",
        )

        parent_parser.add_argument(
            "--la",
            "--log-append <bool>",
            dest="log_append",
            choices=["true", "false"],
            default="true",
            help="Append to log file.",
        )

        parent_parser.add_argument(
            "--json",
            dest="json",
            action="store_true",
            default=False,
            help="Output messages as JSON",
        )

        parent_parser.add_argument(
            "-v",
            dest="verbose",
            action="count",
            default=0,
            help="Give more Cli output. Option is additive, and can be used up to 3 times.",
        )

        parser = argparse.ArgumentParser(
            description=(
                "Tool to scaffold Ansible Content. Get started by looking at the help text."
            ),
        )

        parser.add_argument(
            "--version",
            action="version",
            version=__version__,
            help="Print ansible-creator version and exit.",
        )

        subparsers = parser.add_subparsers(
            help="The subcommand to invoke.",
            title="Commands",
            dest="subcommand",
        )
        subparsers.required = True

        # 'init' command parser

        init_command_parser = subparsers.add_parser(
            "init",
            help="Initialize an Ansible Collection.",
            description=("Creates the skeleton framework of an Ansible collection."),
            parents=[parent_parser],
        )

        init_command_parser.add_argument(
            "collection",
            help="The collection name in the format ``<namespace>.<collection>``.",
        )

        init_command_parser.add_argument(
            "--init-path",
            default="./",
            help="The path in which the skeleton collection will be created. The default is the "
            "current working directory.",
        )

        init_command_parser.add_argument(
            "--force",
            default=False,
            action="store_true",
            help="Force re-initialize the specified directory as an Ansible collection.",
        )

        return parser.parse_args()

    def run(self: Cli) -> None:
        """Dispatch work to correct subcommand class."""
        self.output.debug(msg=f"parsed args {self.args!s}")
        subcommand = self.args.subcommand
        subcommand_module = f"ansible_creator.subcommands.{subcommand}"
        subcommand_cls = f"{subcommand}".capitalize()
        args = vars(self.args)
        args.update({"creator_version": __version__})

        try:
            self.output.debug(msg=f"starting requested action '{subcommand}'")
            subcommand = getattr(import_module(subcommand_module), subcommand_cls)
            self.output.debug(f"found action class {subcommand}")
            subcommand(config=Config(**args), output=self.output).run()
        except CreatorError as exc:
            self.output.error(str(exc))
            sys.exit(1)

        self.output.debug(msg="exiting ansible-creator")


def main() -> None:
    """Entry point for ansible-creator Cli."""
    cli = Cli()
    cli.init_output()
    cli.run()


if __name__ == "__main__":
    main()
