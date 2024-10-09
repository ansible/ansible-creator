"""Parse the command line arguments."""

from __future__ import annotations

import argparse
import contextlib
import re
import sys

from argparse import HelpFormatter
from operator import attrgetter
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

from ansible_creator.output import Level, Msg


if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any


try:
    import argcomplete

    HAS_ARGCOMPLETE = True
except ImportError:  # pragma: no cover
    HAS_ARGCOMPLETE = False

try:
    from ._version import version as __version__  # type: ignore[unused-ignore,import-not-found]
except ImportError:  # pragma: no cover
    __version__ = "source"

MIN_COLLECTION_NAME_LEN = 2

COMING_SOON = (
    "add resource devcontainer",
    "add resource devfile",
    "add resource role",
    "add plugin action",
    "add plugin filter",
    "add plugin lookup",
)


class Parser:
    """A parser for the command line arguments."""

    def __init__(self: Parser) -> None:
        """Initialize the parser."""
        self.args: argparse.Namespace
        self.pending_logs: list[Msg] = []

    def parse_args(self: Parser) -> tuple[argparse.Namespace, list[Msg]]:
        """Parse the root arguments.

        Returns:
            The parsed arguments and any pending logs
        """
        is_init = sys.argv[1:2] == ["init"]
        not_empty = sys.argv[2:] != []
        not_help = not any(arg in sys.argv for arg in ["-h", "--help"])
        if all((is_init, not_empty, not_help)):
            proceed = self.handle_deprecations()
            if not proceed:
                return argparse.Namespace(), self.pending_logs

        parser = ArgumentParser(
            description="The fastest way to generate all your ansible content.",
            formatter_class=CustomHelpFormatter,
        )
        parser.add_argument(
            "--version",
            action="version",
            help="Print ansible-creator version and exit.",
            version=__version__,
        )
        subparser = parser.add_subparsers(
            dest="subcommand",
            metavar="command",
            required=True,
        )
        self._add(subparser=subparser)
        self._init(subparser=subparser)

        if HAS_ARGCOMPLETE:
            argcomplete.autocomplete(parser)
        self.args = parser.parse_args()

        combinations = (
            ("subcommand", "type", "resource_type"),
            ("subcommand", "type", "plugin_type"),
            ("subcommand", "project"),
        )
        for combination in combinations:
            with contextlib.suppress(AttributeError):
                name = " ".join(getattr(self.args, part) for part in combination)

        if name in COMING_SOON:
            msg = f"The `{name}` command is coming soon. Please try in the next release."
            self.pending_logs.append(Msg(prefix=Level.HINT, message=msg))
            self.pending_logs.append(Msg(prefix=Level.CRITICAL, message="Goodbye."))
            return self.args, self.pending_logs

        return self.args, self.pending_logs

    def _add(self: Parser, subparser: SubParser[ArgumentParser]) -> None:
        """Add resources to an existing Ansible project.

        Args:
            subparser: The subparser to add the resources to
        """
        parser = subparser.add_parser(
            "add",
            formatter_class=CustomHelpFormatter,
            help="Add resources to an existing Ansible project.",
        )
        subparser = parser.add_subparsers(
            dest="type",
            required=True,
            metavar="content-type",
        )
        self._add_resource(subparser=subparser)
        self._add_plugin(subparser=subparser)

    def _add_args_common(self, parser: ArgumentParser) -> None:
        """Add common arguments to the parser.

        Args:
            parser: The parser to add common arguments to
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
            "--verbosity",
            dest="verbose",
            action="count",
            default=0,
            help="Give more Cli output. Option is additive, and can be used up to 3 times.",
        )

    def _add_args_init_common(self, parser: ArgumentParser) -> None:
        """Add common init arguments to the parser.

        Args:
            parser: The parser to add common init arguments to
        """
        parser.add_argument(
            "-f",
            "--force",
            default=False,
            dest="force",
            action="store_true",
            help="Force re-initialize the specified directory.",
        )
        parser.add_argument(
            "-o",
            "--overwrite",
            default=False,
            dest="overwrite",
            action="store_true",
            help="Overwrite existing files or directories.",
        )
        parser.add_argument(
            "-no",
            "--no-overwrite",
            default=False,
            dest="no_overwrite",
            action="store_true",
            help="Flag that restricts overwriting operation.",
        )

    def _add_args_plugin_common(self, parser: ArgumentParser) -> None:
        """Add common plugin arguments to the parser.

        Args:
            parser: The parser to add common plugin arguments to
        """
        parser.add_argument(
            "plugin_name",
            help="The name of the plugin to add.",
        )
        parser.add_argument(
            "path",
            default="./",
            help="The path to the Ansible collection. The default is the "
            "current working directory.",
        )

    def _add_resource(self: Parser, subparser: SubParser[ArgumentParser]) -> None:
        """Add resources to an existing Ansible project.

        Args:
            subparser: The subparser to add resource to
        """
        parser = subparser.add_parser(
            "resource",
            help="Add resources to an existing Ansible project.",
            formatter_class=CustomHelpFormatter,
        )
        subparser = parser.add_subparsers(
            dest="resource_type",
            metavar="resource-type",
            required=True,
        )
        self._add_resource_devcontainer(subparser=subparser)
        self._add_resource_devfile(subparser=subparser)
        self._add_resource_role(subparser=subparser)

    def _add_resource_devcontainer(self: Parser, subparser: SubParser[ArgumentParser]) -> None:
        """Add devcontainer files to an existing Ansible project.

        Args:
            subparser: The subparser to add devcontainer files to
        """
        parser = subparser.add_parser(
            "devcontainer",
            help="Add devcontainer files to an existing Ansible project.",
            formatter_class=CustomHelpFormatter,
        )

        parser.add_argument(
            "path",
            default="./",
            metavar="path",
            help="The destination directory for the devcontainer files. The default is the "
            "current working directory.",
        )

        self._add_args_common(parser)

    def _add_resource_devfile(self: Parser, subparser: SubParser[ArgumentParser]) -> None:
        """Add a devfile file to an existing Ansible project.

        Args:
            subparser: The subparser to add devfile file to
        """
        parser = subparser.add_parser(
            "devfile",
            help="Add a devfile file to an existing Ansible project.",
            formatter_class=CustomHelpFormatter,
        )
        parser.add_argument(
            "path",
            default="./",
            metavar="path",
            help="The destination directory for the devfile file. The default is the "
            "current working directory.",
        )
        self._add_args_common(parser)

    def _add_resource_role(self: Parser, subparser: SubParser[ArgumentParser]) -> None:
        """Add a role to an existing Ansible collection.

        Args:
            subparser: The subparser to add role to
        """
        parser = subparser.add_parser(
            "role",
            help="Add a role to an existing Ansible collection.",
            formatter_class=CustomHelpFormatter,
        )
        parser.add_argument(
            "role_name",
            help="The name of the role to add.",
        )
        parser.add_argument(
            "path",
            default="./",
            metavar="path",
            help="The path to the Ansible collection. The default is the "
            "current working directory.",
        )
        self._add_args_common(parser)

    def _add_plugin(self: Parser, subparser: SubParser[ArgumentParser]) -> None:
        """Add a plugin to an Ansible project.

        Args:
            subparser: The subparser to add plugin to
        """
        parser = subparser.add_parser(
            "plugin",
            help="Add a plugin to an Ansible collection",
            formatter_class=CustomHelpFormatter,
        )
        subparser = parser.add_subparsers(
            dest="plugin_type",
            metavar="plugin-type",
            required=True,
        )

        self._add_plugin_action(subparser=subparser)
        self._add_plugin_filter(subparser=subparser)
        self._add_plugin_lookup(subparser=subparser)

    def _add_plugin_action(self: Parser, subparser: SubParser[ArgumentParser]) -> None:
        """Add an action plugin to an existing Ansible collection project.

        Args:
            subparser: The subparser to add action plugin to
        """
        parser = subparser.add_parser(
            "action",
            help="Add an action plugin to an existing Ansible collection.",
            formatter_class=CustomHelpFormatter,
        )
        self._add_args_common(parser)
        self._add_args_plugin_common(parser)

    def _add_plugin_filter(self: Parser, subparser: SubParser[ArgumentParser]) -> None:
        """Add a filter plugin to an existing Ansible collection project.

        Args:
            subparser: The subparser to add filter plugin to
        """
        parser = subparser.add_parser(
            "filter",
            help="Add a filter plugin to an existing Ansible collection.",
            formatter_class=CustomHelpFormatter,
        )
        self._add_args_common(parser)
        self._add_args_plugin_common(parser)

    def _add_plugin_lookup(self: Parser, subparser: SubParser[ArgumentParser]) -> None:
        """Add a lookup plugin to an existing Ansible collection project.

        Args:
            subparser: The subparser to add lookup plugin to
        """
        parser = subparser.add_parser(
            "lookup",
            help="Add a lookup plugin to an existing Ansible collection.",
            formatter_class=CustomHelpFormatter,
        )
        self._add_args_common(parser)
        self._add_args_plugin_common(parser)

    def _init(self: Parser, subparser: SubParser[ArgumentParser]) -> None:
        """Initialize an Ansible project.

        Args:
            subparser: The subparser add init to
        """
        parser = subparser.add_parser(
            "init",
            formatter_class=CustomHelpFormatter,
            help="Initialize a new Ansible project.",
        )
        subparser = parser.add_subparsers(
            dest="project",
            metavar="project-type",
            required=True,
        )

        self._init_collection(subparser=subparser)
        self._init_playbook(subparser=subparser)

    def _init_collection(self: Parser, subparser: SubParser[ArgumentParser]) -> None:
        """Initialize an Ansible collection.

        Args:
            subparser: The subparser to add collection to
        """
        parser = subparser.add_parser(
            "collection",
            help="Create a new Ansible collection project.",
            formatter_class=CustomHelpFormatter,
        )
        parser.add_argument(
            "collection",
            help="The collection name in the format '<namespace>.<name>'.",
            metavar="collection-name",
            type=self._valid_collection_name,
        )
        parser.add_argument(
            "init_path",
            default="./",
            metavar="path",
            nargs="?",
            help="The destination directory for the collection project. The default is the "
            "current working directory.",
        )

        self._add_args_common(parser)
        self._add_args_init_common(parser)

    def _init_playbook(self: Parser, subparser: SubParser[ArgumentParser]) -> None:
        """Initialize an Ansible playbook.

        Args:
            subparser: The subparser to add playbook to
        """
        parser = subparser.add_parser(
            "playbook",
            help="Create a new Ansible playbook project.",
            formatter_class=CustomHelpFormatter,
        )

        parser.add_argument(
            "collection",
            help="The name for the playbook adjacent collection in the format"
            " '<namespace>.<name>'.",
            metavar="collection-name",
            type=self._valid_collection_name,
        )

        parser.add_argument(
            "init_path",
            default="./",
            metavar="path",
            nargs="?",
            help="The destination directory for the playbook project. The default is the "
            "current working directory.",
        )
        self._add_args_common(parser)
        self._add_args_init_common(parser)

    def _valid_collection_name(self, collection: str) -> str:
        """Validate the collection name.

        Args:
            collection: The collection name to validate

        Returns:
            The validated collection name
        """
        fqcn = collection.split(".", maxsplit=1)
        expected_parts = 2
        name_filter = re.compile(r"^(?!_)[a-z0-9_]+$")

        if len(fqcn) != expected_parts:
            msg = "Collection name must be in the format '<namespace>.<name>'."
            self.pending_logs.append(Msg(prefix=Level.CRITICAL, message=msg))
        elif not name_filter.match(fqcn[0]) or not name_filter.match(fqcn[1]):
            msg = (
                "Collection name can only contain lower case letters, underscores, and numbers"
                " and cannot begin with an underscore."
            )
            self.pending_logs.append(Msg(prefix=Level.CRITICAL, message=msg))
        elif len(fqcn[0]) <= MIN_COLLECTION_NAME_LEN or len(fqcn[1]) <= MIN_COLLECTION_NAME_LEN:
            msg = "Both the collection namespace and name must be longer than 2 characters."
            self.pending_logs.append(Msg(prefix=Level.CRITICAL, message=msg))
        return collection

    def handle_deprecations(self: Parser) -> bool:  # noqa: C901
        """Start parsing args passed from Cli.

        Returns:
            True if parsing can proceed, False otherwise
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("command", help="")
        parser.add_argument("collection", nargs="?", help="")
        parser.add_argument("--project", help="")
        parser.add_argument("--scm-org", help="")
        parser.add_argument("--scm-project", help="")
        parser.add_argument("--init-path", help="")
        args, extras = parser.parse_known_args()

        if args.collection in ["playbook", "collection"]:
            return True
        if args.project:
            msg = "The `project` flag is no longer needed and will be removed."
            self.pending_logs.append(Msg(prefix=Level.WARNING, message=msg))
        if not args.project:
            msg = "The default value `collection` for project type will be removed."
            self.pending_logs.append(Msg(prefix=Level.WARNING, message=msg))
            args.project = "collection"
        if args.scm_org:
            msg = "The `scm-org` flag is no longer needed and will be removed."
            self.pending_logs.append(Msg(prefix=Level.WARNING, message=msg))
        if args.scm_project:
            msg = "The `scm-project` flag is no longer needed and will be removed."
            self.pending_logs.append(Msg(prefix=Level.WARNING, message=msg))
        if args.init_path:
            msg = "The `init-path` flag is no longer needed and will be removed."
            self.pending_logs.append(Msg(prefix=Level.WARNING, message=msg))

        exit_msg = "The CLI has changed. Please refer to `--help` for the new syntax."
        if args.project == "ansible-project":
            args.project = "playbook"
            if not args.scm_org or not args.scm_project:
                self.pending_logs.append(Msg(prefix=Level.CRITICAL, message=exit_msg))
                return False
            msg = "The `ansible-project` project type is deprecated. Please use `playbook`."
            self.pending_logs.append(Msg(prefix=Level.WARNING, message=msg))
            args.collection = f"{args.scm_org}.{args.scm_project}"
        if args.project == "collection" and not args.collection:
            self.pending_logs.append(Msg(prefix=Level.CRITICAL, message=exit_msg))
            return False
        # ansible-creator init collection, ansible-creator init playbook

        base_cli = ["ansible-creator", args.command, args.project, args.collection]
        if args.init_path:
            base_cli.append(args.init_path)
        new_cli = base_cli + extras
        hint = f"Please use the following command in the future: `{' '.join(new_cli)}`"
        self.pending_logs.append(Msg(prefix=Level.HINT, message=hint))
        sys.argv = new_cli
        return True


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


if TYPE_CHECKING:
    SubParser: TypeAlias = argparse._SubParsersAction  # noqa: SLF001


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
