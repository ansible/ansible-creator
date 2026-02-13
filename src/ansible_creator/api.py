"""Public programmatic API for ansible-creator.

This module provides a stable Python API for Ansible ecosystem tooling
(ansible-dev-tools server, VS Code extension, MCP servers). It is intended
for **internal use** within the Ansible tooling ecosystem, not as a public
contract for end users.

Example usage::

    from ansible_creator.api import V1

    api = V1(verbosity=1)

    # Discover capabilities
    tree = api.schema()
    params = api.schema_for("init", "collection")

    # Scaffold dynamically
    result = api.run("init", "collection", collection="testns.testcol")
    result = api.run("add", "resource", "devfile")
    result = api.run("add", "plugin", "filter", plugin_name="my_filter")

    # Inspect result
    print(result.status, result.path, result.logs)
"""

from __future__ import annotations

import argparse
import tempfile

from dataclasses import dataclass, field, fields
from importlib import import_module
from pathlib import Path
from typing import Any, Literal

from ansible_creator.config import Config
from ansible_creator.exceptions import CreatorError
from ansible_creator.output import Output
from ansible_creator.utils import TermFeatures, expand_path


# Set of valid Config field names, used to filter argparser defaults
_CONFIG_FIELDS = {f.name for f in fields(Config)}

try:
    from ansible_creator._version import (
        version as __version__,  # type: ignore[unused-ignore,import-not-found]
    )
except ImportError:  # pragma: no cover
    __version__ = "source"


@dataclass
class CreatorResult:
    """Result of an ansible-creator API operation.

    Attributes:
        status: Whether the operation succeeded or failed.
        path: The directory where content was scaffolded, or ``None`` when
            the command failed before any output was produced. When the
            caller provides an explicit ``init_path`` or ``path`` kwarg,
            ``result.path`` points to that directory.  When no explicit path
            is given, a temporary directory is created and returned here;
            the caller is responsible for cleanup (e.g. ``shutil.rmtree``).
        logs: Log messages captured during execution.
        message: Summary message on success, or error description on failure.
    """

    status: Literal["success", "error"]
    path: Path | None
    logs: list[str] = field(default_factory=list)
    message: str = ""


class V1:
    """Dynamic, schema-driven API for ansible-creator (version 1).

    This API uses the argparser infrastructure to discover available
    commands and parameters at runtime. When new subcommands or resource
    types are added to ansible-creator, they are automatically available
    through this API with no code changes.
    """

    def __init__(self, verbosity: int = 0) -> None:
        """Initialize the V1 API.

        Args:
            verbosity: The verbosity level for captured logs.
        """
        self.verbosity = verbosity

    def schema(self) -> dict[str, Any]:
        """Return the full CLI capability schema as a dictionary.

        The schema describes all available subcommands, their parameters,
        types, defaults, and descriptions.

        Returns:
            Dictionary representing the full command tree.
        """
        from ansible_creator.schema import as_dict  # noqa: PLC0415

        return as_dict()

    def schema_for(self, *path: str) -> dict[str, Any]:
        """Return the schema for a specific command path.

        Note: raises ``KeyError`` if the command path is invalid.

        Args:
            *path: Subcommand segments, e.g. ``("init", "collection")``.

        Returns:
            Dictionary representing the schema for the given command.
        """
        from ansible_creator.schema import for_command  # noqa: PLC0415

        return for_command(*path)

    def build_command(self, *command_path: str, **kwargs: Any) -> list[str]:  # noqa: ANN401
        """Return the CLI argv that would be constructed for the given command.

        Useful for testing and debugging -- see exactly what the API would
        feed to argparse without actually running anything.

        Args:
            *command_path: The command segments, e.g. ``("init", "collection")``.
            **kwargs: Parameters for the command.

        Returns:
            List of argv strings (e.g. ``["init", "collection", "ns.col"]``).
        """
        _, argv = self._build_argv(command_path, kwargs)
        return argv

    def run(self, *command_path: str, **kwargs: Any) -> CreatorResult:  # noqa: C901,ANN401
        """Execute an ansible-creator command dynamically.

        Constructs an argv list from the command path and kwargs, feeds it
        to the real argparser, then dispatches the subcommand -- mirroring
        the CLI flow exactly.

        Args:
            *command_path: The command segments, e.g.
                ``("init", "collection")`` or
                ``("add", "resource", "devfile")``.
            **kwargs: Parameters for the command (e.g. ``collection="ns.name"``).
                Supports both Config parameters and Output parameters
                (``log_file``, ``log_level``, ``log_append``, ``verbose``).

        Returns:
            CreatorResult with status, path to scaffolded content, logs,
            and a summary message.
        """
        if not command_path:
            return CreatorResult(
                status="error",
                path=None,
                message="No command path provided.",
            )

        # Build the parser (same as CLI) and resolve argv
        try:
            parser, argv = self._build_argv(command_path, kwargs)
        except TypeError as exc:
            return CreatorResult(
                status="error",
                path=None,
                message=str(exc),
            )

        # Parse through the real argparser -- catches all validation
        try:
            namespace = parser.parse_args(argv)
        except SystemExit:
            return CreatorResult(
                status="error",
                path=None,
                message=f"Invalid arguments for command: {' '.join(command_path)}",
            )

        args = vars(namespace)
        output, messages = self._build_output(args, kwargs)

        # Determine the output path -- only init/add need a workspace dir
        subcommand = command_path[0]
        needs_workspace = subcommand in ("init", "add")
        output_dir: Path | None = None

        if needs_workspace:
            explicit_path = self._get_explicit_path(subcommand, kwargs)
            if explicit_path is not None:
                output_dir = Path(explicit_path)
            else:
                output_dir = Path(tempfile.mkdtemp(prefix="ansible-creator-"))

            # Point the config at the actual output directory -- the
            # leaf parser may not have the path argument so argparse can miss it.
            if subcommand == "init":
                args["init_path"] = str(output_dir)
            else:
                args["path"] = str(output_dir)

            # For add commands targeting a bare directory, skip collection check
            if subcommand == "add":
                args.setdefault("skip_collection_check", True)

        # Build Config from the remaining args (same as Cli.run)
        args["creator_version"] = __version__
        args["output"] = output
        config_args = {k: v for k, v in args.items() if k in _CONFIG_FIELDS}

        try:
            subcommand_module = f"ansible_creator.subcommands.{subcommand}"
            subcommand_cls = subcommand.capitalize()

            cls = getattr(import_module(subcommand_module), subcommand_cls)
            config = Config(**config_args)
            cls(config=config).run()

            # Extract the last note as the summary message
            message = ""
            for msg in reversed(messages):
                if msg.startswith("Note:"):
                    message = msg.removeprefix("Note:").strip()
                    break

        except CreatorError as exc:
            return CreatorResult(
                status="error",
                path=output_dir,
                logs=messages,
                message=str(exc),
            )

        return CreatorResult(
            status="success",
            path=output_dir,
            logs=messages,
            message=message,
        )

    def _build_output(
        self,
        args: dict[str, Any],
        kwargs: dict[str, Any],
    ) -> tuple[Output, list[str]]:
        """Construct an ``Output`` instance from parsed argparse values.

        Pops output-related keys from *args* (mirrors ``Cli.init_output``)
        and returns the ``Output`` together with the captured-messages list
        that the caller can inspect after the subcommand has run.

        Args:
            args: Mutable dict of parsed arguments (output keys are popped).
            kwargs: Original caller kwargs -- used to detect whether
                ``verbose`` was explicitly provided.

        Returns:
            Tuple of (Output instance, captured messages list).
        """
        messages: list[str] = []
        effective_verbosity = (
            args.pop("verbose", self.verbosity) if "verbose" in kwargs else self.verbosity
        )
        args.pop("verbose", None)

        output = Output(
            log_file=str(
                expand_path(args.pop("log_file", "./ansible-creator.log")),
            ),
            log_level=args.pop("log_level", "notset"),
            log_append=args.pop("log_append", "true"),
            term_features=TermFeatures(color=False, links=False),
            verbosity=effective_verbosity,
            display="json" if args.pop("json", False) else "text",
            captured_messages=messages,
        )
        args.pop("no_ansi", None)

        return output, messages

    def _build_argv(
        self,
        command_path: tuple[str, ...],
        kwargs: dict[str, Any],
    ) -> tuple[argparse.ArgumentParser, list[str]]:
        """Build an argparser and an argv list from the command path and kwargs.

        Walks the parser tree to identify positional vs optional arguments
        at the leaf level, then constructs the correct argv ordering.

        Args:
            command_path: The command segments to traverse.
            kwargs: Caller-provided parameters.

        Returns:
            Tuple of (parser, argv list).

        Raises:
            TypeError: If kwargs contain routing keys or unknown parameters.
        """
        from ansible_creator.arg_parser import Parser  # noqa: PLC0415

        main_parser = Parser().build_parser()

        leaf, routing = self._walk_to_leaf(main_parser, command_path, kwargs)

        # Classify leaf parser actions into positional and optional
        positionals: list[argparse.Action] = []
        optionals: dict[str, argparse.Action] = {}
        for action in leaf._actions:  # noqa: SLF001
            if action.dest in ("help", "version"):
                continue
            if action.option_strings:
                optionals[action.dest] = action
            else:
                positionals.append(action)

        # Build argv: command_path + positional args + optional flags
        argv: list[str] = list(command_path)

        # Positional args (in parser order)
        pos_names = {a.dest for a in positionals}
        argv.extend(str(kwargs[a.dest]) for a in positionals if a.dest in kwargs)

        # Optional/flag args
        matched = pos_names | set(routing)
        for dest, value in kwargs.items():
            if dest in pos_names or dest in routing:
                continue

            opt_action = optionals.get(dest)
            if opt_action is None:
                continue

            matched.add(dest)
            argv.extend(self._action_to_argv(opt_action, value))

        # Reject kwargs that don't match any positional, routing, or optional
        unmatched = set(kwargs) - matched
        if unmatched:
            msg = f"Unknown parameters for command '{' '.join(command_path)}': {sorted(unmatched)}"
            raise TypeError(msg)

        return main_parser, argv

    @staticmethod
    def _action_to_argv(action: argparse.Action, value: Any) -> list[str]:  # noqa: ANN401
        """Convert a single optional action and value into argv tokens.

        Args:
            action: The argparse action for this option.
            value: The caller-provided value.

        Returns:
            List of argv tokens (may be empty for false boolean flags).
        """
        flag = action.option_strings[0]
        if isinstance(action, argparse._StoreTrueAction):  # noqa: SLF001
            return [flag] if value else []
        if isinstance(action, argparse._CountAction):  # noqa: SLF001
            return [flag] * int(value)
        return [flag, str(value)]

    @staticmethod
    def _walk_to_leaf(
        parser: argparse.ArgumentParser,
        command_path: tuple[str, ...],
        kwargs: dict[str, Any],
    ) -> tuple[argparse.ArgumentParser, dict[str, str]]:
        """Walk the parser tree to the leaf subparser for *command_path*.

        Also validates that *kwargs* do not contain routing keys that are
        implicitly derived from the command path (e.g. ``subcommand``,
        ``project``, ``type``).

        Args:
            parser: The root argument parser.
            command_path: The command segments to traverse.
            kwargs: Caller-provided parameters (checked for conflicts).

        Returns:
            Tuple of (leaf parser, routing dict mapping dest -> segment).

        Raises:
            TypeError: If kwargs contain routing keys derived from the path.
        """
        current = parser
        routing: dict[str, str] = {}

        for segment in command_path:
            found = False
            for action in current._actions:  # noqa: SLF001
                if (
                    hasattr(action, "choices")
                    and isinstance(action.choices, dict)
                    and segment in action.choices
                ):
                    routing[action.dest] = segment
                    current = action.choices[segment]
                    found = True
                    break
            if not found:
                break

        conflicts = set(kwargs) & set(routing)
        if conflicts:
            msg = f"Cannot override routing keys derived from the command path: {sorted(conflicts)}"
            raise TypeError(msg)

        return current, routing

    @staticmethod
    def _get_explicit_path(
        subcommand: str,
        kwargs: dict[str, Any],
    ) -> str | None:
        """Return the caller-provided output path, if any.

        Args:
            subcommand: The top-level subcommand name.
            kwargs: The original caller kwargs.

        Returns:
            The explicit path string, or None if the caller didn't provide one.
        """
        if subcommand == "init" and "init_path" in kwargs:
            return str(kwargs["init_path"])
        if subcommand == "add" and "path" in kwargs:
            return str(kwargs["path"])
        return None
