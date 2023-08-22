"""The ansible-creator CLI."""

import argparse
import logging

from importlib import import_module
from ansible_creator.exceptions import CreatorError
from ansible_creator.logger import ColoredFormatter, ExitOnExceptionHandler

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "source"


class AnsibleCreatorCLI:
    """Class representing the ansible-creator CLI."""

    def __init__(self):
        """Initialize the CLI and parse CLI args."""
        self.args = self.parse_args()
        self.logger = None

    def init_logger(self):
        """Initialize the logger."""
        self.logger = logging.getLogger("ansible-creator")
        stream_handler = ExitOnExceptionHandler()
        stream_handler.setLevel(logging.DEBUG)
        colored_formatter = ColoredFormatter(
            "%(levelname)s %(message)s",
        )
        stream_handler.setFormatter(colored_formatter)
        self.logger.addHandler(stream_handler)
        if self.args.verbose:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

    def parse_args(self):
        """Start parsing args passed from CLI.

        :returns: A dictionary of CLI args.
        """
        parser = argparse.ArgumentParser(
            description=(
                "Tool to scaffold Ansible Content. Get started by looking at the help text."
            )
        )

        parser.add_argument(
            "--version",
            action="version",
            version=__version__,
            help="Print ansible-creator version and exit.",
        )

        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Increase output verbosity.",
        )

        subparsers = parser.add_subparsers(help="The command to invoke.", dest="action")
        subparsers.required = True

        # 'init' command parser

        init_command_parser = subparsers.add_parser(
            "init",
            help="Initialize an Ansible Collection.",
            description=("Creates the skeleton framework of an Ansible collection."),
        )

        init_command_parser.add_argument(
            "collection_name",
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

        # 'create' command parser

        create_command_parser = subparsers.add_parser(
            "create",
            help="Scaffold Ansible Content.",
            description=(
                "Scaffold Ansible Content based on the definition provided "
                " through -f or --file options."
            ),
        )

        create_command_parser.add_argument(
            "-f",
            "--file",
            default="./content.yaml",
            help="A YAML file containing definition of Ansible Content(s) to be scaffolded.",
        )

        sample_command_parser = subparsers.add_parser(
            "sample",
            help="Generate a sample content.yaml file.",
            description=(
                "Generate a sample content.yaml file to serve as a reference."
            ),
        )

        sample_command_parser.add_argument(
            "-f",
            "--file",
            default="./contents.yaml",
            help="Path where the sample content.yaml file will be added. Default: ./",
        )

        args = parser.parse_args()

        return args

    def run(self):
        """Dispatch work to correct action class."""
        args = vars(self.args)
        self.logger.debug("parsed args %s", str(args))
        action = args["action"]
        action_modules = f"ansible_creator.actions.{action}"
        action_prefix = "Creator" + f"{action}".capitalize()

        try:
            self.logger.info("starting requested action '%s'", action)
            action_class = getattr(import_module(action_modules), action_prefix)
            self.logger.debug("found action class %s", action_class)
            action_class(**args).run()
        except CreatorError as exc:
            self.logger.error(str(exc))

        self.logger.debug("successfully exiting ansible-creator")


def main():
    """Entry point for ansible-creator CLI."""
    cli = AnsibleCreatorCLI()
    cli.init_logger()
    cli.run()


if __name__ == "__main__":
    main()
