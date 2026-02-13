"""CLI schema introspection for ansible-creator.

Provides functions to extract the full command-tree schema from the
argparse infrastructure.  Used by:

* The ``V1`` API (``schema()`` / ``schema_for()``).
* The ``schema`` CLI subcommand (``ansible-creator schema``).
"""

from __future__ import annotations

import argparse
import re

from typing import Any


def as_dict() -> dict[str, Any]:
    """Return the full CLI schema as a Python dictionary.

    Builds the argparser tree and extracts the schema structure
    including all subcommands, parameters, and metadata.

    Returns:
        Dictionary representing the full command schema.
    """
    from ansible_creator.arg_parser import Parser  # noqa: PLC0415

    main_parser = Parser().build_parser()
    return _extract_parser_schema(main_parser, "ansible-creator")


def for_command(*path: str) -> dict[str, Any]:
    """Return the schema subtree for a specific command path.

    Example: ``for_command("init", "collection")`` returns the schema
    node for ``ansible-creator init collection``.

    Args:
        *path: Sequence of subcommand names to traverse.

    Returns:
        Dictionary representing the schema for the given command path.

    Raises:
        KeyError: If the command path is invalid.
    """
    schema = as_dict()
    node = schema
    for segment in path:
        subcommands = node.get("subcommands", {})
        if segment not in subcommands:
            msg = (
                f"Invalid command path: {' > '.join(path)!r}. "
                f"'{segment}' not found. "
                f"Available: {list(subcommands)}"
            )
            raise KeyError(msg)
        node = subcommands[segment]
    return node


# ---- private helpers --------------------------------------------------------


def _extract_parser_schema(
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
            help_map: dict[str, str] = {}
            for choice_action in action._choices_actions:  # type: ignore[attr-defined]  # noqa: SLF001
                help_map[choice_action.dest] = choice_action.help or ""

            for sub_name, sub_parser in action.choices.items():
                sub_help = help_map.get(sub_name, "")
                subcommands[sub_name] = _extract_parser_schema(
                    sub_parser,
                    sub_name,
                    sub_help,
                )
        else:
            param_info = _extract_action_info(action)
            result["parameters"]["properties"][action.dest] = param_info

            if _is_required(action):
                result["parameters"]["required"].append(action.dest)

    if subcommands:
        result["subcommands"] = subcommands

    return result


def _extract_action_info(action: argparse.Action) -> dict[str, Any]:
    """Extract parameter info from an argparse action.

    Args:
        action: The argparse action to extract info from.

    Returns:
        Dictionary with parameter type, description, and other metadata.
    """
    info: dict[str, Any] = {
        "description": _clean_help_text(action.help or ""),
    }

    # Determine type
    if action.choices:
        info["type"] = "string"
        info["enum"] = list(action.choices)
    elif isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):  # noqa: SLF001
        info["type"] = "boolean"
    elif action.type:
        type_name = getattr(action.type, "__name__", str(action.type))
        if type_name in ("int", "float"):
            info["type"] = type_name
        else:
            info["type"] = "string"
    elif action.nargs in ("+", "*") or (isinstance(action.nargs, int) and action.nargs > 1):
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


def _is_required(action: argparse.Action) -> bool:
    """Determine if an argument is required.

    Args:
        action: The argparse action to check.

    Returns:
        True if the argument is required.
    """
    if getattr(action, "required", False):
        return True

    return bool(
        not action.option_strings
        and action.nargs not in ("?", "*")
        and (action.default is None or action.default == argparse.SUPPRESS)
    )


def _clean_help_text(help_text: str) -> str:
    """Clean up help text by removing default/choices suffixes.

    Removes suffixes added by ``CustomArgumentParser`` such as
    ``(default: ...)`` and ``(choices: ...)``.

    Args:
        help_text: The raw help text.

    Returns:
        Cleaned help text.
    """
    help_text = re.sub(r"\s*\(default:\s*[^)]+\)\s*$", "", help_text)
    help_text = re.sub(r"\s*\(choices:\s*[^)]+\)\s*$", "", help_text)
    return help_text.strip()
