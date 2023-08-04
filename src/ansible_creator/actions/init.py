"""Definitions for ansible-creator init action."""
import os
import shutil

from pathlib import Path

from ..constants import COLLECTION_SKEL_DIRS, COLLECTION_SKEL_TEMPLATES
from ..templar import Templar
from ..utils import creator_exit
from ..exceptions import CreatorError
from importlib import resources


class CreatorInit:
    """Class representing ansible-creator create subcommand."""

    def __init__(self, **args):
        """Initialize the init action.

        :param args: Arguments passed for the init action
        """
        self._namespace = args["collection_name"].split(".")[0]
        self._collection_name = args["collection_name"].split(".")[-1]
        self._init_path = os.path.abspath(
            os.path.expanduser(os.path.expandvars(args["init_path"]))
        )
        self._force = args["force"]
        self._templar = Templar()

    def run(self):
        """Start scaffolding collection skeleton.

        :raises CreatorError: if computed collection path is an existing directory or file.
        """
        col_path = os.path.join(self._init_path, self._namespace, self._collection_name)

        # check if init_path already exists
        if os.path.exists(col_path):
            if os.path.isfile(col_path):
                raise CreatorError(
                    f"- the path {col_path} already exists, but is a file - aborting"
                )

            if not self._force:
                raise CreatorError(
                    f"- The directory {col_path} already exists.\n"
                    "You can use --force to re-initialize this directory,\n"
                    "however it will delete ALL existing contents in it."
                )

            # user requested --force, re-initializing existing directory
            for root, dirs, files in os.walk(col_path, topdown=True):
                for old_dir in dirs:
                    path = os.path.join(root, old_dir)
                    shutil.rmtree(path)
                for old_file in files:
                    path = os.path.join(root, old_file)
                    os.unlink(path)

        # if init_path does not exist, create it
        if not os.path.exists(col_path):
            os.makedirs(col_path)

        # start scaffolding collection skeleton - directories
        for directory in COLLECTION_SKEL_DIRS:
            dir_path = os.path.join(col_path, directory)
            os.makedirs(dir_path)

        # touch __init__.py files in plugin subdirs
        for plugin_dir in COLLECTION_SKEL_DIRS[4:14]:
            file_path = os.path.join(col_path, plugin_dir, "__init__.py")
            Path(file_path).touch()

        # render and write collection skel templates
        init_data = {
            "namespace": self._namespace,
            "collection_name": self._collection_name,
        }

        for template in COLLECTION_SKEL_TEMPLATES:
            rendered_content = self._templar.render(
                template_name=template, data=init_data
            )
            dest_file = os.path.join(col_path, template.split(".j2", maxsplit=1)[0])
            with open(dest_file, "w", encoding="utf-8") as dest_file:
                dest_file.write(rendered_content)

        creator_exit(
            status="OKGREEN",
            message=(
                f"- Collection {self._namespace}.{self._collection_name}"
                f" was created successfully at {self._init_path}"
            ),
        )
