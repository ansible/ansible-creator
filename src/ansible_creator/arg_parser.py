"""Parse the command line arguments."""

from __future__ import annotations

import argparse
import re
import sys

from argparse import HelpFormatter
from operator import attrgetter
from pathlib import Path
from typing import TYPE_CHECKING

from ansible_creator.output import Level, Msg


if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any


try:
    from ._version import version as __version__  # type: ignore[unused-ignore,import-not-found]
except ImportError:  # pragma: no cover
    __version__ = "source"

MIN_COLLECTION_NAME_LEN = 2


def valid_collection_name(collection: str) -> str:
    """Validate the collection name.

    Args:
        collection: The collection name to validate

    Raises:
        argparse.ArgumentTypeError: If the collection name is invalid

    Returns:
        The validated collection name
    """
    fqcn = collection.split(".", maxsplit=1)
    name_filter = re.compile(r"^(?!_)[a-z0-9_]+$")

    if not name_filter.match(fqcn[0]) or not name_filter.match(fqcn[-1]):
        msg = (
            "Collection name can only contain lower case letters, underscores, and numbers"
            " and cannot begin with an underscore."
        )
        raise argparse.ArgumentTypeError(msg)

    if len(fqcn[0]) <= MIN_COLLECTION_NAME_LEN or len(fqcn[-1]) <= MIN_COLLECTION_NAME_LEN:
        msg = "Both the collection namespace and name must be longer than 2 characters."
        raise argparse.ArgumentTypeError(msg)
    return collection


class RootParser:
    """A parser for the command line arguments."""

    def __init__(self: RootParser) -> None:
        """Initialize the parser."""
        self.sys_argv = sys.argv[1:]
        self.args: argparse.Namespace
        self.pending_logs: list[Msg] = []
        self.deprecated_flags_used: bool = False

    def _add_common(self, parser: ArgumentParser) -> None:
        """Add common arguments to the parser.

        Args:
            parser: The parser to add the arguments to
        """
        parser.add_argument(
            "--na",
            "--no-ansi",
            action="store_true",
            default=False,
            dest="no_ansi",
            help="Disable the use of ANSI codes for terminal color.",
        )

        parser.add_argument(
            "--lf",
            "--log-file <file>",
            dest="log_file",
            default=str(Path.cwd() / "ansible-creator.log"),
            help="Log file to write to.",
        )

        parser.add_argument(
            "--ll",
            "--log-level <level>",
            dest="log_level",
            default="notset",
            choices=["notset", "debug", "info", "warning", "error", "critical"],
            help="Log level for file output.",
        )

        parser.add_argument(
            "--la",
            "--log-append <bool>",
            dest="log_append",
            choices=["true", "false"],
            default="true",
            help="Append to log file.",
        )

        parser.add_argument(
            "--json",
            dest="json",
            action="store_true",
            default=False,
            help="Output messages as JSON",
        )

        parser.add_argument(
            "-v",
            dest="verbose",
            action="count",
            default=0,
            help="Give more Cli output. Option is additive, and can be used up to 3 times.",
        )

    def _add_init_common(self, parser: ArgumentParser) -> None:
        """Add common init arguments to the parser.

        Args:
            parser: The parser to add the arguments to
        """
        parser.add_argument(
            "--f",
            "--force",
            default=False,
            dest="force",
            action="store_true",
            help="Force re-initialize the specified directory as an Ansible collection.",
        )

    def _next_argv(self: RootParser) -> list[str]:
        """Get the next argument from the sys.argv.

        Returns:
            The next argument
        """
        try:
            return [self.sys_argv.pop(0)]
        except IndexError:
            return []

    def parse_args(self: RootParser) -> tuple[argparse.Namespace, list[Msg]]:
        """Parse the root arguments.

        Returns:
            The parsed arguments and any pending logs
        """
        parser = ArgumentParser(
            description="The fastest way to generate all your ansible content.",
            formatter_class=CustomHelpFormatter,
        )
        subparsers = parser.add_subparsers(
            title="Commands",
            dest="subcommand",
            metavar="",
        )
        subparsers.add_parser(
            "init",
            formatter_class=CustomHelpFormatter,
            help="Create a new Ansible project.",
        )

        args = parser.parse_args(self._next_argv())
        if args.subcommand is None:
            parser.print_help()
            sys.exit(1)
        self.args = args
        getattr(self, args.subcommand)()

        # Some cleanup for unused arguments
        del self.args.unused_init_path
        del self.args.unused_project
        # The internal still reference the old project name
        if self.args.project == "playbook":
            self.args.project = "ansible-project"
            self.args.collection = None

        return self.args, self.pending_logs

    def init(self: RootParser) -> None:
        """Initialize an Ansible project."""
        parser = ArgumentParser(
            description="Create a new Ansible project.",
            formatter_class=CustomHelpFormatter,
            usage="ansible-creator init [PROJECT TYPE]",
        )
        parser.add_argument(
            "--project",
            choices=["ansible-project", "collection"],
            dest="unused_project",
            default="collection",
            help="(deprecated) Project type to scaffold."
            " Valid choices are collection, ansible-project.",
        )
        subparsers = parser.add_subparsers(
            title="Project types",
            dest="project",
            metavar="",
        )
        subparsers.add_parser(
            "collection",
            formatter_class=CustomHelpFormatter,
            help="Create a new Ansible collection project.",
        )
        subparsers.add_parser(
            "playbook",
            formatter_class=CustomHelpFormatter,
            help="Create a new Ansible playbook project.",
        )

        # if the user requests help without a project, print the init help and exit
        # otherwise collection help would be shown as we set a default subcommand
        # for backward compatibility
        if "-h" in self.sys_argv or "--help" in self.sys_argv and len(self.sys_argv) == 1:
            parser.print_help()
            sys.exit(0)

        # if no more args are provided show the help for init
        # this is to prevent the collection help from being shown
        if not self.sys_argv:
            parser.print_help()
            sys.exit(1)

        # if the user has specified a project type, use it now to set a default
        # project type for backward compatibility
        if any("--project" in argv for argv in self.sys_argv):
            msg = "The `project` flag is no longer needed and will be removed."
            self.pending_logs.append(Msg(prefix=Level.WARNING, message=msg))
            tmp_parser = argparse.ArgumentParser()
            tmp_parser.add_argument("--project", help="")
            tmp_args, _extra = tmp_parser.parse_known_args(self.sys_argv)
            possible_values = ["collection", "ansible-project"]
            if tmp_args.project not in possible_values:
                parser.print_help()
                sys.exit(1)
            self.sys_argv = [arg for arg in self.sys_argv if not arg.startswith("--project")]
            self.sys_argv = [arg for arg in self.sys_argv if arg not in possible_values]
            if tmp_args.project == "ansible-project":
                self.sys_argv.insert(0, "playbook")
            else:
                self.sys_argv.insert(0, "collection")
            msg = f"project flag removed, sys.argv now: {self.sys_argv}"
            self.pending_logs.append(Msg(prefix=Level.DEBUG, message=msg))
            self.deprecated_flags_used = True

        # Set the default init type to collection for backward compatibility
        if not self.sys_argv or self.sys_argv[0] not in ["collection", "playbook"]:
            self.sys_argv.insert(0, "collection")

        args = parser.parse_args(self._next_argv())

        self.args = argparse.Namespace(**vars(args), **vars(self.args))
        getattr(self, f"{self.args.subcommand}_{args.project}")()

    def init_collection(self: RootParser) -> None:
        """Initialize an Ansible collection."""
        parser = ArgumentParser(
            description="Create a new Ansible collection project.",
            formatter_class=CustomHelpFormatter,
            usage="ansible-creator init collection [COLLECTION] [PATH]",
        )
        parser.add_argument(
            "--init-path",
            default="./",
            dest="unused_init_path",
            help="(deprecated) The path in which the skeleton collection will be created."
            " The default is the current working directory.",
        )
        parser.add_argument(
            "collection",
            help="The collection name in the format '<namespace>.<collection>'.",
            type=valid_collection_name,
        )
        parser.add_argument(
            "init_path",
            default="./",
            metavar="path",
            nargs="?",
            help="The destination directory for the collection project. The default is the "
            "current working directory.",
        )
        # if init-path is provided, set the positional path
        if any("--init-path" in argv for argv in self.sys_argv):
            msg = "The `init-path` flag is no longer needed and will be removed."
            self.pending_logs.append(Msg(prefix=Level.WARNING, message=msg))
            tmp_parser = argparse.ArgumentParser()
            tmp_parser.add_argument("--init-path", help="")
            tmp_args, _extra = tmp_parser.parse_known_args(self.sys_argv)
            self.sys_argv = [arg for arg in self.sys_argv if not arg.startswith("--init-path")]
            self.sys_argv = [arg for arg in self.sys_argv if arg != tmp_args.init_path]
            self.sys_argv.insert(1, tmp_args.init_path)
            msg = f"init-path flag removed, sys.argv now: {self.sys_argv}"
            self.pending_logs.append(Msg(prefix=Level.DEBUG, message=msg))
            self.deprecated_flags_used = True

        self._add_common(parser)
        self._add_init_common(parser)

        msg = "args right before parse: {self.sys_argv}"
        self.pending_logs.append(Msg(prefix=Level.DEBUG, message=msg))
        args = parser.parse_args(self.sys_argv)
        msg = (
            "Please use the following command in the future:"
            f" `ansible-creator {self.args.subcommand} {self.args.project}"
            f" {' '.join(self.sys_argv)}`"
        )
        prefix = Level.HINT if self.deprecated_flags_used else Level.DEBUG
        self.pending_logs.append(Msg(prefix=prefix, message=msg))
        self.args = argparse.Namespace(**vars(args), **vars(self.args))

    def init_playbook(self: RootParser) -> None:
        """Initialize an Ansible playbook."""
        parser = ArgumentParser(
            description="Create a new Ansible playbook project.",
            formatter_class=CustomHelpFormatter,
            usage="ansible-creator init playbook [COLLECTION] [PATH]",
        )
        parser.add_argument(
            "--init-path",
            default="./",
            dest="unused_init_path",
            help="(deprecated) The path in which the skeleton collection will be created."
            " The default is the current working directory.",
        )
        parser.add_argument(
            "--scm-org",
            help=(
                "(deprecated) The SCM org where the ansible-project will be hosted."
                " This value is used as the namespace for the playbook adjacent collection."
            ),
        )
        parser.add_argument(
            "--scm-project",
            help=(
                "(deprecated) The SCM project where the ansible-project will be hosted."
                "This value is used as the collection_name for the playbook adjacent collection."
                " Required when `--project=ansible-project`."
            ),
        )
        parser.add_argument(
            "collection",
            help="The name for the playbook adjacent collection in the format"
            "'<namespace>.<collection>'.",
            type=valid_collection_name,
        )

        parser.add_argument(
            "init_path",
            default="./",
            metavar="path",
            nargs="?",
            help="The destination directory for the playbook project. The default is the "
            "current working directory.",
        )

        # if --init-path is provided, prepend sys_argv with the path
        if any("--init-path" in argv for argv in self.sys_argv):
            msg = "The `init-path` flag is no longer needed and will be removed."
            self.pending_logs.append(Msg(prefix=Level.WARNING, message=msg))
            tmp_parser = argparse.ArgumentParser()
            tmp_parser.add_argument("--init-path", help="")
            tmp_args, _extra = tmp_parser.parse_known_args(self.sys_argv)
            self.sys_argv = [arg for arg in self.sys_argv if not arg.startswith("--init-path")]
            self.sys_argv = [arg for arg in self.sys_argv if arg != tmp_args.init_path]
            self.sys_argv.insert(0, tmp_args.init_path)
            msg = f"init-path flag removed, sys.argv now: {self.sys_argv}"
            self.pending_logs.append(Msg(prefix=Level.DEBUG, message=msg))
            self.deprecated_flags_used = True

        # if scm-org and scm-project are provided, set the positional collection
        scm_org_found = any("--scm-org" in argv for argv in self.sys_argv)
        scm_project_found = any("--scm-project" in argv for argv in self.sys_argv)
        if scm_org_found or scm_project_found:
            msg = "The `scm-org` and `scm-project` flags are no longer needed and will be removed."
            self.pending_logs.append(Msg(prefix=Level.WARNING, message=msg))
            tmp_parser = argparse.ArgumentParser()
            tmp_parser.add_argument("--scm-org", help="")
            tmp_parser.add_argument("--scm-project", help="")
            tmp_args, _extra = tmp_parser.parse_known_args(self.sys_argv)
            self.sys_argv = [arg for arg in self.sys_argv if not arg.startswith("--scm-org")]
            self.sys_argv = [arg for arg in self.sys_argv if not arg.startswith("--scm-project")]
            self.sys_argv = [arg for arg in self.sys_argv if arg != tmp_args.scm_org]
            self.sys_argv = [arg for arg in self.sys_argv if arg != tmp_args.scm_project]
            self.sys_argv.insert(0, f"{tmp_args.scm_org}.{tmp_args.scm_project}")
            msg = f"scm-org and/or scm-project flags removed, sys.argv now: {self.sys_argv}"
            self.pending_logs.append(Msg(prefix=Level.DEBUG, message=msg))
            self.deprecated_flags_used = True

        elif scm_org_found or scm_project_found:
            parser.print_help()
            sys.exit(1)

        self._add_common(parser)
        self._add_init_common(parser)

        msg = "args right before parse: {self.sys_argv}"
        self.pending_logs.append(Msg(prefix=Level.DEBUG, message=msg))
        args = parser.parse_args(self.sys_argv)

        # use the collection name to populate the scm org and project until
        # those can be dereferenced in the codebase
        if args.collection:
            args.scm_org, args.scm_project = args.collection.split(".", maxsplit=1)
        msg = (
            "Please use the following command in the future:"
            f" `ansible-creator {self.args.subcommand} {self.args.project}"
            f" {' '.join(self.sys_argv)}`"
        )
        prefix = Level.HINT if self.deprecated_flags_used else Level.DEBUG
        self.pending_logs.append(Msg(prefix=prefix, message=msg))
        self.args = argparse.Namespace(**vars(args), **vars(self.args))


class ArgumentParser(argparse.ArgumentParser):
    """A custom argument parser."""

    def add_argument(  # type: ignore[override]
        self: ArgumentParser,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Add an argument.

        Args:
            *args: The arguments
            **kwargs: The keyword arguments
        """
        if "choices" in kwargs:
            kwargs["help"] += f" (choices: {', '.join(kwargs['choices'])})"
        if "default" in kwargs and kwargs["default"] != "==SUPPRESS==":
            kwargs["help"] += f" (default: {kwargs['default']})"
        kwargs["help"] = kwargs["help"][0].upper() + kwargs["help"][1:]
        super().add_argument(*args, **kwargs)

    def add_argument_group(
        self: ArgumentParser,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> argparse._ArgumentGroup:
        """Add an argument group.

        Args:
            *args: The arguments
            **kwargs: The keyword arguments

        Returns:
            The argument group
        """
        group = super().add_argument_group(*args, **kwargs)
        if group.title:
            group.title = group.title.capitalize()
        return group


class CustomHelpFormatter(HelpFormatter):
    """A custom help formatter."""

    def __init__(self: CustomHelpFormatter, prog: str) -> None:
        """Initialize the help formatter.

        Args:
            prog: The program name
        """
        long_string = "--abc  --really_really_really_log"
        # 3 here accounts for the spaces in the ljust(6) below
        HelpFormatter.__init__(
            self,
            prog=prog,
            indent_increment=1,
            max_help_position=len(long_string) + 3,
        )

    def _format_action_invocation(
        self: CustomHelpFormatter,
        action: argparse.Action,
    ) -> str:
        """Format the action invocation.

        Args:
            action: The action to format

        Raises:
            ValueError: If more than 2 options are given

        Returns:
            The formatted action invocation
        """
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            (metavar,) = self._metavar_formatter(action, default)(1)
            return metavar

        if len(action.option_strings) == 1:
            return action.option_strings[0]

        max_variations = 2
        if len(action.option_strings) == max_variations:
            # Account for a --1234 --long-option-name
            return f"{action.option_strings[0].ljust(6)} {action.option_strings[1]}"
        msg = "Too many option strings"
        raise ValueError(msg)

    def add_arguments(self, actions: Iterable[argparse.Action]) -> None:
        """Add arguments sorted by option strings.

        Args:
            actions: The actions to add
        """
        actions = sorted(actions, key=attrgetter("option_strings"))
        super().add_arguments(actions)
