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
from ansible_creator.output import Level, Output
from ansible_creator.utils import TermFeatures


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
        path: Path to the temporary directory containing scaffolded content,
            or ``None`` when the command failed before any directory was
            created (e.g. invalid command path). The caller is responsible
            for cleanup (e.g. ``shutil.rmtree``) when ``path`` is not
            ``None``.
        logs: Log messages captured during execution.
        message: Summary message on success, or error description on failure.
    """

    status: Literal["success", "error"]
    path: Path | None
    logs: list[str] = field(default_factory=list)
    message: str = ""


class _CapturingOutput(Output):
    """An Output subclass that captures messages instead of printing them.

    Used internally by the V1 API to collect log output from Init/Add
    operations without writing to stdout/stderr or log files.
    """

    def __init__(self, verbosity: int = 0) -> None:
        """Initialize the capturing output.

        Args:
            verbosity: The verbosity level (0=normal, 1=info, 2=debug).
        """
        super().__init__(
            log_file="",
            log_level="notset",
            log_append="true",
            term_features=TermFeatures(color=False, links=False),
            verbosity=verbosity,
        )
        self.messages: list[str] = []

    def log(self, msg: str, level: Level = Level.ERROR) -> None:
        """Capture a log message instead of printing it.

        Respects the same verbosity thresholds as the parent Output class:
        debug messages require verbosity >= 2, info requires >= 1.

        Does NOT increment call_count because the parent's level-specific
        methods (note, debug, info, etc.) already increment before calling
        log(). This avoids double-counting.

        Args:
            msg: The message to capture.
            level: The level of the message.
        """
        debug = 2
        info = 1
        if (self._verbosity < debug and level == Level.DEBUG) or (
            self._verbosity < info and level == Level.INFO
        ):
            return

        self.messages.append(f"{level.value}: {msg}")

    def critical(self, msg: str) -> None:
        """Capture a critical message without calling sys.exit.

        The parent ``Output.critical`` calls ``sys.exit(1)``. This override
        captures the message instead of exiting.

        Args:
            msg: The message to capture.
        """
        self.call_count["critical"] += 1
        self.messages.append(f"{Level.CRITICAL.value}: {msg}")


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
        from ansible_creator.subcommands.schema import Schema  # noqa: PLC0415

        return Schema.as_dict()

    def schema_for(self, *path: str) -> dict[str, Any]:
        """Return the schema for a specific command path.

        Note: raises ``KeyError`` if the command path is invalid.

        Args:
            *path: Subcommand segments, e.g. ``("init", "collection")``.

        Returns:
            Dictionary representing the schema for the given command.
        """
        from ansible_creator.subcommands.schema import Schema  # noqa: PLC0415

        return Schema.for_command(*path)

    def run(self, *command_path: str, **kwargs: Any) -> CreatorResult:  # noqa: ANN401
        """Execute an ansible-creator command dynamically.

        Walks the argparser tree following the command path, merges the
        provided kwargs with parser defaults, scaffolds into a temporary
        directory, and returns a structured result.

        Args:
            *command_path: The command segments, e.g.
                ``("init", "collection")`` or
                ``("add", "resource", "devfile")``.
            **kwargs: Parameters for the command (e.g. ``collection="ns.name"``).

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

        output = _CapturingOutput(verbosity=self.verbosity)

        # Resolve and validate the command before creating a temp directory
        try:
            config_args = self._resolve_command(command_path, kwargs, output)
        except (KeyError, TypeError) as exc:
            return CreatorResult(
                status="error",
                path=None,
                logs=output.messages,
                message=str(exc),
            )

        tmp_dir = Path(tempfile.mkdtemp(prefix="ansible-creator-"))

        # Apply temp dir as the output path if the caller didn't provide one
        subcommand = command_path[0]
        if subcommand == "init" and "init_path" not in kwargs:
            config_args["init_path"] = str(tmp_dir)
        if subcommand == "add" and "path" not in kwargs:
            config_args["path"] = str(tmp_dir)

        try:
            subcommand_module = f"ansible_creator.subcommands.{subcommand}"
            subcommand_cls = subcommand.capitalize()

            cls = getattr(import_module(subcommand_module), subcommand_cls)
            config = Config(**config_args)
            cls(config=config).run()

            # Extract the last note as the summary message
            message = ""
            for msg in reversed(output.messages):
                if msg.startswith("Note:"):
                    message = msg.removeprefix("Note:").strip()
                    break

        except (CreatorError, KeyError, TypeError) as exc:
            return CreatorResult(
                status="error",
                path=tmp_dir,
                logs=output.messages,
                message=str(exc),
            )

        return CreatorResult(
            status="success",
            path=tmp_dir,
            logs=output.messages,
            message=message,
        )

    @staticmethod
    def _resolve_command(
        command_path: tuple[str, ...],
        kwargs: dict[str, Any],
        output: _CapturingOutput,
    ) -> dict[str, Any]:
        """Resolve a command path to a Config-compatible argument dictionary.

        Walks the argparser tree following the command path, collecting
        routing values (subcommand, project, type, etc.) and parameter
        defaults from each level. Merges with caller-provided kwargs.

        Args:
            command_path: The command segments to traverse.
            kwargs: Caller-provided parameters to override defaults.
            output: The capturing output instance.

        Returns:
            Dictionary suitable for passing to ``Config(**result)``.

        Raises:
            KeyError: If a segment in the command path is not found.
        """
        from ansible_creator.arg_parser import CustomArgumentParser, Parser  # noqa: PLC0415

        # Build the full parser tree
        main_parser = CustomArgumentParser(
            description="The fastest way to generate all your ansible content.",
        )
        main_parser.add_argument(
            "--version",
            action="version",
            help="Print ansible-creator version and exit.",
            version="source",
        )

        subparser_action = main_parser.add_subparsers(
            dest="subcommand",
            metavar="command",
            required=True,
        )

        parser_instance = Parser()
        parser_instance._add(subparser=subparser_action)  # type: ignore[arg-type]  # noqa: SLF001
        parser_instance._init(subparser=subparser_action)  # type: ignore[arg-type]  # noqa: SLF001
        parser_instance._schema(subparser=subparser_action)  # type: ignore[arg-type]  # noqa: SLF001

        # Walk the parser tree following the command path
        current_parser = main_parser
        routing: dict[str, str] = {}

        for segment in command_path:
            found = False
            for action in current_parser._actions:  # noqa: SLF001
                if (
                    hasattr(action, "choices")
                    and isinstance(action.choices, dict)
                    and segment in action.choices
                ):
                    routing[action.dest] = segment
                    current_parser = action.choices[segment]
                    found = True
                    break
            if not found:
                available = V1._get_subparser_choices(current_parser)
                msg = f"Invalid command path segment: '{segment}'. Available: {available}"
                raise KeyError(msg)

        # Collect defaults from the leaf parser
        defaults = V1._collect_defaults(current_parser)

        # Merge: defaults < routing < caller kwargs < api-managed values
        merged = {**defaults, **routing, **kwargs}

        # Set API-managed values
        merged["creator_version"] = __version__
        merged["output"] = output

        subcommand = command_path[0]
        if subcommand == "add":
            # Skip collection path validation for API usage since the
            # target may be a bare temp directory without galaxy.yml.
            merged.setdefault("skip_collection_check", True)

        # Ensure required Config fields have values
        merged.setdefault("subcommand", subcommand)

        # Filter to only include keys that Config accepts.
        # The argparser tree includes CLI-only options (e.g. no_ansi,
        # json, verbose, log_file) that are not Config fields.
        return {k: v for k, v in merged.items() if k in _CONFIG_FIELDS}

    @staticmethod
    def _get_subparser_choices(parser: argparse.ArgumentParser) -> list[str]:
        """Get available subparser choices for a parser.

        Args:
            parser: The parser to inspect.

        Returns:
            List of available subcommand names.
        """
        choices: list[str] = []
        for action in parser._actions:  # noqa: SLF001
            if hasattr(action, "choices") and isinstance(action.choices, dict):
                choices.extend(action.choices.keys())
        return choices

    @staticmethod
    def _collect_defaults(parser: argparse.ArgumentParser) -> dict[str, Any]:
        """Collect default values from a parser's actions.

        Args:
            parser: The parser to collect defaults from.

        Returns:
            Dictionary of dest -> default for all actions with defaults.
        """
        defaults: dict[str, Any] = {}
        for action in parser._actions:  # noqa: SLF001
            if action.dest in ("help", "version"):
                continue
            if action.default is not None and action.default != argparse.SUPPRESS:
                defaults[action.dest] = action.default
        return defaults
