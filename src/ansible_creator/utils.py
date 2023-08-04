"""Re-usable utility functions used by this package."""

import os
import sys

from importlib import resources
from .constants import MessageColors


def get_file_contents(directory, filename):
    """Return contents of a file.

    :param directory: A directory within ansible_creator package.
    :param filename: Name of the file to read contents from.

    :raises FileNotFoundError: if filename cannot be located
    :raises TypeError:
    :raises ModuleNotFoundError: if incorrect package is provided
    """
    package = f"ansible_creator.{directory}"

    try:
        with resources.files(package).joinpath(filename).open(
            "r", encoding="utf-8"
        ) as file_open:
            content = file_open.read()
    except (FileNotFoundError, TypeError, ModuleNotFoundError) as exc:
        raise exc

    return content


def creator_exit(status, message):
    """Print a message and exit the creator process.

    :param status: exit status
    :param message: exit message
    """
    if status not in MessageColors:
        print(
            f"{MessageColors['FAILURE']}Invalid exit status: {status}. This is likely a bug."
        )
    else:
        print(f"{MessageColors[status]}{message}".strip())

        if status == "FAILURE":
            sys.exit(1)
        else:
            sys.exit(0)


def copy_container(src, dest, root, templar=None, template_data=None):
    """Recursively traverses a resource container and copies content to destination.
    :param src: A traversable object representing the source container.
    :param root: Name of the root container.
    :param dest: Absolute destination path.
    :param templar: An object of template class.
    :param template_data: A dictionary containing data to render templates with.

    """

    for obj in src.iterdir():
        dest_name = str(obj).split(root + "/", maxsplit=1)[-1]
        dest_path = os.path.join(dest, dest_name)

        if obj.is_dir():
            os.makedirs(dest_path)
            # recursively copy the directory
            copy_container(src=obj, dest=dest, root=root, template_data=template_data)

        elif obj.is_file():
            content = obj.read_text(encoding="utf-8")

            # only render as templates if both of these are provided
            # templating is not mandatory
            if templar and template_data:
                content = templar.render_from_content(
                    template=content, data=template_data
                )

            # remove .j2 suffix at destination
            dest_file = os.path.join(dest, dest_path.split(".j2", maxsplit=1)[0])
            with open(dest_file, "w", encoding="utf-8") as df_handle:
                df_handle.write(content)
