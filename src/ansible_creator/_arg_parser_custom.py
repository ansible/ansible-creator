"""Custom argparse formatter and parser used by ``arg_parser``."""

from __future__ import annotations

import argparse
import sys

from argparse import HelpFormatter
from operator import attrgetter
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any


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
