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
        if action.dest in ("help", "version"):
            continue

        if hasattr(action, "choices") and isinstance(action.choices, dict):
            _collect_subcommands(action, subcommands)
        else:
            param_info = _extract_action_info(action)
            result["parameters"]["properties"][action.dest] = param_info
            if _is_required(action):
                result["parameters"]["required"].append(action.dest)

    if subcommands:
        result["subcommands"] = subcommands

    return result


def _collect_subcommands(
    action: argparse.Action,
    subcommands: dict[str, Any],
) -> None:
    help_map: dict[str, str] = {}
    for choice_action in action._choices_actions:  # type: ignore[attr-defined]  # noqa: SLF001
        help_map[choice_action.dest] = choice_action.help or ""

    for sub_name, sub_parser in action.choices.items():  # type: ignore[union-attr]
        sub_help = help_map.get(sub_name, "")
        subcommands[sub_name] = _extract_parser_schema(
            sub_parser,
            sub_name,
            sub_help,
        )


def _extract_action_info(action: argparse.Action) -> dict[str, Any]:
    """Extract parameter info from an argparse action.

    For the ``ee_config`` parameter the returned dict is enriched with
    the full ``EEConfig.to_schema()`` structure so that consumers (e.g.
    the ADT server) know the expected JSON shape.

    If the action carries a ``schema_metadata`` dict attribute, its
    entries (standard JSON Schema validation keywords such as
    ``minLength``, ``pattern``, ``minimum``, ``format``, etc.) are merged
    into the output.

    Args:
        action: The argparse action to extract info from.

    Returns:
        Dictionary with parameter type, description, and other metadata.
    """
    schema_cls = getattr(action, "schema_class", None)
    if schema_cls is not None:
        structured: dict[str, Any] = schema_cls.to_schema()
        structured["description"] = _clean_help_text(action.help or "")
        if action.option_strings:
            structured["aliases"] = list(action.option_strings)
        return structured

    info: dict[str, Any] = {
        "description": _clean_help_text(action.help or ""),
    }

    info.update(_infer_type(action))

    if action.default is not None and action.default != argparse.SUPPRESS:
        info["default"] = action.default

    if action.option_strings:
        info["aliases"] = list(action.option_strings)

    schema_metadata: dict[str, Any] | None = getattr(action, "schema_metadata", None)
    if schema_metadata:
        info.update(schema_metadata)

    return info


def _infer_type(action: argparse.Action) -> dict[str, Any]:
    """Infer JSON Schema type information from an argparse action.

    Args:
        action: The argparse action to inspect.

    Returns:
        Dictionary with ``type`` and optionally ``enum`` or ``items``.
    """
    if action.choices:
        return {"type": "string", "enum": list(action.choices)}

    if isinstance(
        action,
        (
            argparse._StoreTrueAction,  # noqa: SLF001
            argparse._StoreFalseAction,  # noqa: SLF001
            argparse.BooleanOptionalAction,
        ),
    ):
        return {"type": "boolean"}

    if isinstance(action, argparse._CountAction):  # noqa: SLF001
        return {"type": "integer"}

    if action.type:
        type_name = getattr(action.type, "__name__", str(action.type))
        return {"type": type_name if type_name in ("int", "float") else "string"}

    if (
        isinstance(action, argparse._AppendAction)  # noqa: SLF001
        or action.nargs in ("+", "*")
        or (isinstance(action.nargs, int) and action.nargs > 1)
    ):
        return {"type": "array", "items": {"type": "string"}}

    return {"type": "string"}


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
    help_text = re.sub(r" \(default: [^)]+\)$", "", help_text)
    help_text = re.sub(r" \(choices: [^)]+\)$", "", help_text)
    return help_text.strip()
