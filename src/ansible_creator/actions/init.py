"""Definitions for ansible-creator init action."""

from __future__ import annotations

import logging
import os
import shutil

from ansible_creator.exceptions import CreatorError
from ansible_creator.templar import Templar
from ansible_creator.utils import copy_container


logger = logging.getLogger("ansible-creator")


class CreatorInit:
    """Class representing ansible-creator create subcommand."""

    def __init__(self: CreatorInit, **kwargs: str) -> None:
        """Initialize the init action.

        :param kwargs: Arguments passed for the init action
        """
        self._namespace: str = kwargs["collection_name"].split(".")[0]
        self._collection_name: str = kwargs["collection_name"].split(".")[-1]
        self._init_path: str = os.path.abspath(
            os.path.expanduser(os.path.expandvars(kwargs["init_path"])),
        )
        self._force = kwargs["force"]
        self._templar = Templar()

    def run(self: CreatorInit) -> None:
        """Start scaffolding collection skeleton.

        :raises CreatorError: if computed collection path is an existing directory or file.
        """
        col_path = os.path.join(self._init_path, self._namespace, self._collection_name)

        logger.debug("final collection path set to %s", col_path)

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
                    "{'':<9}You can use --force to re-initialize this directory,"
                    "\n{'':<9}However it will delete ALL existing contents in it."
                )
                raise CreatorError(msg)

            # user requested --force, re-initializing existing directory
            logger.warning("re-initializing existing directory %s", col_path)
            for root, dirs, files in os.walk(col_path, topdown=True):
                for old_dir in dirs:
                    path = os.path.join(root, old_dir)
                    logger.debug("removing tree %s", old_dir)
                    shutil.rmtree(path)
                for old_file in files:
                    path = os.path.join(root, old_file)
                    logger.debug("removing file %s", old_file)
                    os.unlink(path)

        # if init_path does not exist, create it
        if not os.path.exists(col_path):
            logger.debug("creating new directory at %s", col_path)
            os.makedirs(col_path)

        # copy new_collection container to destination, templating files when found
        logger.debug("started copying collection skeleton to destination")
        copy_container(
            source="new_collection",
            dest=col_path,
            templar=self._templar,
            template_data={
                "namespace": self._namespace,
                "collection_name": self._collection_name,
            },
        )

        logger.info(
            "collection %s.%s successfully created at %s",
            self._namespace,
            self._collection_name,
            self._init_path,
        )
