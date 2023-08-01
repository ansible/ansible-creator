"""Re-usable utility functions used by this package."""

import sys

from importlib import resources

from .constants import MessageColors


def get_file_contents(directory, filename):
    """Return contents of a file.

    :param directory: A directory within ansible_creator package.
    :param filename: Name of the file to read contents from.

    :raises FileNotFoundError:
    :raises TypeError:
    """
    package = f"ansible_creator.{directory}"

    try:
        with resources.files(package).joinpath(filename).open(
            "r", encoding="utf-8"
        ) as fh:
            content = fh.read()
    except (FileNotFoundError, TypeError) as exc:
        raise exc

    return content


def creator_exit(status, message):
    """Helper function for printing a message and exiting the creator process.

    :param status: exit status
    :param message: exit message
    """
    if status not in MessageColors:
        print(
            f"{MessageColors['FAILURE']}Invalid exit status: {status}. This is likely a bug."
        )
    else:
        print(f"{MessageColors[status]}{message}")

        if status == "FAILURE":
            sys.exit(1)
        else:
            sys.exit(0)
