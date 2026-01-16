"""Definitions for ansible-creator schema action."""

from __future__ import annotations

import argparse
import json
import sys

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from ansible_creator.config import Config
    from ansible_creator.output import Output


class Schema:
    """Class to handle the schema subcommand."""

    def __init__(self, config: Config) -> None:
        """Initialize the schema action.

        Args:
            config: App configuration object.
        """
        self.output: Output = config.output
        self._format = getattr(config, "schema_format", "json")

    def run(self) -> None:
        """Generate and output the CLI schema."""
        from ansible_creator.arg_parser import CustomArgumentParser, Parser

        # Build the full parser structure
        main_parser = CustomArgumentParser(
            description="The fastest way to generate all your ansible content.",
        )
        main_parser.add_argument(
            "--version",
            action="version",
            help="Print ansible-creator version and exit.",
            version="source",
        )

        subparser = main_parser.add_subparsers(
            dest="subcommand",
            metavar="command",
            required=True,
        )

        # Use Parser instance to build subparsers
        parser_instance = Parser()
        parser_instance._add(subparser=subparser)  # noqa: SLF001
        parser_instance._init(subparser=subparser)  # noqa: SLF001

        # Extract schema
        schema = self._extract_parser_schema(main_parser, "ansible-creator")

        # Output as JSON
        output = json.dumps(schema, indent=2, default=str)
        sys.stdout.write(output + "\n")

    def _extract_parser_schema(
        self,
        parser: argparse.ArgumentParser,
        name: str,
        help_text: str = "",
    ) -> dict[str, Any]:
        """Recursively extract parser structure as JSON Schema-like format.

        Args:
            parser: The argument parser to extract from.
            name: The name of this command/subcommand.
            help_text: The help text from the parent subparser action.

        Returns:
            Dictionary representing the command schema.
        """
        result: dict[str, Any] = {
            "name": name,
            "description": help_text or parser.description or "",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }

        subcommands: dict[str, Any] = {}

        for action in parser._actions:  # noqa: SLF001
            # Skip help and version actions
            if action.dest in ("help", "version"):
                continue

            # Handle subparsers
            if hasattr(action, "choices") and isinstance(action.choices, dict):
                # Build a map of subparser name -> help text from _choices_actions
                help_map: dict[str, str] = {}
                if hasattr(action, "_choices_actions"):
                    for choice_action in action._choices_actions:
                        help_map[choice_action.dest] = choice_action.help or ""
                
                for sub_name, sub_parser in action.choices.items():
                    sub_help = help_map.get(sub_name, "")
                    subcommands[sub_name] = self._extract_parser_schema(
                        sub_parser,
                        sub_name,
                        sub_help,
                    )
            elif action.dest:
                # Regular argument - skip internal routing params
                if action.dest in (
                    "subcommand",
                    "project",
                    "type",
                    "resource_type",
                    "plugin_type",
                ):
                    continue

                param_info = self._extract_action_info(action)
                result["parameters"]["properties"][action.dest] = param_info

                # Check if required (positional without default or nargs=?)
                if self._is_required(action):
                    result["parameters"]["required"].append(action.dest)

        if subcommands:
            result["subcommands"] = subcommands

        return result

    def _extract_action_info(self, action: argparse.Action) -> dict[str, Any]:
        """Extract parameter info from an argparse action.

        Args:
            action: The argparse action to extract info from.

        Returns:
            Dictionary with parameter type, description, and other metadata.
        """
        info: dict[str, Any] = {
            "description": self._clean_help_text(action.help or ""),
        }

        # Determine type
        if action.choices:
            info["type"] = "string"
            info["enum"] = list(action.choices)
        elif isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
            info["type"] = "boolean"
        elif action.type:
            type_name = getattr(action.type, "__name__", str(action.type))
            if type_name in ("int", "float"):
                info["type"] = type_name
            else:
                info["type"] = "string"
        elif action.nargs in ("+", "*") or (
            isinstance(action.nargs, int) and action.nargs > 1
        ):
            info["type"] = "array"
            info["items"] = {"type": "string"}
        else:
            info["type"] = "string"

        # Add default if present and not suppressed
        if action.default is not None and action.default != argparse.SUPPRESS:
            info["default"] = action.default

        # Add aliases (option strings)
        if action.option_strings:
            info["aliases"] = list(action.option_strings)

        return info

    def _is_required(self, action: argparse.Action) -> bool:
        """Determine if an argument is required.

        Args:
            action: The argparse action to check.

        Returns:
            True if the argument is required.
        """
        # Explicitly marked as required
        if getattr(action, "required", False):
            return True

        # Positional arguments without nargs=? or default are required
        if not action.option_strings:
            if action.nargs not in ("?", "*"):
                if action.default is None or action.default == argparse.SUPPRESS:
                    return True

        return False

    def _get_subparser_help(
        self,
        parser: argparse.ArgumentParser,
        subparser_name: str,
    ) -> str:
        """Get the help text for a subparser by name.

        Args:
            parser: The parent parser.
            subparser_name: The name of the subparser.

        Returns:
            The help text for the subparser, or empty string if not found.
        """
        for action in parser._actions:  # noqa: SLF001
            if hasattr(action, "_choices_actions"):
                for choice_action in action._choices_actions:
                    if choice_action.dest == subparser_name:
                        return choice_action.help or ""
        return ""

    def _clean_help_text(self, help_text: str) -> str:
        """Clean up help text by removing default/choices suffixes added by CustomArgumentParser.

        Args:
            help_text: The raw help text.

        Returns:
            Cleaned help text.
        """
        # Remove " (default: ...)" and " (choices: ...)" suffixes
        import re

        help_text = re.sub(r"\s*\(default:\s*[^)]+\)\s*$", "", help_text)
        help_text = re.sub(r"\s*\(choices:\s*[^)]+\)\s*$", "", help_text)
        return help_text.strip()
