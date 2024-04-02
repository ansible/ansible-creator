"""Definitions for ansible-creator init action."""

from __future__ import annotations

import os
import shutil

from typing import TYPE_CHECKING

from ansible_creator.exceptions import CreatorError
from ansible_creator.templar import Templar
from ansible_creator.utils import copy_container


if TYPE_CHECKING:
    from ansible_creator.config import Config
    from ansible_creator.output import Output


class Init:
    """Class representing ansible-creator init subcommand."""

    def __init__(
        self: Init,
        config: Config,
        output: Output,
    ) -> None:
        """Initialize the init action.

        :param config: App configuration object.
        :param output: Output class object.
        """
        self._namespace: str = config.namespace
        self._collection_name: str = config.collection_name
        self._init_path: str = config.init_path
        self._force = config.force
        self._creator_version = config.creator_version
        self._templar = Templar()
        self.output: Output = output

    def run(self: Init) -> None:
        """Start scaffolding collection skeleton.

        :raises CreatorError: if computed collection path is an existing directory or file.
        """
        if self._init_path.endswith("collections/ansible_collections"):
            self._init_path = os.path.join(
                self._init_path,
                self._namespace,
                self._collection_name,
            )

        self.output.debug(msg=f"final collection path set to {self._init_path}")

        # check if init_path already exists
        if os.path.exists(self._init_path):
            if os.path.isfile(self._init_path):
                msg = f"the path {self._init_path} already exists, but is a file - aborting"
                raise CreatorError(
                    msg,
                )

            if not self._force:
                msg = (
                    f"The directory {self._init_path} already exists.\n"
                    f"You can use --force to re-initialize this directory."
                    f"\nHowever it will delete ALL existing contents in it."
                )
                raise CreatorError(msg)

            # user requested --force, re-initializing existing directory
            self.output.warning(f"re-initializing existing directory {self._init_path}")
            for root, dirs, files in os.walk(self._init_path, topdown=True):
                for old_dir in dirs:
                    path = os.path.join(root, old_dir)
                    self.output.debug(f"removing tree {old_dir}")
                    shutil.rmtree(path)
                for old_file in files:
                    path = os.path.join(root, old_file)
                    self.output.debug(f"removing file {old_file}")
                    os.unlink(path)

        # if init_path does not exist, create it
        if not os.path.exists(self._init_path):
            self.output.debug(msg=f"creating new directory at {self._init_path}")
            os.makedirs(self._init_path)

        # copy new_collection container to destination, templating files when found
        self.output.debug(msg="started copying collection skeleton to destination")
        copy_container(
            source="new_collection",
            dest=self._init_path,
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
