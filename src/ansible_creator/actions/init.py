"""Definitions for ansible-creator init action."""
import os
import shutil
from importlib import resources

from ..exceptions import CreatorError
from ..templar import Templar
from ..utils import creator_exit, copy_container


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

        # copy new_collection container to destination, templating files when found
        copy_container(
            src=resources.files("ansible_creator.resources.new_collection"),
            dest=col_path,
            root="new_collection",
            templar=self._templar,
            template_data={
                "namespace": self._namespace,
                "collection_name": self._collection_name,
            },
        )

        creator_exit(
            status="OKGREEN",
            message=(
                f"- Collection {self._namespace}.{self._collection_name}"
                f" was created successfully at {self._init_path}"
            ),
        )
