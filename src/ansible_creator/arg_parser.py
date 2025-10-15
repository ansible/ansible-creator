"""Parse the command line arguments."""

from __future__ import annotations

import argparse
import os
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
MAX_COLLECTION_NAME_LEN = 64


if TYPE_CHECKING:
    SubParser: TypeAlias = argparse._SubParsersAction  # noqa: SLF001


class CustomHelpFormatter(HelpFormatter):  # pragma: no cover py>=3.14
    """A custom help formatter."""

    def __init__(self, prog: str) -> None:
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
        self,
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
        if not action.option_strings:  # pragma: no branch
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


class Parser:
    """A parser for the command line arguments."""

    def __init__(self) -> None:
        """Initialize the parser."""
        self.args: argparse.Namespace
        self.pending_logs: list[Msg] = []
        self.init_parser: argparse.ArgumentParser | None = None
        self.add_parser: argparse.ArgumentParser | None = None
        self.add_resource_parser: argparse.ArgumentParser | None = None
        self.add_plugin_parser: argparse.ArgumentParser | None = None
        self.exit_code: int = 0

    def parse_args(self) -> tuple[argparse.Namespace, list[Msg], int]:
        """Parse the root arguments.

        Returns:
            The parsed arguments, any pending logs, and exit code
            (0 for success, os.EX_USAGE for usage error)
        """
        is_init = sys.argv[1:2] == ["init"]
        not_empty = sys.argv[2:] != []
        not_help = not any(arg in sys.argv for arg in ["-h", "--help"])
        if all((is_init, not_empty, not_help)):
            proceed = self.handle_deprecations()
            if not proceed:
                return argparse.Namespace(), self.pending_logs, 1

        parser = CustomArgumentParser(
            description="The fastest way to generate all your ansible content.",
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
        self._add(subparser=subparser)  # type: ignore[arg-type]
        self._init(subparser=subparser)  # type: ignore[arg-type]

        if HAS_ARGCOMPLETE:  # pragma: no cover
            argcomplete.autocomplete(parser)
        self.args = parser.parse_args()

        # Show help for 'ansible-creator init' without arguments
        if self.args.subcommand == "init" and self.args.project is None and self.init_parser:
            self.init_parser.print_help(sys.stderr)
            self.pending_logs.append(
                Msg(
                    prefix=Level.ERROR,
                    message="Missing required argument 'project-type'.\n"
                    "Choose from: collection, playbook, execution_env",
                )
            )
            self.exit_code = os.EX_USAGE

        # Show help for 'ansible-creator add' without arguments
        if self.args.subcommand == "add" and self.args.type is None and self.add_parser:
            self.add_parser.print_help(sys.stderr)
            self.pending_logs.append(
                Msg(
                    prefix=Level.ERROR,
                    message="Missing required argument 'content-type'.\n"
                    "Choose from: resource, plugin",
                )
            )
            self.exit_code = os.EX_USAGE

        # Show help for 'ansible-creator add resource' without arguments
        if (
            self.args.subcommand == "add"
            and self.args.type == "resource"
            and self.args.resource_type is None
        ) and self.add_resource_parser:
            self.add_resource_parser.print_help(sys.stderr)
            self.pending_logs.append(
                Msg(
                    prefix=Level.ERROR,
                    message="Missing required argument 'resource-type'.\n"
                    "Choose from: devcontainer, devfile, execution-environment, "
                    "play-argspec, role",
                )
            )
            self.exit_code = os.EX_USAGE

        # Show help for 'ansible-creator add plugin' without arguments
        if (
            self.args.subcommand == "add"
            and self.args.type == "plugin"
            and self.args.plugin_type is None
            and self.add_plugin_parser
        ):
            self.add_plugin_parser.print_help(sys.stderr)
            self.pending_logs.append(
                Msg(
                    prefix=Level.ERROR,
                    message="Missing required argument 'plugin-type'.\n"
                    "Choose from: action, filter, lookup, module, test",
                )
            )
            self.exit_code = os.EX_USAGE

        return self.args, self.pending_logs, self.exit_code

    def _add(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add resources to an existing Ansible project.

        Args:
            subparser: The subparser to add the resources to
        """
        parser = subparser.add_parser(
            "add",
            help="Add resources to an existing Ansible project.",
        )
        self.add_parser = parser
        subparser = parser.add_subparsers(
            dest="type",
            required=False,
            metavar="content-type",
        )
        self._add_resource(subparser=subparser)
        self._add_plugin(subparser=subparser)

    def _add_args_common(self, parser: argparse.ArgumentParser) -> None:
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

    def _add_args_init_common(self, parser: argparse.ArgumentParser) -> None:
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
            help=(
                "Force re-initialize the specified directory. "
                "This flag is deprecated and will be removed soon."
            ),
        )
        self._add_overwrite(parser)

    def _add_args_plugin_common(self, parser: argparse.ArgumentParser) -> None:
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
            nargs="?",
            help="The path to the Ansible collection. The default is the "
            "current working directory.",
        )

    def _add_resource(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add resources to an existing Ansible project.

        Args:
            subparser: The subparser to add resource to
        """
        parser = subparser.add_parser(
            "resource",
            help="Add resources to an existing Ansible project.",
        )
        self.add_resource_parser = parser
        subparser = parser.add_subparsers(
            dest="resource_type",
            metavar="resource-type",
            required=False,
        )
        # keep arguments order sorted alphabetically to ease reading
        self._add_resource_ai(subparser=subparser)
        self._add_resource_devcontainer(subparser=subparser)
        self._add_resource_devfile(subparser=subparser)
        self._add_resource_execution_env(subparser=subparser)
        self._add_resource_play_argspec(subparser=subparser)
        self._add_resource_role(subparser=subparser)

    def _add_resource_ai(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add AI files to an existing Ansible project.

        Args:
            subparser: The subparser to add files to
        """
        parser = subparser.add_parser(
            "ai",
            help="Add AI agent helper files.",
        )
        self._add_args_common(parser)

    def _add_resource_devcontainer(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add devcontainer files to an existing Ansible project.

        Args:
            subparser: The subparser to add devcontainer files to
        """
        parser = subparser.add_parser(
            "devcontainer",
            help="Add devcontainer files to an existing Ansible project.",
        )

        parser.add_argument(
            "path",
            default="./",
            metavar="path",
            nargs="?",
            help="The destination directory for the devcontainer files. The default is the "
            "current working directory.",
        )

        parser.add_argument(
            "-i",
            "--image",
            default="auto",
            dest="image",
            required=False,
            help="Image with which devcontainer needs to be scaffolded",
        )

        self._add_overwrite(parser)
        self._add_args_common(parser)

    def _add_resource_devfile(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add a devfile file to an existing Ansible project.

        Args:
            subparser: The subparser to add devfile file to
        """
        parser = subparser.add_parser(
            "devfile",
            help="Add a devfile file to an existing Ansible project.",
        )
        parser.add_argument(
            "path",
            default="./",
            metavar="path",
            nargs="?",
            help="The destination directory for the devfile file. The default is the "
            "current working directory.",
        )

        self._add_overwrite(parser)
        self._add_args_common(parser)

    def _add_resource_execution_env(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add execution environment sample file to an existing path.

        Args:
            subparser: The subparser to add execution environment file to
        """
        parser = subparser.add_parser(
            "execution-environment",
            help="Add a sample execution-environment.yml file to an existing path.",
        )

        parser.add_argument(
            "path",
            default="./",
            metavar="path",
            nargs="?",
            help="The destination directory for the execution environment file. "
            "The default is the current working directory.",
        )

        self._add_overwrite(parser)
        self._add_args_common(parser)

    def _add_resource_play_argspec(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add example playbook argspec files to an existing Ansible project.

        Args:
            subparser: The subparser to add playbook argspec files to
        """
        parser = subparser.add_parser(
            "play-argspec",
            help="Add example playbook argspec files to an existing Ansible project.",
        )

        parser.add_argument(
            "path",
            default="./",
            metavar="path",
            nargs="?",
            help="The destination directory for the playbook argspec files. The default is the "
            "current working directory.",
        )

        self._add_overwrite(parser)
        self._add_args_common(parser)

    def _add_resource_role(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add a role to an existing Ansible collection.

        Args:
            subparser: The subparser to add role to
        """
        parser = subparser.add_parser(
            "role",
            help="Add a role to an existing Ansible collection.",
        )
        parser.add_argument(
            "role_name",
            help="The name of the role to add.",
        )
        parser.add_argument(
            "path",
            default="./",
            metavar="path",
            nargs="?",
            help="The path to the Ansible collection. The default is the "
            "current working directory.",
        )

        self._add_overwrite(parser)
        self._add_args_common(parser)

    def _add_plugin(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add a plugin to an Ansible project.

        Args:
            subparser: The subparser to add plugin to
        """
        parser = subparser.add_parser(
            "plugin",
            help="Add a plugin to an Ansible collection.",
        )
        self.add_plugin_parser = parser
        subparser = parser.add_subparsers(
            dest="plugin_type",
            metavar="plugin-type",
            required=False,
        )

        self._add_plugin_action(subparser=subparser)
        self._add_plugin_filter(subparser=subparser)
        self._add_plugin_lookup(subparser=subparser)
        self._add_plugin_module(subparser=subparser)
        self._add_plugin_test(subparser=subparser)

    def _add_plugin_action(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add an action plugin to an existing Ansible collection project.

        Args:
            subparser: The subparser to add action plugin to
        """
        parser = subparser.add_parser(
            "action",
            help="Add an action plugin to an existing Ansible collection.",
        )
        self._add_args_common(parser)
        self._add_overwrite(parser)
        self._add_args_plugin_common(parser)

    def _add_plugin_filter(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add a filter plugin to an existing Ansible collection project.

        Args:
            subparser: The subparser to add filter plugin to
        """
        parser = subparser.add_parser(
            "filter",
            help="Add a filter plugin to an existing Ansible collection.",
        )
        self._add_args_common(parser)
        self._add_overwrite(parser)
        self._add_args_plugin_common(parser)

    def _add_plugin_lookup(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add a lookup plugin to an existing Ansible collection project.

        Args:
            subparser: The subparser to add lookup plugin to
        """
        parser = subparser.add_parser(
            "lookup",
            help="Add a lookup plugin to an existing Ansible collection.",
        )
        self._add_args_common(parser)
        self._add_overwrite(parser)
        self._add_args_plugin_common(parser)

    def _add_plugin_module(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add a module plugin to an existing Ansible collection project.

        Args:
            subparser: The subparser to add module plugin to
        """
        parser = subparser.add_parser(
            "module",
            help="Add a module plugin to an existing Ansible collection.",
        )
        self._add_args_common(parser)
        self._add_overwrite(parser)
        self._add_args_plugin_common(parser)

    def _add_plugin_test(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Add a test plugin to an existing Ansible collection project.

        Args:
            subparser: The subparser to add test plugin to
        """
        parser = subparser.add_parser(
            "test",
            help="Add a test plugin to an existing Ansible collection.",
        )
        self._add_args_common(parser)
        self._add_overwrite(parser)
        self._add_args_plugin_common(parser)

    def _add_overwrite(self, parser: argparse.ArgumentParser) -> None:
        """Add overwrite and no-overwrite arguments to the parser.

        Args:
            parser: The parser to add overwrite and no_overwrite options
        """
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

    def _init(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Initialize an Ansible project.

        Args:
            subparser: The subparser add init to
        """
        parser = subparser.add_parser(
            "init",
            help="Initialize a new Ansible project.",
        )
        self.init_parser = parser
        subparser = parser.add_subparsers(
            dest="project",
            metavar="project-type",
            required=False,
        )

        self._init_collection(subparser=subparser)
        self._init_playbook(subparser=subparser)
        self._init_ee_project(subparser=subparser)

    def _init_collection(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Initialize an Ansible collection.

        Args:
            subparser: The subparser to add collection to
        """
        parser = subparser.add_parser(
            "collection",
            help="Create a new Ansible collection project.",
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

    def _init_playbook(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Initialize an Ansible playbook.

        Args:
            subparser: The subparser to add playbook to
        """
        parser = subparser.add_parser(
            "playbook",
            help="Create a new Ansible playbook project.",
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

    def _init_ee_project(self, subparser: SubParser[argparse.ArgumentParser]) -> None:
        """Initialize an EE project.

        Args:
            subparser: The subparser to add EE project to
        """
        parser = subparser.add_parser(
            "execution_env",
            help="Create a new execution environment project.",
        )
        parser.add_argument(
            "init_path",
            metavar="path",
            nargs="?",
            help="The destination directory for the EE project.",
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

    def handle_deprecations(self) -> bool:  # noqa: C901
        """Start parsing args passed from Cli.

        Returns:
            True if parsing can proceed, False otherwise
        """
        parser = CustomArgumentParser()
        parser.add_argument("command", help="")
        parser.add_argument("collection", nargs="?", help="")
        parser.add_argument("--project", help="")
        parser.add_argument("--scm-org", help="")
        parser.add_argument("--scm-project", help="")
        parser.add_argument("--init-path", help="")
        args, extras = parser.parse_known_args()

        if args.collection in {"playbook", "collection", "execution_env"}:
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


class CustomArgumentParser(argparse.ArgumentParser):
    """A custom argument parser."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize the argument parser.

        Args:
            *args: The arguments
            **kwargs: The keyword arguments
        """
        super().__init__(*args, **kwargs)
        if sys.version_info < (3, 14):  # pragma: no cover py>=3.14
            self.formatter_class = CustomHelpFormatter

    def add_argument(  # type: ignore[override]
        self,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Add an argument.

        Args:
            *args: The arguments
            **kwargs: The keyword arguments
        """
        if sys.version_info < (3, 14):  # pragma: no cover py>=3.14
            if "choices" in kwargs:  # pragma: no cover py>=3.14
                kwargs["help"] += f" (choices: {', '.join(kwargs['choices'])})"
            if "default" in kwargs and kwargs["default"] != "==SUPPRESS==":
                kwargs["help"] += f" (default: {kwargs['default']})"
        super().add_argument(*args, **kwargs)

    def add_argument_group(
        self,
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
        if group.title:  # pragma: no cover
            group.title = group.title.capitalize()
        return group
