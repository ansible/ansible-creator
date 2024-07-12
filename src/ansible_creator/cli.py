"""The ansible-creator Cli."""

from __future__ import annotations

import os
import sys

from importlib import import_module

from ansible_creator.arg_parser import RootParser
from ansible_creator.config import Config
from ansible_creator.exceptions import CreatorError
from ansible_creator.output import Output
from ansible_creator.utils import TermFeatures, expand_path


try:
    from typing import Any

    from ._version import version as __version__
except ImportError:
    __version__ = "source"


class Cli:
    """Class representing the ansible-creator Cli."""

    def __init__(self: Cli) -> None:
        """Initialize the Cli and parse Cli args."""
        self.args: dict[str, Any]
        self.output: Output
        self.pending_logs: list[tuple[str, str]]
        self.term_features: TermFeatures
        self.parse_args()

    def init_output(self: Cli) -> None:
        """Initialize the output object."""
        no_ansi = self.args.pop("no_ansi")
        if not sys.stdout.isatty():
            self.term_features = TermFeatures(color=False, links=False)
        else:
            self.term_features = TermFeatures(
                color=False if os.environ.get("NO_COLOR") else not no_ansi,
                links=not no_ansi,
            )

        self.output = Output(
            log_append=self.args.pop("log_append"),
            log_file=str(expand_path(self.args.pop("log_file"))),
            log_level=self.args.pop("log_level"),
            term_features=self.term_features,
            verbosity=self.args.pop("verbose"),
            display="json" if self.args.pop("json") else "text",
        )

    def parse_args(self: Cli) -> None:
        """Start parsing args passed from Cli."""
        args, pending_logs = RootParser().parse_args()
        self.args = vars(args)
        self.pending_logs = pending_logs

    def process_pending_logs(self: Cli) -> None:
        """Log any pending logs."""
        for msg in self.pending_logs:
            getattr(self.output, msg.prefix.value.lower())(msg.message)

    def run(self: Cli) -> None:
        """Dispatch work to correct subcommand class."""
        self.output.debug(msg=f"parsed args {self.args!s}")
        subcommand = self.args["subcommand"]
        subcommand_module = f"ansible_creator.subcommands.{subcommand}"
        subcommand_cls = f"{subcommand}".capitalize()
        self.args.update({"creator_version": __version__})

        try:
            self.output.debug(msg=f"starting requested action '{subcommand}'")
            subcommand = getattr(import_module(subcommand_module), subcommand_cls)
            self.output.debug(f"found action class {subcommand}")
            subcommand(config=Config(**self.args, output=self.output)).run()
        except CreatorError as exc:
            self.output.error(str(exc))
            sys.exit(1)

        self.output.debug(msg="exiting ansible-creator")


def main() -> None:
    """Entry point for ansible-creator Cli."""
    cli = Cli()
    cli.init_output()
    cli.process_pending_logs()
    cli.run()


if __name__ == "__main__":
    main()
