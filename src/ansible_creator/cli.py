"""The ansible-creator CLI"""

import argparse
from .actions.init import AnsibleCreatorInit
from .actions.create import AnsibleCreatorCreate
from .constants import MessageColors


class AnsibleCreatorCLI:
    def __init__(self):
        self.args = self.parse_args()

    def get_version(self):
        try:
            from ._version import version as __version__
        except ImportError:
            __version__ = "source"

        return __version__

    def parse_args(self):
        parser = argparse.ArgumentParser(
            description=(
                "Tool to scaffold Ansible Content. "
                "Get started by looking at the help text."
            )
        )

        parser.add_argument(
            "--version",
            action="version",
            version=self.get_version(),
            help="Print ansible-creator version and exit.",
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
            default="./ansible-contents.yaml",
            help="A YAML file containing definition of Ansible Content(s) to be scaffolded.",
        )

        args = parser.parse_args()

        return args

    def run(self):
        args = vars(self.args)
        if args["action"] == "init":
            AnsibleCreatorInit(**args).run()
        elif args["action"] == "create":
            AnsibleCreatorCreate(**args).run()


def main():
    cli = AnsibleCreatorCLI()
    cli.run()


if __name__ == "__main__":
    main()
