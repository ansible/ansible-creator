"""Output functionality."""

from __future__ import annotations

import decimal
import json
import logging
import os
import shutil
import sys
import textwrap

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar


if TYPE_CHECKING:
    from .utils import TermFeatures


T = TypeVar("T", bound="Level")
GOLDEN_RATIO = 1.61803398875


def round_half_up(number: float) -> int:
    """Round a number to the nearest integer with ties going away from zero.

    This is different the round() where exact halfway cases are rounded to the nearest
    even result instead of away from zero. (e.g. round(2.5) = 2, round(3.5) = 4).

    This will always round based on distance from zero. (e.g round(2.5) = 3, round(3.5) = 4).

    Args:
        number: The number to round
    Returns:
        The rounded number as an int
    """
    rounded = decimal.Decimal(number).quantize(
        decimal.Decimal("1"),
        rounding=decimal.ROUND_HALF_UP,
    )
    return int(rounded)


def console_width() -> int:
    """Get a console width based on common screen widths.

    Returns:
        The console width
    """
    columns = int(os.environ.get("COLUMNS", "0"))
    if columns:
        return columns
    medium = 80
    wide = 132
    width = shutil.get_terminal_size().columns
    if width <= medium:
        return width
    if width <= wide:
        return max(80, round_half_up(width / GOLDEN_RATIO))
    return wide


class Color:
    """Color constants.

    Attributes:
        BLACK: Black color
        RED: Red color
        GREEN: Green color
        YELLOW: Yellow color
        BLUE: Blue color
        MAGENTA: Magenta color
        CYAN: Cyan color
        WHITE: White color
        GREY: Bright black color
        BRIGHT_RED: Bright red color
        BRIGHT_GREEN: Bright green color
        BRIGHT_YELLOW: Bright yellow color
        BRIGHT_BLUE: Bright blue color
        BRIGHT_MAGENTA: Bright magenta color
        BRIGHT_CYAN: Bright cyan color
        BRIGHT_WHITE: Bright white color
        END: End
    """

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GREY = "\033[90m"  # Bright black?
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    END = "\033[0m"


class Level(Enum):
    """An exit message prefix.

    Attributes:
        CRITICAL: Critical
        DEBUG: Debug
        ERROR: Error
        HINT: Hint
        INFO: Info
        NOTE: Note
        WARNING: Warning
    """

    CRITICAL = "Critical"
    DEBUG = "Debug"
    ERROR = "Error"
    HINT = "Hint"
    INFO = "Info"
    NOTE = "Note"
    WARNING = "Warning"

    @property
    def log_level(self: Level) -> int:
        """Return a log level.

        :returns: The log level
        """
        mapping = {
            Level.CRITICAL: logging.CRITICAL,
            Level.DEBUG: logging.DEBUG,
            Level.ERROR: logging.ERROR,
            Level.HINT: logging.INFO,
            Level.INFO: logging.INFO,
            Level.NOTE: logging.INFO,
            Level.WARNING: logging.WARNING,
        }
        return mapping[self]

    @classmethod
    def _longest_name(cls) -> int:
        """Return the longest exit message prefix.

        Returns:
            The longest exit message prefix
        """
        return max(len(member.value) for member in cls)

    @classmethod
    def longest_formatted(cls) -> int:
        """Return the longest exit message prefix.

        Returns:
            The longest exit message prefix
        """
        return max(len(str(member)) for member in cls)

    def __str__(self: Level) -> str:
        """Return the exit message prefix as a string.

        Returns:
            The exit message prefix as a string
        """
        return f"{' ' * (self._longest_name() - len(self.name))}{self.name.capitalize()}: "


@dataclass
class Msg:
    """An object to hold a message to present when exiting.

    Attributes:
        message: The message that will be presented
        prefix: The prefix for the message, used for formatting
    """

    message: str
    prefix: Level = Level.ERROR

    @property
    def color(self: Msg) -> str:
        """Return a color for the prefix.

        :returns: The color for the prefix
        """
        color_mapping = {
            Level.CRITICAL: Color.BRIGHT_RED,
            Level.DEBUG: Color.GREY,
            Level.ERROR: Color.RED,
            Level.HINT: Color.CYAN,
            Level.INFO: Color.MAGENTA,
            Level.NOTE: Color.GREEN,
            Level.WARNING: Color.YELLOW,
        }
        return color_mapping[self.prefix]

    def to_lines(
        self: Msg,
        color: bool,  # noqa: FBT001
        width: int,
        with_prefix: bool,  # noqa: FBT001
    ) -> list[str]:
        """Output exit message to the console.

        Args:
            color: Whether to color the message
            width: Constrain message to width
            with_prefix: Whether to prefix the message
        Returns:
            The exit message as a string
        """
        prefix_length = Level.longest_formatted()
        indent = " " * prefix_length

        lines = []
        message_lines = self.message.splitlines()

        lines.extend(
            textwrap.fill(
                message_lines[0],
                width=width,
                break_on_hyphens=False,
                initial_indent=str(self.prefix) if with_prefix else indent,
                subsequent_indent=indent,
            ).splitlines(),
        )

        if len(message_lines) > 1:
            for line in message_lines[1:]:
                lines.extend(
                    textwrap.fill(
                        line,
                        width=width,
                        break_on_hyphens=False,
                        initial_indent=indent,
                        subsequent_indent=indent,
                    ).splitlines(),
                )

        start_color = self.color if color else ""
        end_color = Color.END if color else ""

        return [f"{start_color}{line}{end_color}" for line in lines]


class Output:
    """Output functionality."""

    def __init__(  # noqa: PLR0913 # pylint: disable=too-many-positional-arguments
        self: Output,
        log_file: str,
        log_level: str,
        log_append: str,
        term_features: TermFeatures,
        verbosity: int,
        display: str = "text",
    ) -> None:
        """Initialize the output object.

        Args:
            log_file: The path to the log file
            log_level: The log level
            log_append: Whether to append to the log file
            term_features: Terminal features
            verbosity: The verbosity level
            display: Whether to output as text or JSON
        """
        self._verbosity = verbosity
        self.call_count: dict[str, int] = {
            "critical": 0,
            "debug": 0,
            "error": 0,
            "hint": 0,
            "info": 0,
            "note": 0,
            "warning": 0,
        }
        self.term_features = term_features
        self.logger = logging.getLogger("ansible_creator")
        if log_level != "notset":
            self.logger.setLevel(log_level.upper())
            log_file_path = Path(log_file)
            if log_file_path.exists() and log_append == "false":
                log_file_path.unlink()
            formatter = logging.Formatter(
                fmt="%(asctime)s %(levelname)s '%(name)s.%(module)s.%(funcName)s' %(message)s",
            )
            handler = logging.FileHandler(log_file)
            handler.setFormatter(formatter)
            handler.setLevel(log_level.upper())
            self.logger.addHandler(handler)
            self.log_to_file = True
        else:
            self.log_to_file = False
        self.display = display

    def critical(self: Output, msg: str) -> None:
        """Print a critical message to the console.

        Args:
            msg: The message to print
        """
        self.call_count["critical"] += 1
        self.log(msg, level=Level.CRITICAL)
        sys.exit(1)

    def debug(self: Output, msg: str) -> None:
        """Print a debug message to the console.

        Args:
            msg: The message to print
        """
        self.call_count["debug"] += 1
        self.log(msg, level=Level.DEBUG)

    def error(self: Output, msg: str) -> None:
        """Print an error message to the console.

        Args:
            msg: The message to print
        """
        self.call_count["error"] += 1
        self.log(msg, level=Level.ERROR)

    def hint(self: Output, msg: str) -> None:
        """Print a hint message to the console.

        Args:
            msg: The message to print
        """
        self.call_count["hint"] += 1
        self.log(msg, level=Level.HINT)

    def info(self: Output, msg: str) -> None:
        """Print a info message to the console.

        Args:
            msg: The message to print
        """
        self.call_count["info"] += 1
        self.log(msg, level=Level.INFO)

    def note(self: Output, msg: str) -> None:
        """Print a note message to the console.

        Args:
            msg: The message to print
        """
        self.call_count["note"] += 1
        self.log(msg, level=Level.NOTE)

    def warning(self: Output, msg: str) -> None:
        """Print a warning message to the console.

        Args:
            msg: The message to print
        """
        self.call_count["warning"] += 1
        self.log(msg, level=Level.WARNING)

    def log(self: Output, msg: str, level: Level = Level.ERROR) -> None:
        """Print a message to the console.

        Args:
            msg: The message to print
            level: The level of the message
        """
        if self.log_to_file:
            self.logger.log(level.log_level, msg, stacklevel=3)

        debug = 2
        info = 1
        if (self._verbosity < debug and level == Level.DEBUG) or (
            self._verbosity < info and level == Level.INFO
        ):
            return

        if self.display == "json":
            print(  # noqa: T201
                json.dumps({"level": level.name, "msg": msg}),
                flush=True,
            )
            return

        lines = Msg(message=msg, prefix=level).to_lines(
            color=self.term_features.color,
            width=console_width(),
            with_prefix=True,
        )
        final_msg = "\n".join(lines)

        file = sys.stderr if level in [Level.CRITICAL, Level.ERROR] else sys.stdout

        print(final_msg, file=file)
