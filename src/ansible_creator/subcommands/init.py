"""Definitions for ansible-creator init action."""

from __future__ import annotations

import shutil
import uuid

from pathlib import Path
from typing import TYPE_CHECKING

from ansible_creator.exceptions import CreatorError
from ansible_creator.templar import Templar
from ansible_creator.types import TemplateData
from ansible_creator.utils import Copier, Walker, ask_yes_no


if TYPE_CHECKING:
    from ansible_creator.config import Config
    from ansible_creator.output import Output


class Init:
    """Class representing ansible-creator init subcommand.

    Attributes:
        common_resources: List of common resources to copy.
    """

    common_resources = (
        "common.devcontainer",
        "common.devfile",
        "common.gitignore",
        "common.vscode",
    )

    def __init__(
        self: Init,
        config: Config,
    ) -> None:
        """Initialize the init action.

        Args:
            config: App configuration object.
        """
        self._namespace: str = config.namespace
        self._collection_name = config.collection_name or ""
        self._init_path: Path = Path(config.init_path)
        self._force = config.force
        self._overwrite = config.overwrite
        self._no_overwrite = config.no_overwrite
        self._creator_version = config.creator_version
        self._project = config.project
        self._templar = Templar()
        self.output: Output = config.output

    def run(self: Init) -> None:
        """Start scaffolding skeleton."""
        self._construct_init_path()
        self.output.debug(msg=f"final collection path set to {self._init_path}")

        if self._init_path.exists():
            self.init_exists()
        self._init_path.mkdir(parents=True, exist_ok=True)

        self._scaffold()

    def _construct_init_path(self: Init) -> None:
        """Construct the init path based on project type."""
        if self._project == "playbook":
            return

        if (
            self._init_path.parts[-2:] == ("collections", "ansible_collections")
            and self._project == "collection"
            and isinstance(self._collection_name, str)
        ):
            self._init_path = self._init_path / self._namespace / self._collection_name

    def init_exists(self) -> None:
        """Handle existing init path.

        Raises:
            CreatorError: When init path is a file or not empty and --force is not provided.
        """
        # check if init_path already exists
        # init-path exists and is a file
        if self._init_path.is_file():
            msg = f"the path {self._init_path} already exists, but is a file - aborting"
            raise CreatorError(msg)
        if next(self._init_path.iterdir(), None) and self._force:
            # user requested --force, re-initializing existing directory
            self.output.warning(
                f"re-initializing existing directory {self._init_path}",
            )
            try:
                shutil.rmtree(self._init_path)
            except OSError as e:
                err = f"failed to remove existing directory {self._init_path}: {e}"
                raise CreatorError(err) from e

    def unique_name_in_devfile(self) -> str:
        """Use project specific name in devfile.

        Returns:
            Unique name entry.
        """
        final_name = f"{self._namespace}.{self._collection_name}"
        final_uuid = str(uuid.uuid4())[:8]
        return f"{final_name}-{final_uuid}"

    def _scaffold(self) -> None:
        """Scaffold an ansible project.

        Raises:
            CreatorError: When the destination directory contains files that will be overwritten and
                the user chooses not to proceed.
        """
        self.output.debug(msg=f"started copying {self._project} skeleton to destination")
        template_data = TemplateData(
            namespace=self._namespace,
            collection_name=self._collection_name,
            creator_version=self._creator_version,
            dev_file_name=self.unique_name_in_devfile(),
        )

        walker = Walker(
            resources=(f"{self._project}_project", *self.common_resources),
            resource_id=f"{self._project}_project",
            dest=self._init_path,
            output=self.output,
            templar=self._templar,
            template_data=template_data,
        )
        paths = walker.collect_paths()

        copier = Copier(
            output=self.output,
        )

        if self._no_overwrite:
            msg = "The flag `--no-overwrite` restricts overwriting."
            if paths.has_conflicts():
                msg += (
                    "\nThe destination directory contains files that can be overwritten."
                    "\nPlease re-run ansible-creator with --overwrite to continue."
                )
            raise CreatorError(msg)

        if not paths.has_conflicts() or self._force or self._overwrite:
            copier.copy_containers(paths)
            self.output.note(f"{self._project} project created at {self._init_path}")
            return

        if not self._overwrite:
            question = (
                "Files in the destination directory will be overwritten. Do you want to proceed?"
            )
            answer = ask_yes_no(question)
            if answer:
                copier.copy_containers(paths)
            else:
                msg = (
                    "The destination directory contains files that will be overwritten."
                    " Please re-run ansible-creator with --overwrite to continue."
                )
                raise CreatorError(msg)

        self.output.note(f"{self._project} project created at {self._init_path}")
