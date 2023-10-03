"""Definitions for ansible-creator init action."""

from __future__ import annotations

import os
import shutil

from typing import TYPE_CHECKING

from ansible_creator.exceptions import CreatorError
from ansible_creator.templar import Templar
from ansible_creator.utils import copy_container


if TYPE_CHECKING:
    from ansible_creator.output import Output


class CreatorInit:
    """Class representing ansible-creator create subcommand."""

    def __init__(  # noqa: PLR0913
        self: CreatorInit,
        collection_name: str,
        init_path: str,
        force: bool,  # noqa: FBT001
        creator_version: str,
        output: Output,
    ) -> None:
        """Initialize the init action.

        :param kwargs: Arguments passed for the init action
        """
        self._namespace: str = collection_name.split(".")[0]
        self._collection_name: str = collection_name.split(".")[-1]
        self._init_path: str = os.path.abspath(
            os.path.expanduser(os.path.expandvars(init_path)),
        )
        self._force = force
        self._creator_version = creator_version
        self._templar = Templar()
        self.output: Output = output

    def run(self: CreatorInit) -> None:
        """Start scaffolding collection skeleton.

        :raises CreatorError: if computed collection path is an existing directory or file.
        """
        col_path = os.path.join(self._init_path, self._namespace, self._collection_name)

        self.output.debug(msg="final collection path set to {col_path}")

        # check if init_path already exists
        if os.path.exists(col_path):
            if os.path.isfile(col_path):
                msg = f"the path {col_path} already exists, but is a file - aborting"
                raise CreatorError(
                    msg,
                )

            if not self._force:
                msg = (
                    f"The directory {col_path} already exists.\n"
                    f"You can use --force to re-initialize this directory."
                    f"\nHowever it will delete ALL existing contents in it."
                )
                raise CreatorError(msg)

            # user requested --force, re-initializing existing directory
            self.output.warning(f"re-initializing existing directory {col_path}")
            for root, dirs, files in os.walk(col_path, topdown=True):
                for old_dir in dirs:
                    path = os.path.join(root, old_dir)
                    self.output.debug(f"removing tree {old_dir}")
                    shutil.rmtree(path)
                for old_file in files:
                    path = os.path.join(root, old_file)
                    self.output.debug(f"removing file {old_file}")
                    os.unlink(path)

        # if init_path does not exist, create it
        if not os.path.exists(col_path):
            self.output.debug(msg=f"creating new directory at {col_path}")
            os.makedirs(col_path)

        # copy new_collection container to destination, templating files when found
        self.output.debug(msg="started copying collection skeleton to destination")
        copy_container(
            source="new_collection",
            dest=col_path,
            templar=self._templar,
            template_data={
                "namespace": self._namespace,
                "collection_name": self._collection_name,
                "creator_version": self._creator_version,
            },
            output=self.output,
        )

        self.output.note(
            f"collection {self._namespace}.{self._collection_name} created at {self._init_path}",
        )
