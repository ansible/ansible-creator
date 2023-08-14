"""Re-usable utility functions used by this package."""

import os
import sys

from importlib import resources
from ansible_creator.constants import MessageColors
from ansible_creator.exceptions import CreatorError

PATH_REPLACERS = {
    "network_os": "collection_name",
    "resource": "resource",
}


def get_file_contents(directory, filename):
    """Return contents of a file.

    :param directory: A directory within ansible_creator package.
    :param filename: Name of the file to read contents from.

    :returns: Content loaded from file as string.

    :raises FileNotFoundError: if filename cannot be located
    :raises TypeError: if invalid type is found
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


def copy_container(
    source, dest, templar=None, template_data=None, allow_overwrite=None
):
    """Copy files and directories from a possibly nested source to a destination.

    :param source: Name of the source container.
    :param dest: Absolute destination path.
    :param templar: An object of template class.
    :param template_data: A dictionary containing data to render templates with.
    :param allow_overwrite: A list of paths that should be overwritten at destination.

    :raises CreatorError: if allow_overwrite is not a list.
    """

    def _recursive_copy(root):
        """Recursively traverses a resource container and copies content to destination.

        :param root: A traversable object representing root of the container to copy.
        """
        for obj in root.iterdir():
            overwrite = False
            dest_name = str(obj).split(source + "/", maxsplit=1)[-1]
            dest_path = os.path.join(dest, dest_name)

            if (allow_overwrite) and (dest_name in allow_overwrite):
                overwrite = True

            # replace placeholders in destination path with real values
            for key, val in PATH_REPLACERS.items():
                if key in dest_path:
                    dest_path = dest_path.replace(key, template_data.get(val))

            if obj.is_dir():
                if not os.path.exists(dest_path):
                    os.makedirs(dest_path)

                # recursively copy the directory
                _recursive_copy(root=obj)

            elif obj.is_file():
                dest_file = os.path.join(dest, dest_path.split(".j2", maxsplit=1)[0])

                # write at destination only if missing or belongs to overwrite list
                if not os.path.exists(dest_file) or overwrite:
                    content = obj.read_text(encoding="utf-8")

                    # only render as templates if both of these are provided
                    # templating is not mandatory
                    if templar and template_data:
                        content = templar.render_from_content(
                            template=content, data=template_data
                        )

                    # remove .j2 suffix at destination
                    with open(dest_file, "w", encoding="utf-8") as df_handle:
                        df_handle.write(content)

    if allow_overwrite and not isinstance(allow_overwrite, list):
        raise CreatorError(
            f"allow_overwrite should be of type list, instead got {type(allow_overwrite)}"
        )

    _recursive_copy(root=resources.files(f"ansible_creator.resources.{source}"))
