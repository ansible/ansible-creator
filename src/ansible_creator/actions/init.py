"""Definitions for ansible-creator init action."""
import os
import logging
import shutil

from ansible_creator.exceptions import CreatorError
from ansible_creator.templar import Templar
from ansible_creator.utils import copy_container

logger = logging.getLogger("ansible-creator")


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

        logger.debug("final collection path set to %s", col_path)

        # check if init_path already exists
        if os.path.exists(col_path):
            if os.path.isfile(col_path):
                raise CreatorError(
                    f"the path {col_path} already exists, but is a file - aborting"
                )

            if not self._force:
                raise CreatorError(
                    f"The directory {col_path} already exists.\n"
                    f"{'':<9}You can use --force to re-initialize this directory,\n"
                    f"{'':<9}However it will delete ALL existing contents in it."
                )

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
