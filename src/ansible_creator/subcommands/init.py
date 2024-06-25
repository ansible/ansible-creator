"""Definitions for ansible-creator init action."""

from __future__ import annotations

import shutil

from pathlib import Path
from typing import TYPE_CHECKING

from ansible_creator.exceptions import CreatorError
from ansible_creator.templar import Templar
from ansible_creator.types import TemplateData
from ansible_creator.utils import Copier


if TYPE_CHECKING:

    from ansible_creator.config import Config
    from ansible_creator.output import Output


class Init:
    """Class representing ansible-creator init subcommand."""

    def __init__(
        self: Init,
        config: Config,
    ) -> None:
        """Initialize the init action.

        Args:
            config: App configuration object.
        """
        self._namespace: str = config.namespace
        self._collection_name: str | None = config.collection_name
        self._init_path: Path = Path(config.init_path)
        self._force = config.force
        self._creator_version = config.creator_version
        self._project = config.project
        self._scm_org = config.scm_org
        self._scm_project = config.scm_project
        self._templar = Templar()
        self.output: Output = config.output

    def run(self: Init) -> None:  # noqa: C901
        """Start scaffolding skeleton.

        Raises:
            CreatorError: When computed collection path is an existing directory or file.
        """
        if (
            self._init_path.parts[-2:] == ("collections", "ansible_collections")
            and self._project == "collection"
            and isinstance(self._collection_name, str)
        ):
            self._init_path = self._init_path / self._namespace / self._collection_name

        self.output.debug(msg=f"final collection path set to {self._init_path}")

        # check if init_path already exists
        if self._init_path.exists():
            # init-path exists and is a file
            if self._init_path.is_file():
                msg = f"the path {self._init_path} already exists, but is a file - aborting"
                raise CreatorError(
                    msg,
                )
            if next(self._init_path.iterdir(), None):
                # init-path exists and is not empty, but user did not request --force
                if not self._force:
                    msg = (
                        f"The directory {self._init_path} is not empty.\n"
                        f"You can use --force to re-initialize this directory."
                        f"\nHowever it will delete ALL existing contents in it."
                    )
                    raise CreatorError(msg)

                # user requested --force, re-initializing existing directory
                self.output.warning(
                    f"re-initializing existing directory {self._init_path}",
                )
                try:
                    shutil.rmtree(self._init_path)
                except OSError as e:
                    err = f"failed to remove existing directory {self._init_path}: {e}"
                    raise CreatorError(err) from e

        # if init_path does not exist, create it
        if not self._init_path.exists():
            self.output.debug(msg=f"creating new directory at {self._init_path}")
            self._init_path.mkdir(parents=True)

        common_resources = [
            "common.devcontainer",
            "common.devfile",
            "common.gitignore",
            "common.vscode",
        ]

        if self._project == "collection":
            if not isinstance(self._collection_name, str):
                msg = "Collection name is required when scaffolding a collection."
                raise CreatorError(msg)
            # copy new_collection container to destination, templating files when found
            self.output.debug(msg="started copying collection skeleton to destination")
            template_data = TemplateData(
                namespace=self._namespace,
                collection_name=self._collection_name,
                creator_version=self._creator_version,
            )
            copier = Copier(
                resources=["new_collection", *common_resources],
                resource_id="new_collection",
                dest=self._init_path,
                output=self.output,
                templar=self._templar,
                template_data=template_data,
            )
            copier.copy_containers()

            self.output.note(
                f"collection {self._namespace}.{self._collection_name} "
                f"created at {self._init_path}",
            )

        else:
            self.output.debug(
                msg="started copying ansible-project skeleton to destination",
            )
            if not isinstance(self._scm_org, str) or not isinstance(
                self._scm_project,
                str,
            ):
                msg = (
                    "Parameters 'scm-org' and 'scm-project' are required when "
                    "scaffolding an ansible-project."
                )
                raise CreatorError(msg)

            template_data = TemplateData(
                creator_version=self._creator_version,
                scm_org=self._scm_org,
                scm_project=self._scm_project,
            )

            copier = Copier(
                resources=["ansible_project", *common_resources],
                resource_id="ansible_project",
                dest=self._init_path,
                output=self.output,
                templar=self._templar,
                template_data=template_data,
            )
            copier.copy_containers()

            self.output.note(
                f"ansible project created at {self._init_path}",
            )
